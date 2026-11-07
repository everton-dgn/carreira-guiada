"""Fictional career and employer decisions through isolated real CLI processes."""
import json
import os
from datetime import datetime
from pathlib import Path
import unittest

from tests import test_job_preparation_journey as preparation


class GuidanceJourneyTests(unittest.TestCase):
    setUp = preparation.PreparationJourneyTests.setUp
    call = preparation.PreparationJourneyTests.call
    say = preparation.PreparationJourneyTests.say

    def tearDown(self):
        destination = os.environ.get('JOB_GUIDANCE_REPORT')
        if destination:
            folder = Path(destination) / self._testMethodName
            folder.mkdir(parents=True, exist_ok=False)
            (folder / 'evidence.json').write_text(json.dumps({
                'scope': 'Fictional scripted dialogue; real CLI; network and subprocesses blocked; simulated next day.',
                'calls': self.calls, 'dialogue': self.turns,
            }, ensure_ascii=False, indent=2))

    def session(self):
        return self.call('career', 'status')['session']

    def mutate(self, action, **data):
        session = self.session()
        return self.call('career', action, data={'id': session['id'], 'expected_version': session['version'], **data})

    def questions(self):
        self.call('career', 'start', data={})
        answers = {'goal': 'Quero descobrir que trabalho procurar.', 'priorities': 'Preciso de uma rotina previsível.',
                   'experiences': 'Organizei pedidos em uma atividade voluntária fictícia.',
                   'constraints': None, 'available_time': 'Duas horas nesta semana.'}
        for field, value in answers.items():
            state = self.call('start', '--focus', 'career')
            self.assertEqual(state['question']['field'], field)
            self.say(state['message'], value or 'Não sei ainda.')
            self.mutate('answer', field=field, value=value)

    def propose(self):
        session = self.session()
        answer = session['answers']['experiences']
        answer_version = answer['version']
        return self.mutate('propose', alternatives=[{
            'id': 'support', 'title': 'Experimentar apoio administrativo',
            'gains': ['Explorar organização de pedidos.'], 'costs': ['Reservar duas horas para praticar.'],
            'basis': [{'answer_field': 'experiences', 'answer_version': answer_version}],
            'gaps': ['A experiência voluntária não comprova domínio da função.'],
        }])

    def company(self):
        return self.call('company', 'create', data={
            'entity': {'name': 'Aurora Fictícia', 'country': 'BR', 'domain': 'https://aurora.example.invalid', 'relationship': 'employer'},
            'question': 'O que preciso esclarecer sobre a jornada?',
            'dimensions': ['workload', 'salary', 'consumer_reputation'],
        })

    def scope(self, company):
        return self.call('research-scope', 'grant', data={
            'purpose': 'company_dossier', 'target': {'kind': 'company', 'id': company['id']},
            'question': company['question'],
            'urls': ['https://aurora.example.invalid/carreiras', 'https://relatos.example.invalid/aurora'],
            'user_confirmation': 'Pode analisar essas duas fontes fictícias para esta empresa.',
        })

    def check(self, company, scope):
        return {'scope_id': scope['id'], 'expected_version': scope['version'], 'purpose': 'company_dossier',
                'target': {'kind': 'company', 'id': company['id']}, 'url': 'https://aurora.example.invalid/carreiras'}

    def test_empty_optional_entries_are_read_only_and_skip_contact_forms(self):
        career = self.call('start', '--focus', 'career')
        company = self.call('start', '--focus', 'company')
        self.assertEqual(career['next_step'], 'career_guidance')
        self.assertEqual(company['next_step'], 'company_dossier')
        self.assertFalse((self.root / '.job').exists())
        self.assertFalse(career['automatic_execution_started'])
        self.assertEqual(career['question']['field'], 'goal')
        self.assertNotIn('Inicie uma sessão', career['message'])

    def test_novice_career_unknown_answer_pause_next_day_and_small_experiment(self):
        self.questions()
        self.propose()
        before = self.session()
        self.say('Podemos continuar outro dia; suas respostas ficam salvas.', 'Vou continuar amanhã.')
        self.mutate('pause')
        self.time = '2026-11-07T18:00:00-03:00'
        resumed_start = self.call('start')
        self.assertEqual(resumed_start['next_step'], 'career_guidance')
        self.assertTrue(resumed_start['career']['paused'])
        self.assertIsNone(resumed_start['question'])
        self.assertEqual(before['id'], self.session()['id'])
        self.mutate('resume')
        self.mutate('choose', alternative_id='support', user_confirmation='Quero experimentar apoio administrativo.')
        self.mutate('experiment', activity='Organizar uma planilha com pedidos inventados.', duration_days=7,
                    time_budget_minutes=120, learning_criterion='Localizar os pedidos atrasados sem ajuda.',
                    user_confirmation='Tenho essas duas horas e quero fazer o exercício.')
        self.mutate('reflect', observations='Localizei os atrasos na planilha fictícia.',
                    learned='Gostei da organização, mas preciso praticar fórmulas.', next_decision='continue')
        self.assertEqual(self.call('career', 'status')['phase'], 'finished')
        self.assertEqual(self.call('profile', 'show')['sections'], {})
        self.assertEqual(self.call('resume', 'facts'), [])
        state = self.call('status')
        self.assertEqual(state['counts']['opportunities'], 0)
        self.assertEqual(state['counts']['messages'], 0)

    def test_explicit_job_search_keeps_priority_over_optional_career(self):
        """An explicit search request takes priority over an unfinished optional guide."""
        self.call('career', 'start', data={})
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'preferences')
        self.assertEqual(self.call('career', 'status')['phase'], 'questions')

    def test_stopped_state_stays_visible_and_research_needs_new_scope_after_resume(self):
        company = self.company()
        scope = self.scope(company)
        self.assertEqual(datetime.fromisoformat(scope['created_at']), datetime.fromisoformat(self.time))
        check = self.check(company, scope)
        self.assertTrue(self.call('research-scope', 'check', data=check)['allowed'])
        self.call('stop')
        self.assertFalse(self.call('research-scope', 'check', data=check)['allowed'])
        self.assertIn('parado', self.call('status')['message'])
        resumed = self.call('resume-work')
        self.assertNotIn('dados de contato', resumed['message'])
        self.assertFalse(self.call('research-scope', 'check', data=check)['allowed'])
        fresh = self.scope(company)
        self.assertTrue(self.call('research-scope', 'check', data=self.check(company, fresh))['allowed'])
        self.assertEqual(self.call('company', 'get', data={'id': company['id']})['version'], 1)

    def test_company_checkpoint_survives_new_process_without_profile(self):
        company = self.company()
        self.assertEqual(self.call('start')['next_step'], 'company_dossier')
        self.call('checkpoint', 'save', data={'phase': 'company', 'summary': 'Empresa fictícia identificada; faltam relatos.',
                  'next_action': 'Combinar as fontes para conferir a jornada.', 'needs_user': True})
        self.time = '2026-11-07T18:00:00-03:00'
        self.assertEqual(self.call('start')['next_step'], 'company_dossier')
        self.assertNotIn('dados de contato', self.call('status')['message'])
        self.assertEqual(self.call('company', 'list')[0]['id'], company['id'])
        self.assertEqual(self.call('profile', 'show')['sections'], {})

    def test_dossier_separates_consumer_reports_salary_and_interview_questions(self):
        company = self.company()
        scope = self.scope(company)
        evidence = {'id': 'consumer-1', 'dimension': 'workload', 'nature': 'report',
            'statement': 'Um consumidor relata atraso no atendimento.',
            'url': scope['urls'][1], 'checked_at': '2026-11-06T12:00:00Z', 'published_at': None,
            'context': {'audience': 'consumer', 'role': None, 'location': None, 'period': None},
            'origin_group': 'consumer-origin-1', 'limitations': ['Não descreve condições de trabalho.'],
            'scope_id': scope['id'], 'scope_version': scope['version']}
        data = {'id': company['id'], 'expected_version': 1, 'evidence': [evidence],
                'salary_observations': [], 'contradictions': [],
                'interview_questions': ['Como a equipe organiza a jornada?'], 'opportunity_link': None}
        self.call('company', 'revise', data=data)
        summary = self.call('company', 'summary', data={'id': company['id']})
        self.assertIn('workload', summary['unknown_dimensions'])
        self.say('A reclamação é de um consumidor. A jornada de trabalho continua sem informação.',
                 'Quero conferir também a remuneração e relatos da equipe.')
        employee = {**evidence, 'id': 'employee-1', 'statement': 'Um relato de funcionário menciona horas extras.',
                    'context': {**evidence['context'], 'audience': 'employee'}, 'origin_group': 'employee-origin-1',
                    'limitations': ['Relato isolado; equipe desconhecida.']}
        salary = {**employee, 'id': 'salary-1', 'dimension': 'salary',
                  'statement': 'Uma referência fictícia informa mediana mensal de 9000 BRL.',
                  'url': scope['urls'][0], 'origin_group': 'salary-origin-1',
                  'limitations': ['Amostra desconhecida; não representa oferta.']}
        updated = self.call('company', 'revise', data={**data, 'expected_version': 2,
            'evidence': [evidence, employee, salary],
            'salary_observations': [{'evidence_id': 'salary-1', 'kind': 'statistic', 'metric': 'median',
                'value': 9000, 'methodology': 'Mediana informada pela fonte fictícia, sem amostra divulgada.',
                'currency': 'BRL', 'period': 'month', 'role': 'Atendimento', 'seniority': 'mid',
                'location': 'Salvador', 'contract': 'CLT', 'sample_size': None}],
            'interview_questions': ['Como são registradas e compensadas as horas extras?']})
        self.assertEqual(updated['version'], 3)
        historical = self.call('company', 'get', data={'id': company['id'], 'version': 2})
        self.assertEqual(len(historical['evidence']), 1)
        summary = self.call('company', 'summary', data={'id': company['id']})
        self.assertEqual(summary['salary_observations'][0]['metric'], 'median')
        self.assertIsNone(summary['salary_observations'][0]['sample_size'])
        self.assertNotIn('minimum', summary['salary_observations'][0])
        self.assertEqual(len(summary['interview_questions']), 1)
        self.assertEqual(self.call('profile', 'show')['sections'], {})
        self.assertEqual(self.call('status')['counts']['actions'], {})

    def test_failed_edit_keeps_saved_answer_and_uses_plain_error(self):
        self.call('career', 'start', data={})
        self.mutate('answer', field='goal', value='Quero conhecer opções.')
        before = self.session()
        result = self.call('career', 'answer', data={'id': before['id'], 'expected_version': 1,
            'field': 'goal', 'value': 'Resposta de uma tela antiga.'}, success=False)
        self.assertIn('error', result)
        self.assertNotIn('Traceback', result['error'])
        self.assertEqual(self.session(), before)

    def test_missing_record_explains_recovery_instead_of_returning_null(self):
        for command, key in [('company', 'id'), ('career', 'id'), ('research-scope', 'scope_id')]:
            result = self.call(command, 'get', data={key: 'missing-fictional-record'}, success=False)
            self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
