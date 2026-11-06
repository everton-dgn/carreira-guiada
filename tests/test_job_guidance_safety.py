"""Regression cases across research provenance and private guidance."""
from datetime import datetime, timedelta, timezone
import unittest

from tests import test_job_career as career_tests
from tests import test_job_company as company_tests


class GuidanceSafetyTests(unittest.TestCase):
    setUp = career_tests.CareerTests.setUp
    update = career_tests.CareerTests.update
    ready = career_tests.CareerTests.ready
    alternatives = career_tests.CareerTests.alternatives
    selected = career_tests.CareerTests.selected

    def finish_cycle(self):
        s = self.selected()
        s = self.update('experiment', s, activity='Organizar dados fictícios.', duration_days=1,
                        time_budget_minutes=30, learning_criterion='Identificar uma tarefa de interesse.',
                        user_confirmation='Quero experimentar.')
        return self.update('reflect', s, observations=None, learned=None, next_decision='defer')

    def test_old_cycle_cannot_reopen_while_another_is_active(self):
        old = self.finish_cycle()
        active = self.g.start({})
        with self.assertRaises(ValueError):
            self.update('answer', old, field='goal', value='Quero corrigir minha resposta antiga.')
        self.assertEqual(self.g.status()['session']['id'], active['id'])
        self.assertEqual(self.g.get(old['id']), old)

    def test_corrected_old_cycle_becomes_current_after_other_cycles_finish(self):
        old = self.finish_cycle()
        newer = self.finish_cycle()
        self.assertNotEqual(old['id'], newer['id'])
        corrected = self.update('answer', old, field='goal', value='Quero explorar outra tarefa.')
        self.assertEqual(self.g.status()['session']['id'], corrected['id'])

    def test_career_rejects_credential_text_without_saving_it(self):
        s = self.g.start({})
        with self.assertRaises(ValueError):
            self.update('answer', s, field='goal', value='senha: segredo-ficticio-nao-real')
        self.assertEqual(self.g.get(s['id']), s)

    def test_future_market_observation_is_rejected(self):
        from scripts.job.research_scope import ResearchScopes
        s = self.ready()
        scope = ResearchScopes(self.root).grant(dict(purpose='career_exploration', target=dict(kind='career', id=s['id']),
            question='Explorar tarefa fictícia.', urls=['https://example.invalid/career'], user_confirmation='Pode analisar esta fonte fictícia.'))
        alternatives = self.alternatives(s)
        alternatives[0]['market_evidence'] = [dict(statement='Observação fictícia.', url=scope['urls'][0],
            checked_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), scope_id=scope['id'],
            scope_version=1, limitations=['Simulação.'])]
        with self.assertRaises(ValueError):
            self.update('propose', s, alternatives=alternatives)
        self.assertEqual(self.g.get(s['id']), s)


class DossierSafetyTests(unittest.TestCase):
    setUp = company_tests.CompanyTests.setUp
    fixture = company_tests.CompanyTests.fixture

    def test_historical_evidence_can_be_preserved_after_scope_revocation(self):
        r, scope, data = self.fixture()
        self.company.revise(data)
        self.scopes.revoke({'scope_id': scope['id'], 'expected_version': 1})
        saved = self.company.revise({**data, 'expected_version': 2,
                                    'interview_questions': ['Como funciona a jornada nesta equipe?']})
        self.assertEqual(saved['evidence'], data['evidence'])
        self.assertEqual(saved['version'], 3)
        modified = {**data['evidence'][0], 'statement': 'Outro relato sem autorização atual.'}
        with self.assertRaises(ValueError):
            self.company.revise({**data, 'expected_version': 3, 'evidence': [modified]})
        self.assertEqual(self.company.get(r['id'], 2)['evidence'], data['evidence'])

    def test_unknown_salary_context_remains_null_and_visible(self):
        r, scope, data = self.fixture()
        data['evidence'][0]['dimension'] = 'salary'
        salary = dict(evidence_id='e1', kind='statistic', metric='median', value=9000,
                      methodology='Fonte fictícia sem contexto completo.', currency='BRL', period='month',
                      role=None, seniority=None, location=None, contract=None, sample_size=None)
        self.company.revise({**data, 'salary_observations': [salary]})
        summary = self.company.summary(r['id'])
        self.assertIsNone(summary['salary_observations'][0]['contract'])
        self.assertTrue(any('contexto' in text for text in summary['limitations']))

    def test_salary_needs_evidence_in_the_salary_dimension(self):
        r, scope, data = self.fixture()
        salary = dict(evidence_id='e1', kind='range', minimum=8000, maximum=10000,
                      currency='BRL', period='month', role=None, seniority=None,
                      location=None, contract=None, sample_size=None)
        with self.assertRaises(ValueError):
            self.company.revise({**data, 'salary_observations': [salary]})

    def test_identity_stays_visible_and_research_topics_can_expand(self):
        r, scope, data = self.fixture()
        self.assertIn('identity', self.company.summary(r['id'])['unknown_dimensions'])
        data['evidence'][0]['dimension'] = 'equipment'
        updated = self.company.revise({**data, 'dimensions': r['dimensions'] + ['equipment']})
        self.assertIn('equipment', updated['dimensions'])
        self.assertEqual(self.company.get(r['id'], 1)['dimensions'], r['dimensions'])

    def test_candidate_report_preserves_its_context(self):
        r, scope, data = self.fixture()
        data['evidence'][0]['context']['audience'] = 'candidate'
        data['evidence'][0]['statement'] = 'Uma pessoa candidata relata como a jornada foi apresentada na entrevista.'
        saved = self.company.revise(data)
        self.assertEqual(saved['evidence'][0]['context']['audience'], 'candidate')

    def test_evidence_cannot_disappear_from_summary_by_using_unselected_dimension(self):
        r, scope, data = self.fixture()
        data['evidence'][0]['dimension'] = 'equipment'
        with self.assertRaises(ValueError):
            self.company.revise(data)
        self.assertEqual(self.company.get(r['id']), r)


if __name__ == '__main__':
    unittest.main()
