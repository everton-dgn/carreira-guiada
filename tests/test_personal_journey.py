"""Fictional novice journeys through real CLI processes with network denied."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_job_preparation_journey as preparation
from tests import test_job_workflow as support
from tests.test_terminal import Stream, flat
from scripts.job.planning import PersonalPlan
from scripts.job.terminal import render


class PersonalJourneyTests(unittest.TestCase):
    """Exercise optional planning, human practice and resumption independently."""
    setUp = preparation.PreparationJourneyTests.setUp
    call = preparation.PreparationJourneyTests.call
    say = preparation.PreparationJourneyTests.say
    next_day = preparation.PreparationJourneyTests.next_day

    def tearDown(self):
        """Export fictional transcripts only when a maintainer requests evidence."""
        destination = os.environ.get('JOB_PERSONAL_REPORT')
        if destination:
            folder = Path(destination) / self._testMethodName
            folder.mkdir(parents=True, exist_ok=False)
            (folder / 'evidence.json').write_text(json.dumps({
                'scope': 'Real CLI; scripted fictional dialogue; no network or real sends.',
                'calls': self.calls, 'dialogue': self.turns,
            }, ensure_ascii=False, indent=2), encoding='utf-8')

    def action(self, plan, ident, minutes, title='Ensaiar minha apresentação'):
        """Store a concrete fictional action within one explicitly chosen week."""
        return self.call('plan', 'action', data={'id': plan['id'], 'expected_version': plan['version'],
            'action': {'id': ident, 'activity': 'practice', 'title': title,
                'reason': 'Conseguir explicar minha experiência com clareza.',
                'criterion': 'Responder à pergunta e conferir uma sugestão de melhoria.',
                'estimated_minutes': minutes, 'period': '2026-11-09',
                'smaller_step': 'Ensaiar só a primeira frase por cinco minutos.',
                'if_then': 'Se eu estiver cansada, faço apenas a primeira frase.'}})

    def test_new_person_can_inspect_both_routes_without_onboarding_or_writes(self):
        """The new choices are optional and discoverable with no private profile."""
        preparation.PreparationJourneyTests.test_external_access_guard(self)
        more = self.call('menu', '--choose', '5')
        self.assertTrue({'plan', 'progress'} <= {item['focus'] for item in more['choices']})
        for words, focus in [('meu plano', 'plan'), ('minha evolução', 'progress')]:
            value = self.call('menu', '--choose', words)
            self.assertEqual(value['view'], focus)
            self.assertEqual(value['session']['activity'], focus)
            self.assertFalse(value['automatic_execution_started'])
            self.assertNotIn('email', value['question']['question'])
            self.assertIn('question', value['question'])
            self.call('start', '--focus', focus, plain=True)
        self.assertFalse((self.root / '.job').exists())

    def test_nina_budget_switch_pause_and_return_after_two_weeks(self):
        """Nina keeps a smaller next step and her practice after a long pause."""
        self.say(self.call('menu', '--choose', 'meu plano', '--remember')['message'],
                 'Quero uma vaga de atendimento. Sou Nina, pessoa fictícia, e tenho 90 minutos por semana.')
        plan = self.call('plan', 'start', data={'direction': 'Buscar uma vaga de atendimento',
            'weekly_minutes': 90, 'cycle': {'title': 'Preparar uma apresentação com exemplos reais', 'review_on': '2026-11-23'}})
        for ident, minutes in [('a', 20), ('b', 15), ('c', 15), ('d', 10)]:
            plan = self.action(plan, ident, minutes)
        shown = self.call('plan', 'show')
        self.assertEqual(shown['budget']['periods'][0]['planned_minutes'], 60)
        self.assertEqual(shown['budget']['periods'][0]['remaining_minutes'], 30)
        self.assertIn('60 min planejados; 30 min livres', self.call('plan', 'show', '--plain', plain=True))
        self.assertIn('Ensaiar minha apresentação', self.call('status', '--focus', 'plan')['message'])
        self.call('menu', '--choose', 'entrevistas', '--remember')
        practice = self.call('practice', 'start', data={'track': 'presentation', 'mode': 'coach', 'short': True})
        sid, qid = practice['session_id'], practice['question']['id']
        self.call('practice', 'answer', data={'session_id': sid, 'question_id': qid,
            'text': 'Atendi clientes em uma empresa fictícia e organizei pedidos.',
            'attempt_id': 'nina-1', 'origin': 'person', 'user_confirmation': 'Eu mesma ensaiei esta resposta.'})
        self.call('stop')
        plan = self.call('plan', 'pause', data={'id': plan['id'], 'expected_version': plan['version']})
        self.call('menu', '--choose', 'plano', '--remember')
        self.time = '2026-11-23T18:00:00-03:00'
        before = (self.root / '.job/control.sqlite3').read_bytes()
        result = self.call('start')
        self.assertEqual(result['state'], 'paused')
        self.assertIsNone(result['next_action'])
        self.assertIn('pausado', result['message'])
        self.assertTrue(result['session']['campaign_stopped'])
        self.assertEqual((self.root / '.job/control.sqlite3').read_bytes(), before)
        self.say(result['message'], 'Hoje só tenho cinco minutos. Quero retomar meu plano.')
        self.call('plan', 'resume', data={'id': plan['id'], 'expected_version': plan['version']})
        self.assertIn('cinco minutos', self.call('plan', 'show')['next_action']['smaller_step'])
        self.assertEqual(self.call('practice', 'status')['next_step'], 'feedback')
        self.assertTrue(self.call('status')['control']['stopped'])
        self.assertEqual(self.call('progress', 'status')['mode'], 'off')

    def test_personal_status_reports_progress_only_after_a_record_is_saved(self):
        """A first visit or route choice cannot become a confirmed advance."""
        for focus in ('plan', 'progress'):
            with self.subTest(focus=focus):
                self.call('menu', '--choose', focus, '--remember')
                status = self.call('status', '--focus', focus)
                self.assertIsNone(status['session']['advance'])
                self.assertNotIn('Último avanço confirmado:', status['message'])
                self.assertTrue(status['session']['next_action'])
        self.call('plan', 'start', data={'direction': 'Preparar minha apresentação'})
        self.call('progress', 'configure', data={'expected_version': 0, 'mode': 'off'})
        for focus in ('plan', 'progress'):
            with self.subTest(saved_focus=focus):
                status = self.call('status', '--focus', focus)
                self.assertEqual(status['session']['advance'], 'Há um registro salvo desta atividade.')
                self.assertIn('Último avanço confirmado:', status['message'])
                self.assertTrue(status['session']['next_action'])

    def test_jo_unknown_capacity_then_over_budget_preserves_completed_action(self):
        """Jo can begin without an estimate and reduce future work explicitly."""
        self.call('menu', '--choose', 'plano', '--remember')
        plan = self.call('plan', 'start', data={'direction': 'Explorar trabalho administrativo'})
        plan = self.action(plan, 'a', None)
        shown = self.call('plan', 'show')
        self.assertIsNone(shown['budget']['periods'][0]['planned_minutes'])
        self.assertIn('estimativa incompleta', shown['message'])
        plan = self.action(plan, 'a', 80)
        plan = self.call('plan', 'update', data={'id': plan['id'], 'expected_version': plan['version'], 'weekly_minutes': 120})
        self.assertEqual(self.call('plan', 'show')['budget']['periods'][0]['remaining_minutes'], 40)
        plan = self.call('plan', 'transition', data={'id': plan['id'], 'expected_version': plan['version'],
            'action_id': 'a', 'state': 'completed', 'evidence': {'kind': 'user_report',
                'description': 'Jo confirmou que ensaiou e conferiu a sugestão.',
                'criterion': 'Responder à pergunta e conferir uma sugestão de melhoria.'}})
        plan = self.action(plan, 'b', 60)
        plan = self.call('plan', 'update', data={'id': plan['id'], 'expected_version': plan['version'], 'weekly_minutes': 30})
        shown = self.call('plan', 'show')
        self.assertEqual(shown['actions'][0]['state'], 'completed')
        self.assertEqual(shown['budget']['periods'][0]['over_by_minutes'], 30)
        self.assertIn('reduzir ou adiar', shown['message'])
        self.call('plan', 'update', data={'id': plan['id'], 'expected_version': 1, 'weekly_minutes': 300}, success=False)
        self.assertEqual(self.call('plan', 'get', data={})['weekly_minutes'], 30)

    def test_confirmed_practice_is_optional_idempotent_correctable_and_resumable(self):
        """Points reflect distinct human attempts and survive absence without loss."""
        self.call('menu', '--choose', 'evolução', '--remember')
        self.call('progress', 'configure', data={'expected_version': 0, 'mode': 'points'})
        practice = self.call('practice', 'start', data={'track': 'rh', 'mode': 'coach', 'short': True})
        sid, qid = practice['session_id'], practice['question']['id']
        answer = {'session_id': sid, 'question_id': qid, 'text': 'Quero trabalhar com atendimento ao cliente.',
                  'attempt_id': 'jo-1', 'origin': 'person', 'user_confirmation': 'Ensaiei esta resposta.'}
        self.call('practice', 'answer', data=answer)
        self.call('practice', 'answer', data=answer)
        event = {'expected_version': 1, 'event_id': 'jo-practice-1', 'activity': 'practice',
            'source': {'kind': 'practice', 'session_id': sid, 'question_id': qid, 'version': 1},
            'user_confirmation': 'Sim, eu ensaiei.', 'reported_minutes': 5, 'occurred_at': self.time}
        self.call('progress', 'record', data=event)
        self.call('progress', 'record', data=event)
        self.assertEqual(self.call('progress', 'status')['points'], 10)
        self.call('menu', '--choose', 'evolução', '--remember')
        self.time = '2026-11-23T18:00:00-03:00'
        result = self.call('start')
        self.assertEqual(result['points'], 10)
        self.assertIn('Minha evolução', result['welcome_back'])
        self.call('progress', 'correct', data={'expected_version': 2, 'event_id': 'jo-practice-1',
            'reason': 'Conferi a duração.', 'reported_minutes': 4})
        self.assertEqual(self.call('progress', 'status')['reported_minutes'], 4)
        self.call('progress', 'configure', data={'expected_version': 3, 'mode': 'off'})
        self.assertIsNone(self.call('progress', 'status')['points'])
        self.assertEqual(self.call('practice', 'show')['sessions'][0]['questions'][0]['attempts'][0]['text'], answer['text'])

    def test_completed_plan_never_resolves_an_uncertain_application(self):
        """A planning claim cannot grant permission or overwrite an external result."""
        fx = support.WorkflowTests()
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        job, resume = fx.ready()
        action = fx.apply(job, resume)
        fx.done(action['action_id'], outcome='uncertain')
        before = fx.wf.state()
        service = PersonalPlan(fx.root)
        plan = service.start({'direction': 'Organizar minha busca'})
        plan = service.action({'id': plan['id'], 'expected_version': plan['version'], 'action': {
            'id': 'check', 'activity': 'search', 'title': 'Conferir candidatura', 'reason': 'Evitar duplicidade',
            'criterion': 'Conferir o resultado', 'estimated_minutes': 10, 'period': None}})
        service.transition({'id': plan['id'], 'expected_version': plan['version'], 'action_id': 'check',
            'state': 'completed', 'evidence': {'kind': 'user_report', 'description': 'Relato fictício', 'criterion': 'Conferir o resultado'}})
        after = fx.wf.state()
        self.assertEqual(after['control'], before['control'])
        self.assertEqual(after['counts'], before['counts'])
        with self.assertRaises(ValueError):
            fx.apply(job, resume)

    def test_career_context_is_offered_without_assuming_minutes_or_creating_plan(self):
        """A confirmed goal is reused while free-form availability stays unparsed."""
        career = self.call('career', 'start', data={})
        career = self.call('career', 'answer', data={'id': career['id'], 'expected_version': career['version'],
            'field': 'goal', 'value': 'Explorar atendimento ao cliente'})
        before = (self.root / '.job/control.sqlite3').read_bytes()
        result = self.call('plan', 'show')
        self.assertIn('Explorar atendimento ao cliente', result['question']['question'])
        self.assertEqual(result['suggested_basis'][0]['version'], career['version'])
        self.assertIsNone(result['budget'])
        self.assertFalse(result['exists'])
        self.assertEqual((self.root / '.job/control.sqlite3').read_bytes(), before)

    def test_plain_output_keeps_the_action_estimate_and_if_then_plan(self):
        """An accessibility preference preserves the exact practical agreement."""
        plan = self.call('plan', 'start', data={})
        self.call('plan', 'action', data={'id': plan['id'], 'expected_version': plan['version'], 'action': {
            'id': 'a', 'activity': 'practice', 'title': 'Treinar', 'reason': 'Explicar minha experiência',
            'criterion': 'Ensaiar uma resposta', 'estimated_minutes': 20, 'period': None,
            'if_then': 'Se eu me cansar, paro depois da primeira frase.'}})
        plain = self.call('plan', 'show', '--plain', plain=True)
        self.assertIn('Estimativa: 20 min', plain)
        self.assertIn('Se eu me cansar, paro depois da primeira frase.', plain)

    def test_return_shows_completed_and_deferred_goals_without_restarting_them(self):
        """A novice can identify saved work and choose what to do with a deferral."""
        self.time = '2026-11-09T18:00:00-03:00'
        self.call('menu', '--choose', 'meu plano', '--remember')
        plan = self.call('plan', 'start', data={'direction': 'Preparar entrevistas de atendimento', 'weekly_minutes': 60})
        plan = self.action(plan, 'intro', 20, 'Ensaiar minha apresentação')
        plan = self.action(plan, 'example', 20, 'Preparar um exemplo de atendimento')
        plan = self.call('plan', 'transition', data={'id': plan['id'], 'expected_version': plan['version'],
            'action_id': 'intro', 'state': 'completed', 'evidence': {'kind': 'user_report',
                'description': 'Lia Exemplo confirmou o ensaio e a revisão da sugestão.',
                'criterion': 'Responder à pergunta e conferir uma sugestão de melhoria.'}})
        plan = self.call('plan', 'transition', data={'id': plan['id'], 'expected_version': plan['version'],
            'action_id': 'example', 'state': 'deferred'})
        plan = self.call('plan', 'pause', data={'id': plan['id'], 'expected_version': plan['version']})
        self.call('stop')
        self.call('menu', '--choose', 'minha evolução', '--remember')
        self.call('menu', '--choose', 'meu plano', '--remember')
        self.next_day()
        before = (self.root / '.job/control.sqlite3').read_bytes()
        paused = self.call('start')
        self.assertEqual(paused['state'], 'paused')
        self.assertIn('Concluída: Ensaiar minha apresentação', paused['message'])
        self.assertIn('Adiada: Preparar um exemplo de atendimento', paused['message'])
        self.assertIsNone(paused['next_action'])
        self.assertEqual((self.root / '.job/control.sqlite3').read_bytes(), before)
        self.call('plan', 'resume', data={'id': plan['id'], 'expected_version': plan['version']})
        resumed = self.call('start')
        self.assertIn('adiada', resumed['question']['question'])
        self.assertIn('retomar', resumed['question']['question'])
        self.assertIsNone(resumed['next_action'])
        self.assertTrue(resumed['session']['campaign_stopped'])
        self.assertEqual([a['state'] for a in resumed['actions']], ['completed', 'deferred'])
        self.assertIn('Preparar um exemplo de atendimento', self.call('start', '--plain', plain=True))
        with patch.dict(os.environ, {'TERM': 'xterm-256color'}):
            for width in (42, 100):
                output = render(resumed, resumed['message'], width=width, stream=Stream())
                self.assertIn(flat('Concluída: Ensaiar minha apresentação'), flat(output))
                self.assertIn(flat('Adiada: Preparar um exemplo de atendimento'), flat(output))

    def test_finished_actions_offer_cycle_review_instead_of_an_empty_plan_prompt(self):
        """Completing the agreed work offers review without claiming a job outcome."""
        self.call('menu', '--choose', 'meu plano', '--remember')
        plan = self.call('plan', 'start', data={'direction': 'Preparar minha apresentação'})
        plan = self.action(plan, 'a', 5)
        self.call('plan', 'transition', data={'id': plan['id'], 'expected_version': plan['version'],
            'action_id': 'a', 'state': 'completed', 'evidence': {'kind': 'user_report',
                'description': 'Ensaiei e conferi uma sugestão.',
                'criterion': 'Responder à pergunta e conferir uma sugestão de melhoria.'}})
        self.next_day()
        shown = self.call('start')
        self.assertIn('revisar este ciclo', shown['question']['question'])
        self.assertIn('Concluída: Ensaiar minha apresentação', shown['message'])
        self.assertEqual(shown['state'], 'active')
        self.assertIsNone(shown['next_action'])
        self.assertFalse(shown['automatic_execution_started'])

    def test_reported_study_remains_visible_after_switch_return_and_correction(self):
        """A reported study is visible separately from scored interview attempts."""
        self.time = '2026-11-09T18:00:00-03:00'
        self.call('menu', '--choose', 'minha evolução', '--remember')
        self.call('progress', 'configure', data={'expected_version': 0, 'mode': 'tracking'})
        empty = self.call('start')
        self.assertIn('Ainda não há práticas registradas', empty['message'])
        self.assertNotIn('marco', empty['question']['question'])
        self.assertIn('Minha evolução está salva', empty['welcome_back'])
        event = {'expected_version': 1, 'event_id': 'lia-study', 'activity': 'study',
            'source': {'kind': 'user_report', 'description': 'Estudei organização de pedidos com um exercício fictício.'},
            'user_confirmation': 'Eu estudei hoje por 20 minutos.', 'reported_minutes': 20, 'occurred_at': self.time}
        self.call('progress', 'record', data=event)
        self.call('progress', 'record', data=event)
        self.call('menu', '--choose', 'entrevistas', '--remember')
        self.call('menu', '--choose', 'minha evolução', '--remember')
        self.next_day()
        before = (self.root / '.job/control.sqlite3').read_bytes()
        shown = self.call('start')
        self.assertIn('Atividades relatadas por você: 1', shown['message'])
        self.assertIn(event['source']['description'], shown['message'])
        self.assertNotIn('marco', shown['question']['question'])
        self.assertEqual(shown['practice_count'], 0)
        self.assertEqual(shown['reported_minutes'], 20)
        self.assertIsNone(shown['points'])
        self.assertEqual((self.root / '.job/control.sqlite3').read_bytes(), before)
        with patch.dict(os.environ, {'TERM': 'xterm-256color'}):
            for width in (42, 100):
                output = render(shown, shown['message'], width=width, stream=Stream())
                self.assertIn(flat(event['source']['description']), flat(output))
                self.assertIn(flat('Atividades relatadas por você: 1'), flat(output))
        self.call('progress', 'correct', data={'expected_version': 2, 'event_id': 'lia-study',
            'reason': 'Conferi a duração do exercício.', 'reported_minutes': 15})
        plain = self.call('progress', 'show', '--plain', plain=True)
        self.assertIn('Tempo informado por você: 15 min', plain)
        self.assertIn(event['source']['description'], plain)
        self.call('progress', 'correct', data={'expected_version': 3, 'event_id': 'lia-study',
            'reason': 'O registro era somente um exemplo.', 'revoked': True})
        self.assertNotIn(event['source']['description'], self.call('progress', 'show')['message'])
        self.assertEqual(self.call('progress', 'history')[1]['events'][0]['reported_minutes'], 20)

    def test_lia_practices_a_goal_and_returns_next_day_without_duplicate_points(self):
        """A fictional novice completes one goal, records practice and resumes another."""
        preparation.PreparationJourneyTests.test_external_access_guard(self)
        self.time = '2026-11-09T18:00:00-03:00'
        first = self.call('menu', '--choose', 'meu plano', '--remember')
        self.say(first['message'], 'Quero preparar entrevistas de atendimento. Tenho uma hora por semana.')
        plan = self.call('plan', 'start', data={'direction': 'Preparar entrevistas de atendimento',
            'weekly_minutes': 60, 'cycle': {'title': 'Explicar minha experiência', 'review_on': '2026-11-23'}})
        plan = self.action(plan, 'intro', 20, 'Ensaiar minha apresentação')
        plan = self.action(plan, 'example', 20, 'Preparar um exemplo de atendimento')
        self.say(self.call('plan', 'show')['message'], 'Quero fazer o ensaio agora.')
        self.call('menu', '--choose', 'entrevistas', '--remember')
        practice = self.call('practice', 'start', data={'track': 'presentation', 'mode': 'coach', 'short': True})
        sid, qid = practice['session_id'], practice['question']['id']
        self.say(practice['message'], 'Atendi clientes em uma loja fictícia e organizei os pedidos para evitar esquecimentos.')
        self.call('practice', 'answer', data={'session_id': sid, 'question_id': qid,
            'text': self.turns[-1]['person'], 'attempt_id': 'lia-intro-1', 'origin': 'person',
            'user_confirmation': 'Eu mesma ensaiei esta resposta.'})
        self.call('practice', 'feedback', data={'session_id': sid, 'question_id': qid, 'version': 1,
            'strengths': 'Você explicou que organizava os pedidos.', 'improvements': 'Falta contar um exemplo específico.',
            'suggestion': 'Escolha um pedido e explique como conferiu o resultado.', 'exercise': 'Ensaiar esse exemplo em duas frases.'})
        self.say('Você ensaiou e conferiu a sugestão. Quer marcar esta ação como concluída?', 'Sim. Quero guardar a prática com pontos, sem estimar o tempo.')
        source = {'kind': 'practice', 'session_id': sid, 'question_id': qid, 'version': 1}
        plan = self.call('plan', 'transition', data={'id': plan['id'], 'expected_version': plan['version'],
            'action_id': 'intro', 'state': 'completed', 'evidence': {'kind': 'source', 'source': source,
                'description': 'Lia confirmou o ensaio e a leitura da sugestão.',
                'criterion': 'Responder à pergunta e conferir uma sugestão de melhoria.'}})
        self.call('menu', '--choose', 'minha evolução', '--remember')
        self.call('progress', 'configure', data={'expected_version': 0, 'mode': 'points'})
        event = {'expected_version': 1, 'event_id': 'lia-intro-event', 'activity': 'practice', 'source': source,
            'user_confirmation': 'Eu ensaiei hoje.', 'reported_minutes': None, 'occurred_at': self.time}
        self.call('progress', 'record', data=event)
        self.say(self.call('progress', 'show')['message'], 'Vou parar por hoje. Amanhã quero continuar meu plano.')
        plan = self.call('plan', 'pause', data={'id': plan['id'], 'expected_version': plan['version']})
        self.call('menu', '--choose', 'meu plano', '--remember')
        self.next_day()
        paused = self.call('start')
        self.say(paused['message'], 'Quero retomar. Hoje cabe preparar o exemplo.')
        self.assertEqual(paused['state'], 'paused')
        self.assertIn('Concluída: Ensaiar minha apresentação', paused['message'])
        self.call('plan', 'resume', data={'id': plan['id'], 'expected_version': plan['version']})
        resumed = self.call('start')
        self.assertEqual(resumed['next_action']['id'], 'example')
        self.call('menu', '--choose', 'minha evolução', '--remember')
        self.call('progress', 'record', data=event)
        progress = self.call('start')
        self.assertEqual(progress['practice_count'], 1)
        self.assertEqual(progress['points'], 10)
        self.assertEqual(progress['unreported_time_count'], 1)
        self.assertIn('total está incompleto', progress['message'])
        self.assertFalse(progress['automatic_execution_started'])
        self.assertFalse(self.call('profile', 'status')['approved'])
