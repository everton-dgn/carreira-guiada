"""Regression coverage for explicit routes and no-preference modality."""
import unittest
import json
from tests import test_job_cli as cli
from scripts.job.profile import pending_questions
from scripts.job.policy import evaluate, validate_preferences
from scripts.job.cli import render
from scripts.job.navigation import menu


class AuxiliaryNavigationTests(unittest.TestCase):
    setUp = cli.CliTests.setUp
    call = cli.CliTests.call

    def test_more_and_explicit_routes(self):
        result = self.call('menu', '--choose', 'mais opções', '--remember')
        self.assertIsNone(result['selected'])
        self.assertEqual(len(result['choices']), 5)
        self.assertFalse((self.root / '.job').exists())
        for name, step in [('empresa', 'company_dossier'), ('LinkedIn/GitHub', 'professional_presence'),
                           ('propostas', 'offers'), ('modelos', 'model_preferences')]:
            with self.subTest(name=name):
                self.call('menu', '--choose', name, '--remember')
                self.assertEqual(self.call('start')['next_step'], step)
                self.call('start', '--focus', 'career')
                self.assertEqual(self.call('start')['next_step'], step)

    def test_empty_modality_is_answer_and_valid(self):
        self.assertNotIn('modalities', [q['field'] for q in pending_questions('preferences', {'modalities': []})])
        prefs = json.loads((cli.PROJECT / 'templates/profile.json').read_text())['sections']['preferences']
        prefs.update(roles=['Atendimento'], currencies=['BRL'])
        prefs['modalities'] = []
        validate_preferences(prefs)
        prefs['missing'] = 'reject'
        result = evaluate(prefs, {'role': 'Atendimento', 'modality': 'presencial'})
        self.assertFalse(any('modality' in reason for reason in result['reasons']))
        for field in ('roles', 'currencies'):
            with self.assertRaises(ValueError):
                validate_preferences({**prefs, field: []})
        self.assertIn('modalities', [q['field'] for q in pending_questions('preferences', {})])
        self.call('profile', 'answer', 'preferences', data={'field': 'roles', 'value': []})
        self.call('profile', 'answer', 'preferences', data={'field': 'modalities', 'value': []})
        self.assertEqual(self.call('start', '--focus', 'search')['question']['field'], 'roles')

    def test_company_creation_preserves_explicit_activity(self):
        base = self.root
        for route in ('search', 'curriculum', 'company', 'prepare'):
            with self.subTest(route=route):
                self.root = base / route
                self.root.mkdir()
                self.call('menu', '--choose', route, '--remember')
                before = self.call('start')['next_step']
                self.call('company', 'create', data={'entity': {'name': 'Empresa fictícia', 'country': 'BR',
                          'domain': None, 'relationship': 'employer'}, 'question': 'Condições?', 'dimensions': ['workload']})
                self.assertEqual(self.call('start')['next_step'], before)

    def test_plain_menu_and_resume_are_readable(self):
        self.assertIn('5. Mais opções', render(menu()))
        self.assertIn('LinkedIn/GitHub', render(menu('mais opções')))
        self.call('menu', '--choose', 'modelos', '--remember')
        text = render(self.call('start'))
        self.assertIn('Preferências de modelos', text)
        self.assertIn('serviços de IA', text)

    def test_auxiliary_route_can_switch_to_started_interview_or_career(self):
        base = self.root
        for route in ('company', 'presence', 'offers', 'models'):
            self.root = base / route
            self.root.mkdir()
            self.call('menu', '--choose', route, '--remember')
            self.call('practice', 'start', data={'track': 'rh', 'mode': 'coach'})
            self.assertEqual(self.call('start')['next_step'], 'interview_preparation')
            self.call('menu', '--choose', route, '--remember')
            self.call('career', 'start', data={})
            self.assertEqual(self.call('start')['next_step'], 'career_guidance')
