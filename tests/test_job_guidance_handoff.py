"""Real saved-state regressions for optional guidance and operational recovery."""
from argparse import Namespace
from pathlib import Path
import tempfile
import unittest

from scripts.job.career import CareerGuide
from scripts.job.checkpoint import checkpoint
from scripts.job.cli import dispatch_workflow, onboarding
from scripts.job.company import CompanyDossiers
from scripts.job.intake import Intake
from scripts.job.profile import Profile
from tests import test_job_workflow as workflow_tests


class GuidanceHandoffTests(unittest.TestCase):
    setUp = workflow_tests.WorkflowTests.setUp
    approve_profile = workflow_tests.WorkflowTests.approve_profile

    def saved_career(self, paused=False, saved_point=False):
        guide = CareerGuide(self.root)
        session = guide.start({})
        if paused:
            session = guide.pause({'id': session['id'], 'expected_version': session['version']})
        if saved_point:
            checkpoint(self.root, {'phase': 'career', 'summary': 'Conversa fictícia salva.',
                                  'next_action': 'Continuar o guia.', 'needs_user': True})
        return guide, session

    def test_resume_choice_hands_off_without_losing_career(self):
        guide, session = self.saved_career()
        Profile(self.root).save('identity', {'name': 'Pessoa Fictícia', 'email': 'pessoa@example.invalid'})
        Intake(self.root).choose('create')
        self.assertEqual(onboarding(self.root)['next_step'], 'curriculum_intake')
        self.assertEqual(onboarding(self.root)['question']['field'], 'education')
        self.assertEqual(checkpoint(self.root)['phase'], 'resume')
        self.assertEqual(guide.get(session['id']), session)
        self.assertEqual(onboarding(self.root, 'career')['next_step'], 'career_guidance')

    def test_import_choice_replaces_career_checkpoint(self):
        guide, session = self.saved_career(saved_point=True)
        Profile(self.root).save('identity', {'name': 'Pessoa Fictícia', 'email': 'pessoa@example.invalid'})
        Intake(self.root).choose('import')
        self.assertEqual(onboarding(self.root)['next_step'], 'curriculum_input')
        self.assertEqual(checkpoint(self.root)['phase'], 'resume')
        self.assertEqual(guide.get(session['id']), session)

    def test_preparation_choice_preserves_scoped_curriculum_note(self):
        """Selecting preparation retains CV dependencies and the legacy handoff gate."""
        for mode in ('create', 'import'):
            for legacy_phase in (None, 'career', 'fill'):
                with self.subTest(mode=mode, legacy_phase=legacy_phase), tempfile.TemporaryDirectory() as folder:
                    root = Path(folder).resolve()
                    original = checkpoint(root, {
                        'activity': 'curriculum', 'phase': 'resume', 'summary': 'Versão fictícia pronta para revisão.',
                        'next_action': 'Conferir a experiência antes de aprovar.', 'needs_user': True,
                        'condition': 'waiting_user', 'dependency': {'reason': 'review', 'reference': 'Currículo fictício'}})
                    if legacy_phase:
                        previous = checkpoint(root, {'phase': legacy_phase, 'summary': 'Outra etapa fictícia salva.',
                                                    'next_action': 'Conferir a etapa.', 'needs_user': True})
                    Profile(root).save('identity', {'name': 'Pessoa Fictícia', 'email': 'pessoa@example.invalid'})
                    Intake(root).choose(mode)
                    self.assertEqual(checkpoint(root, activity='curriculum'), original)
                    if legacy_phase == 'fill':
                        self.assertEqual(checkpoint(root), previous)
                    else:
                        self.assertEqual(checkpoint(root), original)
                        self.assertEqual(onboarding(root)['next_step'], 'curriculum_intake' if mode == 'create' else 'curriculum_input')

    def test_paused_career_preserves_search_prompts_even_with_checkpoint(self):
        guide, session = self.saved_career(paused=True, saved_point=True)
        self.assertIn('Vamos completar', self.wf.state()['message'])
        self.assertIn('guia de carreira está pausado', self.wf.state()['message'])
        self.approve_profile()
        self.assertIn('Diga se quer apenas conhecer vagas', self.wf.state()['message'])
        guide.resume({'id': session['id'], 'expected_version': session['version']})
        self.assertNotIn('Diga se quer apenas conhecer vagas', self.wf.state()['message'])
        self.assertIn('uma pergunta por vez', self.wf.state()['message'])

    def corrupt_optional(self, table):
        with Profile(self.root)._db(True) as db:
            db.execute(f'UPDATE {table} SET value=?', ('{}',))

    def make_optional_records(self):
        self.saved_career()
        return CompanyDossiers(self.root).create({
            'entity': {'name': 'Empresa Fictícia', 'country': 'BR', 'domain': None, 'relationship': 'employer'},
            'question': 'Como é a jornada?', 'dimensions': ['workload']})

    def test_invalid_career_preserves_company_and_core_context(self):
        dossier = self.make_optional_records()
        self.corrupt_optional('career_revisions')
        state = dispatch_workflow(self.wf, self.root, Namespace(command='context'))['workflow']
        self.assertEqual(state['companies'][0]['id'], dossier['id'])
        self.assertIsNone(state['career'])
        self.assertEqual(state['optional_data_issues'][0]['area'], 'career')
        self.assertIn('precisam de reparo', state['message'])
        self.assertEqual(state['counts']['opportunities'], 0)

    def test_invalid_company_does_not_fail_after_resume_commit(self):
        self.make_optional_records()
        stopped = self.wf.stop()
        self.corrupt_optional('job_company_dossiers')
        resumed = dispatch_workflow(self.wf, self.root, Namespace(command='resume-work'))
        self.assertTrue(resumed['resumed'])
        self.assertFalse(resumed['control']['stopped'])
        self.assertEqual(resumed['control']['generation'], stopped['generation'] + 1)
        self.assertEqual(resumed['companies'], [])
        self.assertIsNotNone(resumed['career']['session'])
        self.assertEqual(resumed['optional_data_issues'][0]['area'], 'companies')
        with Profile(self.root)._db() as db:
            self.assertEqual(db.execute('SELECT value FROM job_company_dossiers').fetchone()[0], '{}')


if __name__ == '__main__':
    unittest.main()
