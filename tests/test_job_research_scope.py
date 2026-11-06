import tempfile
import unittest
from pathlib import Path
from scripts.job.research_scope import ResearchScopes
from scripts.job.workflow import Workflow


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.scopes = ResearchScopes(self.root)

    def grant(self):
        return self.scopes.grant(dict(purpose='company_dossier', target={'kind':'company','id':'fiction'}, question='Jornada?', urls=['https://fiction.example/work'], user_confirmation='Autorizo essa consulta fictícia.'))

    def query(self, r):
        return dict(scope_id=r['id'], expected_version=r['version'], purpose=r['purpose'], target=r['target'], url=r['urls'][0])

    def test_read_without_state(self):
        self.assertEqual(self.scopes.list(), [])
        self.assertIsNone(self.scopes.get('missing'))
        self.assertFalse((self.root / '.job').exists())

    def test_exact_url_target_and_purpose(self):
        r = self.grant(); q = self.query(r)
        self.assertTrue(self.scopes.check(q)['allowed'])
        self.assertFalse(self.scopes.check(dict(q, url=q['url']+'/other'))['allowed'])
        self.assertFalse(self.scopes.check(dict(q, target={'kind':'company','id':'other'}))['allowed'])
        with self.assertRaises(ValueError): self.scopes.check(dict(q, purpose='career_exploration'))
        with self.assertRaises(ValueError): self.scopes.check(dict(q, url=q['url']+'?token=secret'))

    def test_stop_and_resume_generation(self):
        r = self.grant(); q = self.query(r)
        workflow = Workflow(self.root)
        self.addCleanup(workflow.close)
        workflow.stop('Parada fictícia de teste.')
        self.assertEqual(self.scopes.check(q)['reason'], 'stopped')
        with self.assertRaises(ValueError): self.grant()
        workflow.resume()
        self.assertEqual(self.scopes.check(q)['reason'], 'stale_generation')
        self.assertTrue(self.scopes.check(self.query(self.grant()))['allowed'])

    def test_revoke_history_and_stale_writer(self):
        r = self.grant(); payload = dict(scope_id=r['id'], expected_version=1)
        self.scopes.revoke(payload)
        with self.assertRaises(ValueError): ResearchScopes(self.root).revoke(payload)
        self.assertFalse(self.scopes.check(self.query(r))['allowed'])
        self.assertFalse(self.scopes.get(r['id'], 1)['revoked'])
        self.assertTrue(self.scopes.get(r['id'])['revoked'])

    def test_corrupt_record_rejected(self):
        self.grant()
        with self.scopes.profile._db(True) as db: db.execute("UPDATE job_research_scopes SET value='{}'")
        with self.assertRaises(ValueError): self.scopes.list()
