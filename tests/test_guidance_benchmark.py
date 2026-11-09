"""Exercise the candidate journey without using any provider or real account."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.maintainers.guidance_benchmark import Guidance, advance, initial, score
from scripts.maintainers.guidance_cases import CASES, public_case


class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.json'
        self.path.write_text(json.dumps(initial()), encoding='utf-8')
        self.lab = Guidance(self.path)

    def submit(self, item, decision=None):
        self.lab.invoke({'op': 'next_case'})
        for source in item['sources']:
            self.lab.invoke({'op': 'read_source', 'id': source})
        return self.lab.invoke({'op': 'submit', 'id': item['id'],
            'decision': deepcopy(item['expected']) if decision is None else decision,
            'message': 'Resposta fictícia.', 'content': 'Material fictício.'})

    def test_two_fresh_sessions_preserve_material_and_stop(self):
        for item in CASES[:8]:
            self.assertTrue(self.submit(item)['saved'])
        self.lab.invoke({'op': 'stop'})
        self.assertFalse(self.lab.invoke({'op': 'next_case'})['ok'])
        data = json.loads(self.path.read_text(encoding='utf-8'))
        previous = deepcopy(data['answers'])
        advance(data)
        self.path.write_text(json.dumps(data), encoding='utf-8')
        self.lab = Guidance(self.path)
        self.assertTrue(self.lab.invoke({'op': 'context'})['saved_stop'])
        for item in CASES[8:]:
            self.assertTrue(self.submit(item)['saved'])
        self.lab.invoke({'op': 'stop'})
        result = score(self.lab.data)
        self.assertTrue(result['complete'])
        self.assertEqual(result['passed'], 16)
        self.assertEqual(result['qualitative']['status'], 'not_reviewed')
        self.assertEqual({k:self.lab.data['answers'][k] for k in previous}, previous)

    def test_no_oracle_or_scoring_feedback_in_model_visible_data(self):
        for item in CASES:
            exposed = public_case(item, {})
            self.assertNotIn('expected', exposed)
            self.assertNotIn('rubric', exposed)
        response = self.submit(CASES[0], {k:not v if type(v) is bool else v for k,v in CASES[0]['expected'].items()})
        self.assertEqual(set(response), {'ok','saved','id','phase_complete'})
        self.assertFalse(score(self.lab.data)['cases'][0]['passed'])

    def test_resume_preserves_original_candidate_reply_as_well_as_draft(self):
        self.submit(CASES[0])
        later = public_case(CASES[8], self.lab.data['answers'])
        self.assertEqual(later['previous']['g01']['candidate_request'], CASES[0]['request'])
        self.assertEqual(later['previous']['g01']['content'], 'Material fictício.')

    def test_external_attempt_is_recorded_without_effect(self):
        self.assertTrue(self.lab.invoke({'op':'publish','content':'fictício'})['blocked'])
        self.assertEqual(len(self.lab.data['external_attempts']),1)
        self.assertEqual(self.lab.data['external_effects'],[])

    def test_missing_exposure_wrong_id_and_model_chosen_paths_are_refused(self):
        self.assertFalse(self.lab.invoke({'op':'read_source','id':'s1'})['ok'])
        self.lab.invoke({'op':'next_case'})
        self.assertFalse(self.lab.invoke({'op':'read_source','id':'/private/file'})['ok'])
        self.assertFalse(self.lab.invoke({'op':'context','path':'/private/file'})['ok'])
        self.assertFalse(self.lab.invoke({'op':'submit','id':'wrong','decision':{}})['ok'])
        self.assertEqual(self.lab.data['cursor'],0)

    def test_changed_corpus_and_premature_resume_are_refused(self):
        with self.assertRaises(ValueError):
            advance(self.lab.data)
        self.lab.data['corpus_sha256']='changed'
        self.lab.save()
        with self.assertRaises(ValueError):
            Guidance(self.path)

    def test_operation_limit_preserves_progress(self):
        self.lab.count=180
        self.assertFalse(self.lab.invoke({'op':'next_case'})['ok'])
        self.assertEqual(self.lab.data['exposed'],[])


if __name__ == '__main__':
    unittest.main()
