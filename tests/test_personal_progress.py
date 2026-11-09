import tempfile
import unittest
from pathlib import Path
from scripts.job.practice import Practice
from scripts.job.personal_progress import PersonalProgress


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.p = PersonalProgress(self.root)

    def test_empty_and_report_correction(self):
        self.assertEqual(self.p.get()['version'], 0)
        self.assertEqual(self.p.history(), [])
        self.assertFalse((self.root / '.job').exists())
        self.p.configure({'expected_version': 0, 'mode': 'points'})
        event = {'expected_version': 1, 'event_id': 'e', 'activity': 'leitura', 'source': {'kind': 'user_report', 'description': 'Li um artigo'}, 'user_confirmation': 'Eu li', 'reported_minutes': 30, 'occurred_at': '2026-10-01T12:00:00+00:00'}
        self.p.record(event)
        self.p.record(event)
        self.assertEqual(self.p.status()['points'], 0)
        self.p.correct({'expected_version': 2, 'event_id': 'e', 'reason': 'Correção', 'reported_minutes': 20})
        self.assertEqual(self.p.status()['reported_minutes'], 20)
        with self.assertRaises(ValueError): self.p.configure({'expected_version': 2, 'mode': 'off'})
        self.p.configure({'expected_version': 3, 'mode': 'off'})
        self.assertIsNone(self.p.status()['reported_minutes'])
        self.p.configure({'expected_version': 4, 'mode': 'tracking'})
        self.assertEqual(self.p.status()['reported_minutes'], 20)
        self.assertEqual(len(self.p.history()), 5)

    def test_practice_evidence_and_revocation(self):
        practice = Practice(self.root)
        s = practice.start('rh', 'coach', short=True)
        sid, q = s['session_id'], s['question']['id']
        practice.answer(sid, q, 'Minha resposta', origin='person', user_confirmation='Fui eu', attempt_id='a')
        practice.feedback(sid, q, 1, 'Resposta clara', 'Melhorar contexto', 'Explicar', 'Ensaiar')
        self.p.configure({'expected_version': 0, 'mode': 'points'})
        source = {'kind': 'practice', 'session_id': sid, 'question_id': q, 'version': 1}
        e = {'expected_version': 1, 'event_id': 'e', 'activity': 'treino', 'source': source, 'user_confirmation': 'Sim', 'reported_minutes': None, 'occurred_at': '2026-10-01T12:00:00+00:00'}
        self.p.record(e)
        with self.assertRaises(ValueError): self.p.record(dict(e, expected_version=2, event_id='other'))
        m = {'expected_version': 2, 'milestone_id': 'm', 'kind': 'learning', 'title': 'Clareza', 'criterion': 'Resposta clara', 'event_ids': ['e'], 'assessment': 'Resposta clara', 'evidence': {'basis': 'observation', 'event_id': 'e', 'answer_excerpt': 'Minha resposta', 'feedback_excerpt': 'inventado'}}
        with self.assertRaises(ValueError): self.p.milestone(m)
        m['evidence']['feedback_excerpt'] = 'Resposta clara'
        self.p.milestone(m)
        self.assertEqual(self.p.status()['points'], 10)
        practice.feedback(sid, q, 1, 'Outro feedback', 'Contexto', 'Explicar', 'Ensaiar')
        self.assertTrue(self.p.status()['milestones'][0]['needs_review'])
        self.p.correct({'expected_version': 3, 'event_id': 'e', 'reason': 'Engano', 'revoked': True})
        self.assertEqual(self.p.status()['points'], 0)
        self.assertTrue(self.p.status()['milestones'][0]['needs_review'])

    def test_comparison_requires_previous_attempt_independently_of_wording(self):
        """Evidence requirements follow structured intent rather than keyword guesses."""
        practice = Practice(self.root)
        s = practice.start('rh', 'coach', short=True)
        sid, q = s['session_id'], s['question']['id']
        practice.answer(sid, q, 'Minha resposta', origin='person', user_confirmation='Fui eu', attempt_id='a')
        practice.feedback(sid, q, 1, 'Resposta clara', 'Contexto', 'Explicar', 'Ensaiar')
        self.p.configure({'expected_version': 0, 'mode': 'achievements'})
        self.p.record({'expected_version': 1, 'event_id': 'e', 'activity': 'practice',
            'source': {'kind': 'practice', 'session_id': sid, 'question_id': q, 'version': 1},
            'user_confirmation': 'Eu ensaiei', 'reported_minutes': None, 'occurred_at': '2026-11-09T12:00:00+00:00'})
        before = self.p.get()
        with self.assertRaises(ValueError):
            self.p.milestone({'expected_version': 2, 'milestone_id': 'm', 'kind': 'learning',
                'title': 'Clareza', 'criterion': 'Expor o resultado', 'event_ids': ['e'],
                'assessment': 'A resposta está mais precisa que a anterior.',
                'evidence': {'basis': 'comparison', 'event_id': 'e', 'answer_excerpt': 'Minha resposta', 'feedback_excerpt': 'Resposta clara'}})
        self.assertEqual(self.p.get(), before)
        self.assertEqual(self.p.status()['unreported_time_count'], 1)

    def test_unconfirmed_origins_and_invalid_inputs_do_not_change_progress(self):
        practice = Practice(self.root)
        s = practice.start('rh', 'coach', short=True)
        sid, q = s['session_id'], s['question']['id']
        practice.answer(sid, q, 'Resposta desconhecida')
        practice.answer(sid, q, 'Resposta do agente', origin='agent', attempt_id='agent')
        self.p.configure({'expected_version': 0, 'mode': 'points'})
        for version in (1, 2):
            event = {'expected_version': 1, 'event_id': str(version), 'activity': 'treino', 'source': {'kind': 'practice', 'session_id': sid, 'question_id': q, 'version': version}, 'user_confirmation': 'Sim', 'reported_minutes': 5, 'occurred_at': '2026-10-01T12:00:00+00:00'}
            with self.assertRaises(ValueError): self.p.record(event)
        with self.assertRaises(ValueError): self.p.configure({'expected_version': True, 'mode': 'points'})
        self.assertEqual(self.p.status()['practice_count'], 0)
        self.assertEqual(self.p.get()['version'], 1)

    def test_duration_correction_requires_review_of_related_milestone(self):
        """A criterion supported by the old duration cannot stay silently current."""
        self.p.configure({'expected_version': 0, 'mode': 'achievements'})
        self.p.record({'expected_version': 1, 'event_id': 'study', 'activity': 'study',
            'source': {'kind': 'user_report', 'description': 'Estudei um tema fictício'},
            'user_confirmation': 'Eu estudei', 'reported_minutes': 60, 'occurred_at': '2026-11-09T12:00:00-03:00'})
        self.p.milestone({'expected_version': 2, 'milestone_id': 'hour', 'kind': 'participation',
            'title': 'Uma hora de estudo', 'criterion': 'Estudar por 60 minutos', 'event_ids': ['study'],
            'assessment': 'A duração foi informada pela pessoa.'})
        before = self.p.history()[-1]
        self.p.correct({'expected_version': 3, 'event_id': 'study', 'reason': 'Corrigi meu relato', 'reported_minutes': 5})
        self.assertTrue(self.p.status()['milestones'][0]['needs_review'])
        self.assertEqual(self.p.status()['reported_minutes'], 5)
        self.assertEqual(self.p.history()[-2], before)

    def test_skipped_question_is_not_a_confirmed_practice(self):
        """Skipping is a valid choice and cannot become a scored attempt."""
        practice = Practice(self.root)
        s = practice.start('rh', 'coach', short=True)
        sid, qid = s['session_id'], s['question']['id']
        practice.skip(sid, qid)
        self.p.configure({'expected_version': 0, 'mode': 'points'})
        with self.assertRaises(ValueError):
            self.p.record({'expected_version': 1, 'event_id': 'skip', 'activity': 'practice',
                'source': {'kind': 'practice', 'session_id': sid, 'question_id': qid, 'version': 1},
                'user_confirmation': 'Pulei a pergunta', 'reported_minutes': None,
                'occurred_at': '2026-11-09T12:00:00-03:00'})
        self.assertEqual(self.p.status()['practice_count'], 0)
        self.assertEqual(self.p.status()['points'], 0)
