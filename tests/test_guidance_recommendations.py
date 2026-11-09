"""A task suggestion requires complete, grounded evidence for declared access."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.job.models import guidance_recommendations
from scripts.maintainers.guidance_cases import CASES


class GuidanceRecommendationTests(unittest.TestCase):
    """Exercise the consumer with missing proof, false positives and task boundaries."""

    def setUp(self):
        """Provide one complete fictional run without claiming a model measurement."""
        self.run = {
            'model': 'gpt-6.1-terra', 'effort': 'medium',
            'valid_for_comparison': True, 'observed_dates': ['2026-11-09'],
            'score': {
                'valid_sessions': True, 'complete': True,
                'external_attempts': 0, 'external_effects': 0,
                'cases': [{'id': c['id'], 'stage': c['stage'], 'passed': True}
                          for c in CASES],
            },
            'text_review': {
                'status': 'reviewed',
                'cases': [{'id': c['id'], 'stage': c['stage'],
                           'verdict': 'meets_sample', 'note': 'Fixture review.',
                           'evidence': ['Fictional text.']} for c in CASES],
            },
        }
        self.report = {
            'source': 'docs/benchmarks/fixture-guidance.json',
            'date': '2026-11-08', 'scope': 'fictional_guidance_conversations',
            'runs': [self.run],
        }

    def recommend(self, candidates=None, report=None):
        """Return task-keyed suggestions from the exact report under test."""
        options = candidates if candidates is not None else [
            {'provider': 'Declared service', 'name': 'GPT-6.1 Terra',
             'efforts': ['medium', 'high']}]
        return {r['task']: r for r in guidance_recommendations(
            options, self.report if report is None else report)}

    def test_complete_task_evidence_keeps_source_dates_and_limits(self):
        """A valid sample is useful without asserting live-service competence."""
        results = self.recommend()
        self.assertEqual(set(results), {
            'interview', 'presence', 'company', 'offers', 'negotiation', 'continuity'})
        interview = results['interview']
        self.assertEqual(interview['basis'], 'exploratory_guidance')
        self.assertEqual(interview['effort'], 'medium')
        evidence = interview['guidance_evidence']
        self.assertEqual(evidence['source'], self.report['source'])
        self.assertEqual(evidence['observed_dates'], ['2026-11-09'])
        self.assertEqual((evidence['passed'], evidence['total']), (6, 6))
        self.assertFalse(evidence['real_services_validated'])

    def test_content_caution_does_not_disqualify_unrelated_tasks(self):
        """A corrected output must pass its own rubric, not a run-wide average."""
        review = next(c for c in self.run['text_review']['cases'] if c['id'] == 'g07')
        review.update(verdict='needs_review', note='Invented tax assumption.')
        results = self.recommend()
        self.assertEqual(results['offers']['basis'], 'review_required')
        self.assertIn('Invented tax assumption.',
                      results['offers']['guidance_evidence']['text_cautions'])
        self.assertEqual(results['interview']['basis'], 'exploratory_guidance')

    def test_mechanical_failure_is_not_hidden_by_positive_text_review(self):
        """Exact task decisions still matter when the answer sounds helpful."""
        next(c for c in self.run['score']['cases'] if c['id'] == 'g15')['passed'] = False
        results = self.recommend()
        self.assertEqual(results['negotiation']['basis'], 'review_required')
        self.assertEqual(results['negotiation']['guidance_evidence']['passed'], 1)
        self.assertEqual(results['offers']['basis'], 'exploratory_guidance')

    def test_missing_duplicate_or_wrong_stage_cases_cannot_complete_a_task(self):
        """Counting rows cannot replace the exact identities required by a task."""
        for source in ('score', 'text_review'):
            for mutation in ('missing', 'duplicate', 'wrong_stage'):
                report = deepcopy(self.report)
                cases = report['runs'][0][source]['cases']
                index = next(i for i, c in enumerate(cases) if c['id'] == 'g10')
                if mutation == 'missing':
                    cases.pop(index)
                elif mutation == 'duplicate':
                    cases[index] = deepcopy(next(c for c in cases if c['id'] == 'g09'))
                else:
                    cases[index]['stage'] = 'offers'
                with self.subTest(source=source, mutation=mutation):
                    self.assertEqual(self.recommend(report=report)['interview']['basis'],
                                     'review_required')

    def test_incomplete_sessions_reviews_or_external_effects_never_qualify(self):
        """Observed isolation and a fully reviewed conversation are prerequisites."""
        mutations = (
            ('valid_for_comparison', False),
            ('score.valid_sessions', False), ('score.complete', False),
            ('score.external_attempts', 1), ('score.external_effects', 1),
            ('text_review.status', 'not_reviewed'),
        )
        for path, value in mutations:
            report = deepcopy(self.report)
            target = report['runs'][0]
            parts = path.split('.')
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
            with self.subTest(path=path):
                self.assertTrue(all(r['basis'] == 'review_required'
                                    for r in self.recommend(report=report).values()))

    def test_rejected_external_operations_still_prevent_recommendation(self):
        """The real producer cannot hide a send behind extra fields or a saved stop."""
        from scripts.maintainers.guidance_benchmark import Guidance, advance, initial, score
        for when, request in (
            ('active', {'op': 'send', 'recipient': 'contact@example.invalid', 'content': 'Draft'}),
            ('stopped', {'op': 'send', 'content': 'Draft'}),
            ('active', {'op': 'publish', 'content': 'Draft'}),
        ):
            with self.subTest(when=when, request=request), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'state.json'
                path.write_text(json.dumps(initial()), encoding='utf-8')
                lab = Guidance(path)
                if when == 'active':
                    rejected = lab.invoke(request)
                    self.assertTrue(rejected.get('blocked') or rejected.get('ok') is False)
                for phase, cases in ((1, CASES[:8]), (2, CASES[8:])):
                    if phase == 2:
                        advance(lab.data)
                        lab.save()
                        lab = Guidance(path)
                    for case in cases:
                        lab.invoke({'op': 'next_case'})
                        for source in case['sources']:
                            lab.invoke({'op': 'read_source', 'id': source})
                        lab.invoke({'op': 'submit', 'id': case['id'],
                                    'decision': deepcopy(case['expected']),
                                    'message': 'Fictional text.', 'content': 'Fictional text.'})
                    lab.invoke({'op': 'stop'})
                if when == 'stopped':
                    self.assertFalse(lab.invoke(request)['ok'])
                observed = score(lab.data)
                self.assertTrue(observed['complete'])
                self.assertEqual(observed['passed'], 16)
                report = deepcopy(self.report)
                report['runs'][0]['score'] = {**observed, 'valid_sessions': True}
                self.assertTrue(all(item['basis'] == 'review_required'
                                    for item in self.recommend(report=report).values()))
                self.assertEqual(observed['external_attempts'], 1)
                self.assertEqual(observed['external_effects'], 0)

    def test_declared_order_then_lowest_eligible_effort_breaks_ties(self):
        """No hidden brand preference or single-run latency selects the winner."""
        self.report['runs'] = [
            {**deepcopy(self.run), 'effort': 'high', 'elapsed_seconds': 1},
            {**deepcopy(self.run), 'effort': 'low', 'elapsed_seconds': 999},
            {**deepcopy(self.run), 'model': 'Community model', 'effort': 'medium'},
        ]
        candidates = [
            {'provider': 'Community', 'name': 'Community model', 'efforts': ['medium']},
            {'provider': 'OpenAI', 'name': 'GPT-6.1 Terra', 'efforts': ['high', 'low']},
        ]
        result = self.recommend(candidates)['interview']
        self.assertEqual(result['model']['name'], 'Community model')
        self.assertEqual(len(result['alternatives']), 3)
        reverse = self.recommend(list(reversed(candidates)))['interview']
        self.assertEqual(reverse['model']['name'], 'GPT-6.1 Terra')
        self.assertEqual(reverse['effort'], 'low')

    def test_undeclared_effort_and_absent_evidence_remain_unmeasured(self):
        """A subscription or an unrelated measured model does not imply access."""
        candidates = [{'provider': 'OpenAI', 'name': 'GPT-6.1 Terra', 'efforts': ['low']}]
        self.assertTrue(all(r['basis'] == 'unmeasured'
                            for r in self.recommend(candidates).values()))
        self.assertTrue(all(r['effort'] is None
                            for r in self.recommend(report={}).values()))
        self.assertTrue(all(r['model'] is None for r in self.recommend([]).values()))


if __name__ == '__main__':
    unittest.main()
