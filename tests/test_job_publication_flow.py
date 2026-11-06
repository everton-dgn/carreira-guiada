"""External effects are represented by synthetic receipts only."""
import hashlib
import unittest

from scripts.job.presence import Presence
from scripts.job.practice import Practice
from scripts.job.profile import Profile
from tests import test_job_workflow as support


class PublicationFlowTests(unittest.TestCase):
    setUp = support.WorkflowTests.setUp
    approve_profile = support.WorkflowTests.approve_profile
    approved_resume = support.WorkflowTests.approved_resume
    ready = support.WorkflowTests.ready
    apply = support.WorkflowTests.apply
    done = support.WorkflowTests.done

    def publication(self):
        self.ready({'summary': 'Revisar perfil e buscar vagas fictícias',
                    'actions': ['profile_publish', 'research', 'apply']})
        self.presence = Presence(self.root)
        self.presence.choose('now', ['github'], 'Quero revisar meu perfil fictício.')
        content = 'Desenvolvo interfaces acessíveis e testo fluxos de atendimento.'
        self.presence.draft('github', content, 'https://github.com/pessoa-exemplo')
        self.presence.finish('github', 1, 'Conferi este texto.')
        return {'action': 'profile_publish', 'owner': 'chat:sessao', 'generation': 1,
                'channel': {'provider': 'chrome', 'account': 'portal-teste'},
                'user_confirmation': 'Autorizo publicar este texto na biografia pública da minha conta conferida.',
                'publication': {'topic': 'github', 'version': 1, 'section': 'bio',
                                'destination': 'https://github.com/pessoa-exemplo', 'visibility': 'public',
                                'content_sha256': hashlib.sha256(content.encode()).hexdigest()}}

    def test_specific_consent_exact_text_and_destination_receipt(self):
        p = self.publication()
        with self.assertRaisesRegex(ValueError, 'confirmação'):
            self.wf.authorize({**p, 'user_confirmation': None})
        for changes in ({'content_sha256': '0' * 64}, {'version': 0},
                        {'destination': 'https://github.com/outra-pessoa'}, {'visibility': 'unknown'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.wf.authorize({**p, 'publication': {**p['publication'], **changes}})
        action = self.wf.authorize(p)
        checked = self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': 1})
        self.assertEqual(checked['publication'], p['publication'])
        self.assertFalse(self.presence.status()['publication_authorized'])
        with self.assertRaisesRegex(ValueError, 'publication'):
            self.done(action['action_id'])
        for changes in ({'evidence_url': 'https://github.com/outra-pessoa'},
                        {'evidence_source': 'destination_listing'}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'publication'):
                self.done(action['action_id'], publication_sha256=p['publication']['content_sha256'],
                          **changes)
        result = self.done(action['action_id'], publication_sha256=p['publication']['content_sha256'],
                           evidence_url=p['publication']['destination'])
        self.assertEqual(result['status'], 'confirmed')
        self.assertTrue(self.done(action['action_id'], publication_sha256=p['publication']['content_sha256'],
                                  evidence_url=p['publication']['destination'])['duplicate'])
        with self.assertRaisesRegex(ValueError, 'duplicata'):
            self.wf.authorize(p)

    def test_changed_review_blocks_check_and_uncertainty_blocks_new_version(self):
        p = self.publication()
        action = self.wf.authorize(p)
        self.presence.draft('github', 'Uma biografia corrigida.', p['publication']['destination'])
        with self.assertRaisesRegex(ValueError, 'versão|revis'):
            self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': 1})
        self.done(action['action_id'], 'uncertain', evidence_source='agent_report')
        self.presence.finish('github', 2, 'Conferi a correção.')
        p['publication'].update(version=2, content_sha256=hashlib.sha256('Uma biografia corrigida.'.encode()).hexdigest())
        with self.assertRaisesRegex(ValueError, 'incerto'):
            self.wf.authorize(p)
        with self.assertRaisesRegex(ValueError, 'publication'):
            self.done(action['action_id'], 'not_received', evidence_url='https://github.com/outro-perfil')
        with self.assertRaisesRegex(ValueError, 'publication_sha256'):
            self.done(action['action_id'], 'not_received', evidence_url=p['publication']['destination'],
                      publication_sha256=p['publication']['content_sha256'])
        self.done(action['action_id'], 'not_received', evidence_url=p['publication']['destination'])
        self.assertEqual(self.wf.authorize(p)['status'], 'authorized')

    def test_legacy_profile_stays_approved_and_new_permission_can_be_denied(self):
        p = self.publication()
        profile = Profile(self.root)
        permissions = profile.get()['sections']['permissions']
        permissions.pop('profile_publish', None)
        profile.save('permissions', permissions)
        profile.approve(profile.get()['version'])
        self.assertTrue(profile.status()['approved'])
        self.assertEqual(self.wf.authorize(p)['permission'], 'ask')
        profile.save('permissions', {**permissions, 'profile_publish': 'deny'})
        profile.approve(profile.get()['version'])
        with self.assertRaisesRegex(ValueError, 'negada'):
            self.wf.authorize(p)

    def test_postponing_practice_keeps_search_authorization_alive(self):
        self.ready()
        action = self.wf.authorize({'action': 'research', 'source_url': 'https://jobs.example.org/',
                                   'owner': 'chat:sessao', 'generation': 1, 'scope_key': 'busca',
                                   'channel': {'provider': 'chrome', 'account': 'public'}})
        practice = Practice(self.root)
        session = practice.start('rh', 'coach', short=True)
        practice.choose('later')
        self.assertFalse(self.wf.state()['control']['stopped'])
        self.assertEqual(self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': 1})['status'], 'authorized')
        practice.choose('now')
        self.assertEqual(practice.status()['session_id'], session['session_id'])
        self.wf.stop()
        with self.assertRaises(ValueError):
            self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': 1})

    def test_corrected_resume_blocks_old_authorization_without_erasing_history(self):
        from scripts.job.resumes import ResumeManager
        job, resume = self.ready()
        action = self.apply(job, resume)
        manager = ResumeManager(self.root)
        correction = manager.replace_fact(resume['fact_ids'][0], 'Experiência fictícia corrigida.',
                                          'candidate:correcao', True)
        self.assertEqual(correction['open_authorizations'][0]['id'], action['action_id'])
        with self.assertRaisesRegex(ValueError, 'aprovada'):
            self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': 1})
        self.assertEqual(self.wf.state()['counts']['actions']['authorized'], 1)
        self.done(action['action_id'], 'not_received')
        new = manager.approve(manager.draft('novo', '# Pessoa de Teste\n\nExperiência fictícia corrigida.',
                                            [correction['replacement']['id']])['id'])
        self.assertEqual(self.apply(job, new)['status'], 'authorized')

    def test_new_review_after_confirmed_publication_requires_fresh_authorization(self):
        p = self.publication()
        first = self.wf.authorize(p)
        self.done(first['action_id'], publication_sha256=p['publication']['content_sha256'],
                  evidence_url=p['publication']['destination'])
        self.presence.draft('github', 'Biografia nova confirmada.', p['publication']['destination'])
        self.presence.finish('github', 2, 'Conferi a nova biografia.')
        p['publication'].update(version=2, content_sha256=hashlib.sha256('Biografia nova confirmada.'.encode()).hexdigest())
        second = self.wf.authorize(p)
        self.assertNotEqual(first['action_id'], second['action_id'])
        with self.assertRaisesRegex(ValueError, 'responsável'):
            self.wf.check(second['action_id'], {'owner': 'chat:outra', 'generation': 1})

    def test_uncertain_publication_can_be_reconciled_from_persisted_outputs(self):
        from scripts.job.workflow import Workflow
        action_id = self.wf.authorize(self.publication())['action_id']
        self.wf.stop()
        self.wf.close()
        self.wf = Workflow(self.root, clock=self.clock)
        self.addCleanup(self.wf.close)
        generation = self.wf.resume()['control']['generation']
        self.presence.draft('github', 'Outra seção preparada depois.', 'https://github.com/outro-exemplo')
        recovered = self.wf.show_action(action_id)
        self.assertEqual(recovered['status'], 'uncertain')
        self.assertFalse(recovered['execution_allowed'])
        self.assertEqual(recovered['channel']['account'], 'portal-teste')
        with self.assertRaises(ValueError):
            self.wf.check(action_id, {'owner': 'chat:retomada', 'generation': generation})
        receipt = self.wf.complete(action_id, {'owner': 'chat:retomada', 'generation': generation,
            'outcome': 'confirmed', 'evidence': 'Texto anterior conferido na página fictícia.',
            'evidence_source': 'destination_page', 'checked_at': self.clock().isoformat(),
            'evidence_url': recovered['publication']['destination'],
            'publication_sha256': recovered['publication']['content_sha256']})
        self.assertEqual(receipt['status'], 'confirmed')


if __name__ == '__main__':
    unittest.main()
