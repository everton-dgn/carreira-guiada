"""Regressions for the process after onboarding, with fictional data only."""
from datetime import datetime, timedelta
import socket
import unittest
from unittest.mock import patch

import test_job_workflow as support
from scripts.job.profile import Profile
from scripts.job.records import ledger, mail_coverage


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('Network disabled in simulation'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.fx = support.WorkflowTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.wf, self.root = self.fx.wf, self.fx.root
        self.job, self.resume = self.fx.ready()
        goal = self.wf.state()['goal']
        self.wf.configure_goal({'summary': 'Percurso fictício completo', 'actions': list(support.ACTIONS), 'replace_version': goal['version']})

    def authorize(self, action, **extra):
        return self.wf.authorize({'action': action, 'owner': 'chat:sessao', 'generation': 1,
                                  'channel': {'provider': 'chrome', 'account': 'portal-teste'},
                                  'opportunity_id': self.job, 'user_confirmation': 'Pessoa confirmou esta etapa no cenário fictício', **extra})

    def sent(self):
        action = self.fx.apply(self.job, self.resume)
        self.fx.done(action['action_id'])

    def test_followup_form_is_distinct_from_initial_fill(self):
        initial = self.authorize('fill')
        self.fx.done(initial['action_id'])
        self.sent()
        step = ledger(self.root, 'step', {'job_id': self.job, 'step_key': 'complemento-a', 'kind': 'form', 'summary': 'Informar disponibilidade'})
        followup = self.authorize('fill', step_key='complemento-a')
        self.fx.done(followup['action_id'])
        self.assertNotEqual(initial['dedupe_key'], followup['dedupe_key'])
        self.assertEqual(next(s for s in ledger(self.root, 'steps') if s['id'] == step['id'])['state'], 'completed')
        self.assertEqual(self.wf.state()['ledger']['confirmed'], 1)
        with self.assertRaises(ValueError):
            self.authorize('fill', step_key='complemento-a')

    def test_initial_form_can_be_corrected_before_sending_but_not_after(self):
        first = self.authorize('fill')
        self.fx.done(first['action_id'])
        correction = self.authorize('fill', user_confirmation='Pode corrigir o campo com a informação já confirmada')
        with self.assertRaises(ValueError):
            self.fx.apply(self.job, self.resume)
        self.fx.done(correction['action_id'])
        self.sent()
        with self.assertRaises(ValueError):
            self.authorize('fill')
        self.assertEqual(self.wf.state()['ledger']['confirmed'], 1)

    def test_uncertain_fill_requires_verification_before_retry_or_apply(self):
        action = self.authorize('fill')
        self.fx.done(action['action_id'], outcome='uncertain', evidence_source='agent_report')
        with self.assertRaises(ValueError):
            self.authorize('fill')
        with self.assertRaises(ValueError):
            self.fx.apply(self.job, self.resume)
        self.fx.done(action['action_id'], outcome='not_received')
        retry = self.authorize('fill')
        self.fx.done(retry['action_id'])
        self.sent()

    def test_scheduling_keeps_attendance_pending_and_candidate_can_report_done(self):
        self.sent()
        starts = (self.fx.clock() + timedelta(days=2)).isoformat()
        self.wf.ingest_email({'provider': 'gmail', 'account': 'principal', 'message_id': 'convite-a', 'category': 'interview',
                              'received_at': self.fx.clock().isoformat(), 'opportunity_id': self.job,
                              'link_evidence': 'Processo fictício conferido', 'step_key': 'entrevista-a', 'summary': 'Convite para entrevista'})
        action = self.authorize('schedule', step_key='entrevista-a', schedule={'starts_at': starts})
        self.fx.done(action['action_id'])
        pending = [s for s in ledger(self.root, 'steps') if s['state'] == 'candidate_pending']
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['kind'], 'interview_attendance')
        self.assertEqual(datetime.fromisoformat(pending[0]['due_at']), datetime.fromisoformat(starts))
        self.assertIn('Empresa Exemplo', self.wf.state()['message'])
        self.assertNotIn('Tudo pronto', self.wf.state()['message'])
        with self.assertRaises(ValueError):
            ledger(self.root, 'transition', {'id': pending[0]['id'], 'state': 'completed', 'evidence': 'Agente supôs que terminou'})
        result = ledger(self.root, 'transition', {'id': pending[0]['id'], 'state': 'completed', 'evidence': 'Participação informada pela pessoa', 'user_confirmation': 'A pessoa disse: participei da entrevista'})
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(self.wf.state()['ledger']['confirmed'], 1)

    def test_missing_salary_acceptance_is_local_and_expires_on_material_change(self):
        vacancy = {**support.VACANCY, 'salary': None}
        payload = {'company': 'Empresa Sem Salário', 'title': 'Função sintética', 'portal': 'portal', 'aliases': ['job:portal:salario'],
                   'identity_verified': True, 'evidence': 'Anúncio fictício conferido', 'vacancy': vacancy}
        opportunity = self.wf.opportunity(payload)
        self.assertEqual(opportunity['evaluation']['decision'], 'blocked')
        profile = Profile(self.root).get()
        result = self.wf.decide_opportunity({'opportunity_id': opportunity['opportunity_id'], 'reasons': opportunity['evaluation']['reasons'],
                                            'user_confirmation': 'Pode considerar somente esta vaga sem salário informado'})
        self.assertEqual(result['evaluation']['decision'], 'eligible')
        self.assertEqual(Profile(self.root).get(), profile)
        unchanged = self.wf.opportunity(payload)
        self.assertEqual(unchanged['evaluation']['decision'], 'eligible')
        other = self.wf.opportunity({**payload, 'company': 'Outra Sem Salário', 'aliases': ['job:portal:outra']})
        with self.assertRaises(ValueError):
            self.fx.apply(other['opportunity_id'], self.resume)
        changed = self.wf.opportunity({**payload, 'vacancy': {**vacancy, 'modality': None}})
        self.assertEqual(changed['evaluation']['decision'], 'blocked')
        with self.assertRaisesRegex(ValueError, 'elegibilidade'):
            self.fx.apply(changed['opportunity_id'], self.resume)

    def test_decision_counts_confirmed_and_expires_after_profile_change(self):
        payload = {'company': 'Empresa Sem Salário', 'title': 'Função sintética', 'portal': 'portal',
                   'aliases': ['job:portal:unknown'], 'identity_verified': True, 'evidence': 'Anúncio fictício',
                   'vacancy': {**support.VACANCY, 'salary': None}}
        job = self.wf.opportunity(payload)
        self.wf.decide_opportunity({'opportunity_id': job['opportunity_id'], 'reasons': job['evaluation']['reasons'],
                                   'user_confirmation': 'Pode considerar somente esta vaga sem remuneração publicada'})
        self.fx.done(self.fx.apply(job['opportunity_id'], self.resume)['action_id'])
        self.assertEqual(self.wf.state()['ledger']['eligible_confirmed'], 1)
        profile = Profile(self.root)
        profile.answer('preferences', 'roles', ['Função sintética', 'Outra função'])
        profile.approve(profile.get()['version'])
        self.assertEqual(self.wf.state()['ledger']['confirmed'], 1)
        self.assertEqual(self.wf.state()['ledger']['eligible_confirmed'], 0)

    def test_personal_test_cannot_be_submitted_as_a_form(self):
        self.sent()
        ledger(self.root, 'step', {'job_id': self.job, 'step_key': 'teste-pessoal', 'kind': 'assessment', 'summary': 'Autorrelato'})
        with self.assertRaisesRegex(ValueError, 'formulário complementar'):
            self.authorize('fill', step_key='teste-pessoal')

    def test_schedule_requires_future_time_with_timezone(self):
        self.sent()
        ledger(self.root, 'step', {'job_id': self.job, 'step_key': 'entrevista', 'kind': 'interview', 'summary': 'Entrevista'})
        for starts in ('2020-01-01T10:00:00Z', '2099-01-01T10:00:00'):
            with self.subTest(starts=starts), self.assertRaises(ValueError):
                self.authorize('schedule', step_key='entrevista', schedule={'starts_at': starts})

    def test_decision_cannot_accept_a_discarded_vacancy(self):
        vacancy = self.wf.opportunity({'company': 'Empresa Incompatível', 'title': 'Função sintética', 'portal': 'portal',
                                      'aliases': ['job:portal:incompativel'], 'identity_verified': True, 'evidence': 'Anúncio fictício',
                                      'vacancy': {**support.VACANCY, 'modality': 'onsite'}})
        with self.assertRaises(ValueError):
            self.wf.decide_opportunity({'opportunity_id': vacancy['opportunity_id'], 'reasons': vacancy['evaluation']['reasons'], 'user_confirmation': 'Pode enviar'})

    def test_decision_preserves_salary_floor_and_crossing_range(self):
        profile = Profile(self.root)
        profile.answer('preferences', 'salary.floors', [{'contract': 'CLT', 'amount': 5500, 'currency': 'BRL', 'period': 'month'}])
        profile.approve(profile.get()['version'])
        for maximum, expected in ((5000, 'discarded'), (6000, 'blocked')):
            with self.subTest(maximum=maximum):
                job = self.wf.opportunity({'company': 'Empresa Exemplo', 'title': 'Função sintética', 'portal': 'portal',
                                          'aliases': ['job:portal:floor-' + str(maximum)], 'identity_verified': True,
                                          'evidence': 'Anúncio fictício', 'vacancy': {**support.VACANCY, 'contract': 'CLT',
                                          'salary': {**support.VACANCY['salary'], 'min': 4000, 'max': maximum}}})
                self.assertEqual(job['evaluation']['decision'], expected)
                with self.assertRaises(ValueError):
                    self.wf.decide_opportunity({'opportunity_id': job['opportunity_id'], 'reasons': job['evaluation']['reasons'], 'user_confirmation': 'Pode considerar'})

    def test_missing_tool_decision_does_not_accept_unknown_blocked_company(self):
        profile = Profile(self.root)
        profile.answer('preferences', 'technologies', ['Ferramenta Exemplo'])
        profile.approve(profile.get()['version'])
        payload = {'company': 'Empresa Exemplo', 'title': 'Função sintética', 'portal': 'portal',
                   'aliases': ['job:portal:missing-tool'], 'identity_verified': True, 'evidence': 'Anúncio fictício', 'vacancy': support.VACANCY}
        job = self.wf.opportunity(payload)
        decision = self.wf.decide_opportunity({'opportunity_id': job['opportunity_id'], 'reasons': job['evaluation']['reasons'], 'user_confirmation': 'Pode considerar só esta vaga sem ferramenta publicada'})
        self.assertEqual(decision['evaluation']['decision'], 'eligible')
        profile.answer('preferences', 'blocked_companies', ['Empresa Bloqueada'])
        profile.approve(profile.get()['version'])
        job = self.wf.opportunity(payload)
        with self.assertRaises(ValueError):
            self.wf.decide_opportunity({'opportunity_id': job['opportunity_id'], 'reasons': job['evaluation']['reasons'], 'user_confirmation': 'Pode considerar'})

    def test_pending_personal_step_is_explained_in_status(self):
        self.sent()
        ledger(self.root, 'step', {'job_id': self.job, 'step_key': 'questionario-pessoal', 'kind': 'self_report',
                                  'state': 'candidate_pending', 'summary': 'Responder questionário pessoal no portal'})
        message = self.wf.state()['message']
        self.assertIn('Empresa Exemplo', message)
        self.assertIn('questionário pessoal', message)
        self.assertNotIn('Tudo pronto', message)

    def test_partial_email_coverage_is_visible_in_status(self):
        run = mail_coverage(self.root, 'begin', {'minutes': 10})
        mail_coverage(self.root, 'account', {'run_id': run['run_id'], 'provider': 'gmail', 'account': 'principal',
                                            'status': 'partial', 'note': 'Falta a segunda página'})
        self.assertIn('leitura dos e-mails', self.wf.state()['message'])
        self.assertIn('incompleta', self.wf.state()['message'])
        mail_coverage(self.root, 'finish', {'run_id': run['run_id']})


if __name__ == '__main__':
    unittest.main()
