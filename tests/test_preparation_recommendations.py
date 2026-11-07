"""Preparation advice needs content evidence and only selects declared access."""
import copy
import json
import unittest
from scripts.job.models import PREPARATION_REPORT, preparation_recommendations


class PreparationRecommendationsTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads(PREPARATION_REPORT.read_text(encoding='utf-8'))

    def recommend(self, names, report=None):
        candidates = [{'provider': 'Aplicativo informado', 'name': name, 'efforts': efforts} for name, efforts in names]
        return {r['task']: r for r in preparation_recommendations(candidates, self.report if report is None else report)}

    def test_effort_and_selection_are_limited_to_declared_access(self):
        result = self.recommend([('GPT-6.1 Terra', ['medium', 'high'])])
        self.assertEqual({r['effort'] for r in result.values()}, {'medium'})
        self.assertTrue(all(r['basis'] == 'exploratory_preparation' for r in result.values()))
        self.assertTrue(all(not r['preparation_evidence']['tools_validated'] for r in result.values()))
        self.assertTrue(all(r['model']['name'] == 'GPT-6.1 Terra' for r in result.values()))
        only_high = self.recommend([('GPT-6.1 Terra', ['high'])])
        self.assertEqual(only_high['cv']['effort'], 'high')

    def test_mechanical_pass_does_not_hide_onboarding_or_cv_cautions(self):
        haiku = self.recommend([('Claude Haiku 5.5', ['medium'])])
        self.assertEqual(haiku['onboarding']['preparation_evidence']['passed'], 2)
        self.assertEqual(haiku['onboarding']['basis'], 'review_required')
        self.assertTrue(haiku['onboarding']['preparation_evidence']['text_cautions'])
        fable = self.recommend([('Claude Fable 5.1', ['high'])])
        self.assertEqual(fable['cv']['basis'], 'review_required')
        self.assertEqual(fable['career']['basis'], 'exploratory_preparation')

    def test_format_failure_or_missing_review_cannot_promote(self):
        opus = self.recommend([('Claude Opus 5.5', ['high'])])
        self.assertTrue(all(r['basis'] == 'review_required' for r in opus.values()))
        self.assertTrue(opus['cv']['preparation_evidence']['format_errors'])
        report = copy.deepcopy(self.report)
        run = next(r for r in report['runs'] if r['id'] == 'terra-medium')
        run['text_review']['status'] = 'not_reviewed'
        result = self.recommend([('GPT-6.1 Terra', ['medium'])], report)
        self.assertEqual(result['cv']['basis'], 'review_required')
        run['text_review']['status'] = 'reviewed'
        run['tool_calls'] = 1
        self.assertEqual(self.recommend([('GPT-6.1 Terra', ['medium'])], report)['cv']['basis'], 'review_required')

    def test_missing_report_and_unknown_effort_stay_unmeasured(self):
        self.assertEqual(self.recommend([('GPT-6 Astra', ['high'])], {})['cv']['basis'], 'unmeasured')
        self.assertEqual(self.recommend([('GPT-6 Astra', ['medium'])])['cv']['basis'], 'unmeasured')
        empty = self.recommend([])
        self.assertTrue(all(r['model'] is None for r in empty.values()))

    def test_no_cross_stage_inference_and_no_unsafe_text_promotion(self):
        m3 = self.recommend([('MiniMax-M3.1-Flash[1m]', ['xhigh'])])
        self.assertTrue(all(r['basis'] == 'review_required' for r in m3.values()))
        choices = self.recommend([('Claude Fable 5.1', ['high']), ('GPT-6.1 Sol', ['medium'])])
        self.assertEqual(choices['cv']['model']['name'], 'GPT-6.1 Sol')
        self.assertNotIn('Claude Fable 5.1', [m['name'] for m in choices['cv']['alternatives']])
