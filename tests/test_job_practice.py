import tempfile
import unittest
from pathlib import Path

from scripts.job.practice import Practice


class PracticeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.p = Practice(self.root)

    def test_read_does_not_create_database_and_choice_persists(self):
        self.assertEqual(self.p.status()['phase'], 'idle')
        self.assertFalse((self.root / '.job').exists())
        self.p.choose('skip')
        self.assertEqual(Practice(self.root).status()['decision'], 'skip')

    def test_coach_versions_history_and_completion(self):
        s = self.p.start('rh', 'coach', short=True)
        sid, q = s['session_id'], s['question']['id']
        with self.assertRaises(ValueError):
            self.p.advance(sid, q)
        self.p.answer(sid, q, 'Trabalhei em um projeto fictício.')
        with self.assertRaises(ValueError):
            self.p.advance(sid, q)
        self.p.feedback(sid, q, 1, 'Contexto claro', 'Explique a ação', 'Descreva sua contribuição', 'Pratique uma versão curta')
        self.p.answer(sid, q, 'Contribuí com testes no projeto fictício.')
        with self.assertRaises(ValueError):
            self.p.feedback(sid, q, 1, 'a', 'b', 'c', 'd')
        self.assertEqual(Practice(self.root).status(sid)['next_step'], 'feedback')
        self.p.feedback(sid, q, 2, 'a', 'b', 'c', 'd')
        self.p.advance(sid, q)
        self.p.finish(sid, 'Relatório privado', 'Praticar novamente')
        saved = self.p.get()['sessions'][0]
        self.assertEqual(saved['completion'], 'completed')
        self.assertEqual(len(saved['questions'][0]['attempts']), 2)
        self.p.start('technical', 'coach', short=True)
        self.assertEqual(len(self.p.get()['sessions']), 2)

    def test_mock_holds_feedback_until_end_and_early_is_not_complete(self):
        s = self.p.start('rh', 'mock')
        sid, q = s['session_id'], s['question']['id']
        self.p.answer(sid, q, 'Uma resposta.')
        with self.assertRaises(ValueError):
            self.p.feedback(sid, q, 1, 'a', 'b', 'c', 'd')
        self.p.advance(sid, q)
        with self.assertRaises(ValueError):
            self.p.answer(sid, q, 'Pergunta errada')
        self.p.end_questions(sid)
        self.p.feedback(sid, q, 1, 'a', 'b', 'c', 'd')
        self.p.finish(sid, 'Resumo', 'Praticar')
        self.assertEqual(self.p.get()['sessions'][0]['completion'], 'ended_early')

    def test_skip_hint_and_secrets(self):
        s = self.p.start('system_design', 'coach', short=True)
        sid, q = s['session_id'], s['question']['id']
        self.assertIn('Requisitos', self.p.hint(sid, q)['example'])
        self.assertIn('example', self.p.answer(sid, q, 'Não sei.'))
        with self.assertRaises(ValueError):
            self.p.answer(sid, q, 'senha: segredo')
        self.p.skip(sid, q)
        self.p.advance(sid, q)
        self.p.finish(sid, 'Pergunta pulada', 'Tentar depois')

    def test_coach_can_end_early_after_answer_and_give_feedback(self):
        s = self.p.start('rh', 'coach')
        sid, q = s['session_id'], s['question']['id']
        self.p.answer(sid, q, 'Uma resposta.')
        self.p.end_questions(sid)
        self.p.feedback(sid, q, 1, 'a', 'b', 'c', 'd')
        self.p.finish(sid, 'Resumo', 'Praticar')
        self.assertEqual(self.p.get()['sessions'][0]['completion'], 'ended_early')

    def test_question_selection_context_and_duplicate_answer(self):
        s = self.p.start('behavioral', 'coach', question_ids=['erro'])
        sid, q = s['session_id'], s['question']['id']
        self.assertEqual(q, 'erro')
        self.assertEqual(s['total'], 1)
        answer = 'Corrigi um erro fictício de configuração e acrescentei uma conferência.'
        self.p.answer(sid, q, answer)
        self.p.answer(sid, q, answer)
        self.assertEqual(len(self.p.get()['sessions'][0]['questions'][0]['attempts']), 1)
        self.p.choose('later')
        self.assertEqual(Practice(self.root).status()['decision'], 'later')
        self.assertEqual(Practice(self.root).status()['question']['attempt']['version'], 1)
        self.p.choose('now')
        self.p.feedback(sid, q, 1, 'Assumiu o erro.', 'Falta explicar o efeito observado.', 'Explicar o efeito sem inventar números.', 'Recontar em uma frase.')
        self.p.advance(sid, q)
        result = self.p.finish(sid, 'A resposta mostra responsabilidade; ainda falta explicar o impacto.', 'Praticar um resultado que possa confirmar.')
        self.assertIn('ainda falta', result['message'])
        for track in ('coding', 'system_design'):
            s = self.p.start(track, 'coach', short=True)
            self.assertIn('Exercício fictício:', s['context'])
            self.p.end_questions(s['session_id'])
            self.p.finish(s['session_id'], 'Encerrado sem respostas.', 'Voltar ao enunciado.')

    def test_invalid_track_and_question_selections_are_rejected(self):
        for kwargs in ({'track': []}, {'question_ids': ['ausente']}, {'question_ids': ['erro', 'erro']}, {'question_ids': [{}]}, {'question_ids': []}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.p.start(**{'track': 'behavioral', 'mode': 'coach', **kwargs})
        self.assertFalse((self.root / '.job').exists())

    def test_finish_last_answer_without_advance_and_mock_guidance(self):
        session = self.p.start('rh', 'coach', short=True)
        sid, q = session['session_id'], session['question']['id']
        self.p.answer(sid, q, 'Apresentação fictícia.')
        self.p.feedback(sid, q, 1, 'Contexto.', 'Contribuição.', 'Organizar fatos.', 'Ensaiar.')
        self.assertEqual(self.p.finish(sid, 'Relatório.', 'Próximo treino.')['completion'], 'completed')
        session = self.p.start('rh', 'mock', short=True)
        sid, q = session['session_id'], session['question']['id']
        self.p.answer(sid, q, 'Apresentação fictícia.')
        with self.assertRaisesRegex(ValueError, 'end-questions'):
            self.p.finish(sid, 'Relatório.', 'Próximo treino.')
