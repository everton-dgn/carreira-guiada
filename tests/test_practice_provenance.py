import tempfile
import unittest
from pathlib import Path
from scripts.job.practice import Practice


class ProvenanceTests(unittest.TestCase):
    def test_legacy_and_identified_attempts(self):
        """Legacy retries deduplicate while distinct confirmed attempt IDs remain separate."""
        with tempfile.TemporaryDirectory() as root:
            p = Practice(Path(root).resolve())
            s = p.start('rh', 'coach', short=True)
            sid, q = s['session_id'], s['question']['id']
            p.answer(sid, q, 'Resposta')
            p.answer(sid, q, 'Resposta')
            p.answer(sid, q, 'Resposta', attempt_id='one', origin='person', user_confirmation='Eu respondi')
            p.answer(sid, q, 'Resposta', attempt_id='one', origin='person', user_confirmation='Eu respondi')
            p.answer(sid, q, 'Resposta', attempt_id='two', origin='person', user_confirmation='Eu respondi')
            attempts = p.get()['sessions'][0]['questions'][0]['attempts']
            self.assertEqual(len(attempts), 3)
            self.assertEqual(attempts[0]['origin'], 'unknown')
            self.assertIn('recorded_at', attempts[1])
            with self.assertRaises(ValueError): p.answer(sid, q, 'Outra', attempt_id='one', origin='person', user_confirmation='Eu respondi')
            with self.assertRaises(ValueError): p.answer(sid, q, 'Outra', origin='person')
