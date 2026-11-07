"""Scripted novice dialogue through the real CLI, without external effects."""
import json
import os
from pathlib import Path
import unittest

from tests import test_job_preparation_journey as preparation


class MenuJourneyTests(unittest.TestCase):
    setUp = preparation.PreparationJourneyTests.setUp
    call = preparation.PreparationJourneyTests.call
    say = preparation.PreparationJourneyTests.say
    next_day = preparation.PreparationJourneyTests.next_day

    def tearDown(self):
        """Export optional fictional dialogue evidence outside the candidate workspace."""
        destination = os.environ.get('JOB_MENU_REPORT')
        if destination:
            folder = Path(destination) / self._testMethodName
            folder.mkdir(parents=True, exist_ok=False)
            (folder / 'evidence.json').write_text(json.dumps({
                'scope': 'Real CLI; scripted fictional answers; simulated clock; network and subprocesses blocked.',
                'calls': self.calls, 'dialogue': self.turns,
            }, ensure_ascii=False, indent=2), encoding='utf-8')

    def test_import_can_resume_without_uploaded_file(self):
        """A pending import resumes by requesting the file without unrelated setup."""
        self.call('intake', 'choose', data={'mode': 'import', 'route': 'curriculum'})
        result = self.call('start')
        self.assertEqual(result['next_step'], 'curriculum_input')
        self.assertIn('Anexe', result['message'])
        self.assertNotIn('model_setup', result)

    def test_next_day_curriculum_names_saved_activity_without_repeating_answers(self):
        """Returning to a partial CV offers a choice without writing or resuming work."""
        self.say(self.call('start')['message'], 'Quero criar meu currículo.')
        self.call('menu', '--choose', 'CURRÍCULO', '--remember')
        self.call('intake', 'choose', data={'mode': 'create', 'route': 'curriculum'})
        self.call('intake', 'answer', data={'field': 'education', 'text': 'Ensino médio fictício concluído em 2024.'})
        self.call('stop')
        self.next_day()
        db = self.root / '.job/control.sqlite3'
        before = db.read_bytes()
        state = self.call('start')
        self.assertIn('Currículo', state.get('welcome_back') or '')
        self.assertIn('menu', state['resume_options'])
        self.assertEqual(state['question']['field'], 'experience')
        plain = self.call('start', plain=True)
        self.assertIn('Currículo', plain)
        self.assertNotIn(state['question']['question'], plain)
        self.assertEqual(db.read_bytes(), before)
        self.say(plain, 'Continuar meu currículo, sem enviar nada.')
        self.assertIsNone(self.call('start', '--focus', 'curriculum')['welcome_back'])
        self.assertTrue(self.call('status')['control']['stopped'])
        self.assertEqual(self.call('intake', 'status')['question']['field'], 'experience')

    def test_next_day_search_and_invalid_choice_preserve_career_and_stop(self):
        """A chosen search survives restart while invalid or preview choices do not switch it."""
        self.call('menu', '--choose', '3', '--remember')
        career = self.call('career', 'start', data={})
        career = self.call('career', 'answer', data={'id': career['id'], 'expected_version': career['version'],
            'field': 'goal', 'value': 'Quero comparar atendimento e administração.'})
        self.say('Sua resposta no guia está salva.', 'Agora quero só ver vagas de atendimento.')
        self.call('menu', '--choose', 'vagas', '--remember')
        self.call('profile', 'answer', 'preferences', data={'field': 'roles', 'value': ['Atendimento']})
        self.call('profile', 'answer', 'preferences', data={'field': 'modalities', 'value': []})
        self.call('stop')
        self.next_day()
        self.assertIsNone(self.call('menu', '--choose', '99', '--remember')['selected'])
        self.call('menu', '--choose', 'currículo')
        db = self.root / '.job/control.sqlite3'
        before = db.read_bytes()
        state = self.call('start')
        self.assertIn('Busca de vagas', state.get('welcome_back') or '')
        self.assertEqual(state['next_step'], 'sources')
        self.assertIn('menu', state['resume_options'])
        self.assertEqual(db.read_bytes(), before)
        self.assertEqual(self.call('career', 'status')['session'], career)
        self.assertTrue(self.call('status')['control']['stopped'])
        self.assertFalse(self.call('profile', 'show')['sections'].get('identity'))
        self.assertEqual(self.call('status')['counts']['actions'], {})

    def test_deferred_interview_returns_without_reasking_saved_answer(self):
        """An unfinished interview retains its answer and waits for an explicit local resume."""
        self.call('menu', '--choose', '2', '--remember')
        session = self.call('practice', 'start', data={'track': 'rh', 'mode': 'coach', 'short': True})
        answer = {'session_id': session['session_id'], 'question_id': session['question']['id'],
                  'text': 'Ajudei a organizar pedidos em um projeto voluntário fictício.'}
        self.call('practice', 'answer', data=answer)
        self.call('practice', 'choose', data={'decision': 'later'})
        self.call('menu', '--choose', 'carreira', '--remember')
        self.call('stop')
        self.next_day()
        self.say('Seu treino e sua resposta ficaram salvos.', 'Quero voltar às entrevistas.')
        before = self.call('practice', 'show')
        result = self.call('menu', '--choose', 'entrevistas', '--remember')
        self.assertIsNone(result['question'])
        self.assertNotIn(session['question']['question'], result['message'])
        self.assertEqual(self.call('practice', 'show'), before)
        self.assertIsNone(self.call('start', '--focus', 'practice')['question'])
        self.say(result['message'], 'Continuar o treino que deixei para depois.')
        self.call('practice', 'choose', data={'decision': 'now'})
        resumed = self.call('practice', 'status')
        self.assertEqual(resumed['session_id'], session['session_id'])
        self.assertEqual(resumed['next_step'], 'feedback')
        self.assertEqual(resumed['question']['attempt']['text'], answer['text'])
        self.assertNotIn(session['question']['question'], self.call('practice', 'status', plain=True))
        self.assertIsNone(self.call('start', '--focus', 'practice')['question'])
        self.assertTrue(self.call('status')['control']['stopped'])

    def test_career_pause_survives_menu_switch_and_local_resume(self):
        """Resuming a saved career guide preserves its answers and the global stop."""
        self.call('menu', '--choose', 'carreira', '--remember')
        career = self.call('career', 'start', data={})
        career = self.call('career', 'answer', data={'id': career['id'], 'expected_version': career['version'],
            'field': 'goal', 'value': 'Não sei ainda que área escolher.'})
        career = self.call('career', 'pause', data={'id': career['id'], 'expected_version': career['version']})
        self.call('menu', '--choose', '1', '--remember')
        self.call('stop')
        self.next_day()
        selected = self.call('menu', '--choose', 'guia de carreira', '--remember')
        self.assertIsNone(selected['question'])
        self.assertIn('pausado', selected['message'])
        self.say(selected['message'], 'Continuar meu guia de carreira.')
        self.call('career', 'resume', data={'id': career['id'], 'expected_version': career['version']})
        self.assertEqual(self.call('start')['question']['field'], 'priorities')
        self.assertTrue(self.call('status')['control']['stopped'])

    def test_explicit_preparation_takes_priority_over_saved_career(self):
        """Read-only explicit preparation overrides a saved career route for this call."""
        self.call('career', 'start', data={})
        self.assertEqual(self.call('start')['next_step'], 'career_guidance')
        self.assertNotEqual(self.call('start', '--focus', 'prepare')['next_step'], 'career_guidance')

    def test_preparation_choice_survives_next_day_without_reimporting_cv(self):
        """A novice can leave search for full preparation and resume existing work."""
        self.call('intake', 'choose', data={'mode': 'create', 'route': 'curriculum'})
        self.call('intake', 'answer', data={'field': 'experience', 'text': 'Experiência fictícia em atendimento.'})
        draft = self.call('resume', 'draft', data={'label': 'Exemplo',
            'markdown': preparation.CV, 'fact_ids': self.call('intake', 'status')['fact_ids']})
        self.call('resume', 'approve', draft['id'])
        self.call('career', 'start', data={})
        self.call('menu', '--choose', 'busca', '--remember')
        self.call('stop')
        before = self.call('intake', 'status')
        checkpoint = self.call('checkpoint', 'show')
        self.say('A busca está salva.', 'Quero preparar tudo para me candidatar depois.')
        preview = self.call('menu', '--choose', 'preparo completo')
        self.assertEqual(preview['next_step'], 'identity')
        self.assertEqual(self.call('start')['next_step'], 'preferences')
        chosen = self.call('menu', '--choose', 'prepare', '--remember')
        self.assertEqual(chosen['next_step'], 'identity')
        self.next_day()
        self.assertEqual(self.call('start')['next_step'], 'identity')
        self.assertEqual(self.call('intake', 'status'), before)
        self.assertEqual(self.call('checkpoint', 'show'), checkpoint)
        self.assertEqual(self.call('resume', 'show', draft['id'])['status'], 'approved')
        self.assertTrue(self.call('status')['control']['stopped'])

    def test_novice_curriculum_practice_career_and_next_day(self):
        """Exercise fictional novice choices, optional training and next-day continuity."""
        self.say(self.call('menu', plain=True), 'Não sei usar isso. Quero só arrumar meu currículo.')
        entry = self.call('menu', '--choose', 'currículo')
        self.assertNotIn('model_setup', entry)
        self.assertFalse((self.root / '.job').exists())
        self.say(entry['message'], 'Não tenho arquivo. Pode me ajudar a criar.')
        self.call('intake', 'choose', data={'mode': 'create', 'route': 'curriculum'})
        answers = [
            ('education', 'Curso fictício de Sistemas de Informação concluído em 2023.'),
            ('experience', 'Empresa Exemplo, desenvolvimento de formulários com React entre 2023 e 2025.'),
            ('skills', 'React, TypeScript e Git. Projeto pessoal fictício de organização de tarefas.'),
            ('languages', 'Português nativo.'), ('extra', None),
        ]
        for field, value in answers:
            state = self.call('start')
            self.assertEqual(state['question']['field'], field)
            self.say(state['message'], value or 'Não tenho mais nada para acrescentar.')
            self.call('intake', 'answer', data={'field': field, 'text': value})
        self.assertEqual(self.call('start')['next_step'], 'resume_approval')
        self.say('Qual nome e contato quer colocar no documento?', 'Marina Exemplo, marina@example.invalid.')
        draft = self.call('resume', 'draft', data={'label': 'Frontend', 'markdown': preparation.CV,
            'fact_ids': self.call('intake', 'status')['fact_ids']})
        self.assertTrue(self.call('resume', 'check', draft['id'])['passed'])
        self.say(preparation.CV, 'Pode aprovar. Só quero os arquivos, sem enviar.')
        self.call('resume', 'approve', draft['id'])
        self.assertEqual(self.call('start')['next_step'], 'curriculum_complete')
        profile = self.call('profile', 'show')
        self.assertFalse(profile.get('approved_version'))
        self.assertFalse(profile['sections'].get('connections'))
        self.assertFalse(profile['sections'].get('permissions'))
        self.say('Seu currículo está pronto. Pode escolher outra atividade no menu.', 'Agora quero treinar entrevista.')
        self.call('menu', '--choose', '2')
        session = self.call('practice', 'start', data={'track': 'rh', 'mode': 'coach'})
        self.assertEqual(self.call('start')['next_step'], 'interview_preparation')
        self.say(session['message'], 'Vou parar e continuar amanhã.')
        self.call('stop')
        self.next_day()
        self.call('menu')
        self.assertTrue(self.call('status')['control']['stopped'])
        self.say('Seu treino está salvo. Podemos continuar ou escolher outra atividade.', 'Continuar.')
        self.call('resume-work')
        self.assertEqual(self.call('practice', 'status')['session_id'], session['session_id'])
        self.say('Retomamos a pergunta salva.', 'Antes quero entender que carreira seguir.')
        self.call('menu', '--choose', '3')
        self.call('career', 'start', data={})
        self.assertEqual(self.call('start')['next_step'], 'career_guidance')
        self.assertEqual(self.call('resume', 'show', draft['id'])['status'], 'approved')
        self.assertEqual(self.call('practice', 'status')['session_id'], session['session_id'])
        self.assertEqual(self.call('status')['counts']['actions'], {})

    def test_novice_public_search_without_contact_and_safe_resume(self):
        """Search needs only minimal preferences and renewed consent after a stop."""
        self.say(self.call('menu')['message'], 'Quero só ver vagas, sem cadastrar meu e-mail.')
        state = self.call('menu', '--choose', 'vagas', '--remember')
        for field, value, words in [('roles', ['Atendimento'], 'Atendimento ao público.'),
                                    ('modalities', [], 'Não tenho preferência.')]:
            self.assertEqual(state['question']['field'], field)
            self.say(state['message'], words)
            self.call('profile', 'answer', 'preferences', data={'field': field, 'value': value})
            state = self.call('start')
        self.assertEqual(state['next_step'], 'sources')
        self.say(state['message'], 'Use apenas https://vagas.example.invalid/atendimento')
        self.call('profile', 'answer', 'sources', data={'field': 'urls', 'value': ['https://vagas.example.invalid/atendimento']})
        state = self.call('start', '--focus', 'search')
        self.assertEqual(state['next_step'], 'search_scope_confirmation')
        self.say(state['message'], 'Pode consultar resultados, paginação e detalhes dentro desse caminho para atendimento, sem preferência de modalidade.')
        scope = self.call('research-scope', 'grant', data={**state['scope_request'],
            'question': 'Quais vagas públicas de atendimento, sem preferência de modalidade aparecem nesta página?',
            'user_confirmation': 'Pode consultar resultados, paginação e detalhes dentro desse caminho para atendimento, sem preferência de modalidade.'})
        ready = self.call('start', '--focus', 'search')
        self.assertEqual(ready['next_step'], 'search_ready')
        check = {'scope_id': scope['id'], 'expected_version': scope['version'], 'purpose': scope['purpose'],
                 'target': scope['target'], 'url': scope['urls'][0]}
        self.assertTrue(self.call('research-scope', 'check', data=check)['allowed'])
        self.assertFalse(self.call('research-scope', 'check', data={**check, 'url': 'https://outro.example.invalid/'})['allowed'])
        self.call('stop')
        self.next_day()
        self.call('menu')
        self.assertEqual(self.call('start')['next_step'], 'search_paused')
        self.call('resume-work')
        self.assertFalse(self.call('research-scope', 'check', data=check)['allowed'])
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_scope_confirmation')
        profile = self.call('profile', 'show')
        self.assertFalse(profile['sections'].get('identity'))
        self.assertFalse(profile['sections'].get('connections'))
        self.assertFalse(profile.get('approved_version'))
        self.assertEqual(self.call('status')['counts']['actions'], {})


if __name__ == '__main__':
    unittest.main()
