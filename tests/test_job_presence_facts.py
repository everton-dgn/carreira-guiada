"""Fact correction contracts using exclusively temporary fictional state."""
import unittest
from unittest.mock import patch

from scripts.job.resumes import ResumeManager
from tests import test_job_presence as presence_support
from tests import test_job_publication_flow as publication_support


class FactPresenceTests(unittest.TestCase):
    setUp = presence_support.PresenceTests.setUp

    def prepare(self, dependencies=True):
        self.manager = ResumeManager(self.root)
        self.fact = self.manager.add_fact('Experiência fictícia.', 'candidate:test', True)['id']
        self.presence.choose('now', ['github', 'linkedin'], 'Revisar.')
        self.presence.draft('github', 'Texto fictício.', 'https://github.com/example',
                            [self.fact] if dependencies else None)
        self.presence.finish('github', 1, 'Conferido.')

    def test_replace_revoke_and_new_draft(self):
        for operation in ('replace', 'revoke'):
            with self.subTest(operation=operation):
                self.prepare()
                old = self.presence.get()['reviews']['github']
                if operation == 'replace':
                    result = self.manager.replace_fact(self.fact, 'Correção fictícia.', 'candidate:test', True)
                    new_id = result['replacement']['id']
                else:
                    self.manager.revoke_fact(self.fact, 'candidate:test', True)
                    new_id = self.manager.add_fact('Outro fato.', 'candidate:test', True)['id']
                state = self.presence.get()
                self.assertEqual(state['history']['github'][-1], old)
                self.assertIsNone(state['reviews']['github']['content'])
                for version in (1, 2):
                    with self.assertRaises(ValueError):
                        self.presence.finish('github', version, 'Conferido.')
                with self.assertRaises(ValueError):
                    self.presence.draft('github', 'Novo texto.', 'candidate_text', [self.fact])
                self.presence.draft('github', 'Novo texto.', 'candidate_text', [new_id])
                version = self.presence.status()['reviews']['github']['version']
                self.presence.finish('github', version, 'Conferido.')
                self.assertTrue(self.presence.status()['reviews']['github']['reviewed'])
                # Independent fixture for the next operation.
                self.setUp()

    def test_unknown_legacy_invalidates_but_explicit_unrelated_survives(self):
        self.prepare(False)
        other = self.manager.add_fact('Outro fato.', 'candidate:test', True)['id']
        self.presence.draft('linkedin', 'Outro texto.', 'candidate_text', [other])
        self.presence.finish('linkedin', 1, 'Conferido.')
        self.manager.revoke_fact(self.fact, 'candidate:test', True)
        self.assertFalse(self.presence.status()['reviews']['github']['reviewed'])
        self.assertTrue(self.presence.status()['reviews']['linkedin']['reviewed'])

    def test_strict_ids_and_rollback(self):
        self.prepare()
        unconfirmed = self.manager.add_fact('Sem confirmação.', 'candidate:test', False)['id']
        for ids in ('abc', [True], [self.fact, self.fact], [' '+self.fact], ['absent'], [unconfirmed]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.presence.draft('github', 'Texto novo.', 'candidate_text', ids)
        before = self.presence.get()
        with patch.object(self.manager, '_change_result', side_effect=RuntimeError('rollback')):
            with self.assertRaises(RuntimeError):
                self.manager.replace_fact(self.fact, 'Correção.', 'candidate:test', True)
        self.assertEqual(self.presence.get(), before)
        self.assertEqual(len(self.manager.facts()), 2)
        self.assertEqual(next(f for f in self.manager.facts() if f['id'] == self.fact)['status'], 'active')

    def test_draft_and_explicit_empty_dependencies(self):
        self.prepare()
        self.presence.draft('github', 'Rascunho pendente.', 'candidate_text', [self.fact])
        self.presence.draft('linkedin', 'Texto sem fatos.', 'candidate_text', [])
        self.presence.finish('linkedin', 1, 'Conferido.')
        self.manager.revoke_fact(self.fact, 'candidate:test', True)
        self.assertIsNone(self.presence.get()['reviews']['github']['content'])
        self.assertTrue(self.presence.status()['reviews']['linkedin']['reviewed'])


class PublicationFactTests(unittest.TestCase):
    setUp = publication_support.PublicationFlowTests.setUp
    approve_profile = publication_support.PublicationFlowTests.approve_profile
    approved_resume = publication_support.PublicationFlowTests.approved_resume
    ready = publication_support.PublicationFlowTests.ready
    publication = publication_support.PublicationFlowTests.publication
    done = publication_support.PublicationFlowTests.done

    def test_stale_check_and_historical_reconciliation(self):
        payload = self.publication()
        action = self.wf.authorize(payload)
        manager = ResumeManager(self.root)
        fact = manager.add_fact('Fato fictício.', 'candidate:test', True)['id']
        manager.revoke_fact(fact, 'candidate:test', True)
        with self.assertRaises(ValueError):
            self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': 1})
        with self.assertRaises(ValueError):
            self.wf.authorize(payload)
        self.done(action['action_id'], 'uncertain', evidence_source='agent_report')
        historic = self.wf.show_action(action['action_id'])
        self.assertEqual(historic['publication'], payload['publication'])
        self.done(action['action_id'], publication_sha256=payload['publication']['content_sha256'],
                  evidence_url=payload['publication']['destination'])
        self.assertEqual(self.wf.show_action(action['action_id'])['status'], 'confirmed')
        self.presence.draft('github', 'Texto atualizado.', payload['publication']['destination'], [])
        version = self.presence.status()['reviews']['github']['version']
        self.presence.finish('github', version, 'Conferido.')
        import hashlib
        payload['publication'].update(version=version, content_sha256=hashlib.sha256('Texto atualizado.'.encode()).hexdigest())
        self.assertEqual(self.wf.authorize(payload)['status'], 'authorized')

    def test_fact_change_reports_exact_open_publications_and_duplicate_is_stable(self):
        for operation in ('replace', 'revoke'):
            with self.subTest(operation=operation):
                self.setUp()
                payload = self.publication()
                manager = ResumeManager(self.root)
                fact = manager.add_fact('Fato original.', 'candidate:test', True)['id']
                action = self.wf.authorize(payload)
                def correct():
                    if operation == 'replace':
                        return manager.replace_fact(fact, 'Fato corrigido.', 'candidate:test', True)
                    return manager.revoke_fact(fact, 'candidate:test', True)
                result = correct()
                self.assertEqual([a['id'] for a in result['open_authorizations']], [action['action_id']])
                self.assertEqual(result['open_authorizations'][0]['publication'], payload['publication'])
                self.done(action['action_id'], 'uncertain', evidence_source='agent_report')
                self.assertEqual(correct()['open_authorizations'][0]['status'], 'uncertain')
                self.done(action['action_id'], 'not_received', evidence_url=payload['publication']['destination'])
                # Unknown provenance in a newly prepared version must not be associated
                # retroactively with this already corrected fact.
                self.presence.draft('github', 'Texto novo.', payload['publication']['destination'])
                self.presence.finish('github', 3, 'Conferido.')
                import hashlib
                payload['publication'].update(version=3, content_sha256=hashlib.sha256('Texto novo.'.encode()).hexdigest())
                self.wf.authorize(payload)
                self.assertEqual(correct()['open_authorizations'], [])
                self.assertTrue(self.presence.status()['reviews']['github']['reviewed'])

    def test_unrelated_explicit_fact_publication_excluded(self):
        payload = self.publication()
        manager = ResumeManager(self.root)
        unrelated = manager.add_fact('Outro fato.', 'candidate:test', True)['id']
        related = manager.add_fact('Fato usado no texto.', 'candidate:test', True)['id']
        self.presence.draft('github', 'Texto independente.', payload['publication']['destination'], [related])
        self.presence.finish('github', 2, 'Conferido.')
        import hashlib
        payload['publication'].update(version=2, content_sha256=hashlib.sha256('Texto independente.'.encode()).hexdigest())
        action = self.wf.authorize(payload)
        result = manager.revoke_fact(unrelated, 'candidate:test', True)
        self.assertEqual(result['open_authorizations'], [])
        self.assertEqual(self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': 1})['status'], 'authorized')

    def test_archived_publications_reported_without_unrelated_versions(self):
        import hashlib
        for dependencies in ('explicit', 'legacy'):
            for operation in ('replace', 'revoke'):
                with self.subTest(dependencies=dependencies, operation=operation):
                    self.setUp()
                    payload = self.publication()
                    manager = ResumeManager(self.root)
                    fact = manager.add_fact('Fato usado antes.', 'candidate:test', True)['id']
                    other = manager.add_fact('Outro fato atual.', 'candidate:test', True)['id']
                    actions = []
                    for version, ids in ((2, [fact] if dependencies == 'explicit' else None),
                                         (3, [other]), (4, [])):
                        content = f'Texto fictício da versão {version}.'
                        self.presence.draft('github', content, payload['publication']['destination'], ids)
                        self.presence.finish('github', version, 'Conferido.')
                        payload['publication'].update(version=version, content_sha256=hashlib.sha256(content.encode()).hexdigest())
                        if version < 4:
                            payload['publication']['section'] = 'bio' if version == 2 else 'profile_readme'
                            actions.append(self.wf.authorize(payload)['action_id'])
                    if operation == 'revoke':
                        self.done(actions[0], 'uncertain', evidence_source='agent_report')
                    before = self.presence.get()
                    def correct():
                        if operation == 'replace':
                            return manager.replace_fact(fact, 'Fato corrigido.', 'candidate:test', True)
                        return manager.revoke_fact(fact, 'candidate:test', True)
                    result = correct()
                    self.assertEqual([a['id'] for a in result['open_authorizations']], [actions[0]])
                    self.assertEqual(result['open_authorizations'][0]['publication']['version'], 2)
                    self.assertEqual(self.presence.get()['reviews'], before['reviews'])
                    self.assertEqual(self.presence.get()['history'], before['history'])
                    self.assertEqual(correct()['open_authorizations'], result['open_authorizations'])
                    self.assertEqual(self.wf.show_action(actions[1])['status'], 'authorized')

    def test_revocation_between_validation_and_transaction_inserts_no_action(self):
        from scripts.job.presence import Presence
        payload = self.publication()
        manager = ResumeManager(self.root)
        fact = manager.add_fact('Fato original.', 'candidate:test', True)['id']
        original = Presence.publication
        calls = []
        def validate(instance, value):
            result = original(instance, value)
            calls.append(result)
            if len(calls) == 1:
                manager.revoke_fact(fact, 'candidate:test', True)
            return result
        with patch.object(Presence, 'publication', validate):
            with self.assertRaises(ValueError):
                self.wf.authorize(payload)
        with manager._db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM wf_actions WHERE action='profile_publish'").fetchone()[0], 0)
