import json
import os
import tempfile
import unittest
from pathlib import Path
from scripts.job.profile import Profile


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.profile = Profile(self.root)

    def complete(self):
        template = Path(__file__).resolve().parents[1] / 'templates/profile.json'
        sections = json.loads(template.read_text())['sections']
        sections['identity'] = {'name': 'Pessoa de Teste', 'email': 'teste@example.invalid'}
        sections['preferences'].update(roles=['Função sintética'], modalities=['remote'], currencies=['BRL'])
        for section, data in sections.items(): self.profile.save(section, data)
        return self.profile.get()['version']

    def test_empty_read_creates_nothing(self):
        self.assertEqual(self.profile.get()['version'], 0)
        self.assertEqual(self.profile.status()['next_section'], 'identity')
        self.assertFalse((self.root / '.job').exists())

    def test_template_does_not_answer_modality_for_candidate(self):
        template = Path(__file__).resolve().parents[1] / 'templates/profile.json'
        preferences = json.loads(template.read_text(encoding='utf-8'))['sections']['preferences']
        preferences.update(roles=['Atendimento'], currencies=['BRL'])
        self.profile.save('identity', {'name': 'Pessoa fictícia', 'email': 'pessoa@example.invalid'})
        self.profile.save('preferences', preferences)
        self.assertIn('modalities', [q['field'] for q in self.profile.status()['questions']])
        self.profile.answer('preferences', 'modalities', [])
        self.assertNotIn('modalities', [q['field'] for q in self.profile.status()['questions']])

    def test_resume_approval_and_invalidation(self):
        self.profile.save('identity', {'name': 'Pessoa de Teste'})
        self.assertEqual(Profile(self.root).status()['next_section'], 'identity')
        version = self.complete()
        self.profile.approve(version)
        self.assertTrue(self.profile.status()['approved'])
        identity = self.profile.get()['sections']['identity']
        self.assertEqual(self.profile.save('identity', identity)['version'], version)
        self.profile.save('identity', {**identity, 'name': 'Outro nome sintético'})
        self.assertFalse(self.profile.status()['approved'])
        with self.assertRaises(ValueError): self.profile.approve(version)
        self.assertNotIn('example.invalid', json.dumps(self.profile.status()))

    def test_permissions_and_validation(self):
        with self.assertRaises(ValueError): self.profile.save('permissions', {'apply': 'allow'})
        saved = self.profile.save('permissions', {'research': 'allow', 'confirmed': ['research']})
        self.assertNotIn('apply', saved['sections']['permissions'])
        with self.assertRaises(ValueError): self.profile.save('identity', {'email': 'invalid'})
        with self.assertRaises(ValueError): self.profile.save('connections', {'accounts': [{'token': 'synthetic'}]})
        with self.assertRaises(ValueError): self.profile.save('limits', {'mode': 'supervised', 'cycles': True})
        with self.assertRaises(ValueError): self.profile.approve(saved['version'])

    def test_permissions_on_disk(self):
        self.complete()
        self.assertEqual((self.root / '.job').stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / '.job/control.sqlite3').stat().st_mode & 0o777, 0o600)

    def test_reject_directory_symlink(self):
        target = self.root / 'target'
        target.mkdir()
        (self.root / '.job').symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError): self.profile.get()
        self.assertEqual(list(target.iterdir()), [])

    def test_reject_database_symlink(self):
        state = self.root / '.job'
        state.mkdir(mode=0o700)
        target = self.root / 'target'
        target.write_text('preservar')
        (state / 'control.sqlite3').symlink_to(target)
        with self.assertRaises(ValueError): self.profile.save('identity', {'name': 'Teste'})
        self.assertEqual(target.read_text(), 'preservar')

    def test_identity_resume_only_pending_question(self):
        self.profile.save('identity', {'name': 'Pessoa fictícia'})
        status = Profile(self.root).status()
        self.assertEqual([q['field'] for q in status['questions']], ['email'])
        self.assertNotIn('Pessoa fictícia', json.dumps(status, ensure_ascii=False))
        self.profile.save('identity', {'name': 'Pessoa fictícia', 'email': 'teste@example.invalid'})
        self.assertEqual(Profile(self.root).status()['next_section'], 'preferences')

    def test_preferences_resume_each_pending_field(self):
        self.complete()
        preferences = self.profile.get()['sections']['preferences']
        for field in preferences:
            with self.subTest(field=field):
                partial = {k: v for k, v in preferences.items() if k != field}
                self.profile.save('preferences', partial)
                status = Profile(self.root).status()
                self.assertEqual(status['next_section'], 'preferences')
                fields = [q['field'] for q in status['questions']]
                if field == 'salary':
                    self.assertEqual(len(fields), 5)
                    self.assertTrue(all(x.startswith('salary.') for x in fields))
                else:
                    self.assertEqual(fields, [field])
        for field in ('roles', 'currencies'):
            with self.subTest(empty=field):
                self.profile.save('preferences', {**preferences, field: []})
                self.assertEqual([q['field'] for q in Profile(self.root).status()['questions']], [field])
        self.profile.save('preferences', {**preferences, 'modalities': []})
        self.assertEqual(Profile(self.root).status()['questions'], [])
        self.profile.save('preferences', preferences)
        self.assertEqual(Profile(self.root).status()['questions'], [])

    def test_external_executor_is_not_an_onboarding_option(self):
        self.complete()
        with self.assertRaises(ValueError):
            self.profile.save('limits', {'mode': 'supervised', 'duration_minutes': 10})
        self.assertEqual(self.profile.get()['sections']['limits'], {'mode': 'chat'})

    def test_partial_salary_survives_restart_without_repeating(self):
        self.complete()
        preferences = self.profile.get()['sections']['preferences']
        preferences['salary'] = {'floors': []}
        self.profile.save('preferences', preferences)
        status = Profile(self.root).status()
        self.assertNotIn('salary.floors', [q['field'] for q in status['questions']])
        self.assertEqual(len(status['questions']), 3)
        with self.assertRaises(ValueError):
            self.profile.approve(status['version'])
