import copy
import tempfile
import unittest
from pathlib import Path
from scripts.job.company import CompanyDossiers
from scripts.job.research_scope import ResearchScopes
from scripts.job.due_diligence import DueDiligence


class CompanyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.company = CompanyDossiers(self.root)
        self.scopes = ResearchScopes(self.root)

    def fixture(self):
        r = self.company.create(dict(entity=dict(name='Aurora fictícia',country='BR',domain=None,relationship='employer'), question='Condições?', dimensions=['workload','salary']))
        scope = self.scopes.grant(dict(purpose='company_dossier',target={'kind':'company','id':r['id']},question='Condições?',urls=['https://fiction.example/work'],user_confirmation='Autorizo.'))
        evidence = dict(id='e1',dimension='workload',nature='report',statement='Relato fictício.',url=scope['urls'][0],checked_at='2000-01-01T12:00:00Z',published_at=None,context=dict(audience='consumer',role=None,location=None,period=None),origin_group='original',limitations=['Relato isolado.'],scope_id=scope['id'],scope_version=1)
        payload = dict(id=r['id'],expected_version=1,evidence=[evidence],salary_observations=[],contradictions=[],interview_questions=[],opportunity_link=None)
        return r, scope, payload

    def test_read_without_state(self):
        self.assertEqual(self.company.list(), [])
        self.assertIsNone(self.company.summary('missing'))
        self.assertFalse((self.root/'.job').exists())

    def test_duplicate_origins_and_consumer_context(self):
        r, s, p = self.fixture()
        p['evidence'].append(dict(p['evidence'][0], id='e2'))
        self.company.revise(p)
        summary = self.company.summary(r['id'])
        self.assertEqual(summary['independent_origin_counts']['workload'], 1)
        self.assertIn('workload', summary['unknown_dimensions'])
        self.assertEqual(summary['evidence'][0]['context']['audience'], 'consumer')
        self.assertIn('Aurora fictícia', summary['message'])

    def test_median_is_not_range_and_report_allowed(self):
        r,s,p = self.fixture()
        p['evidence'][0]['dimension'] = 'salary'
        salary = dict(evidence_id='e1',kind='statistic',currency='BRL',period='month',role='Dev',seniority='mid',location='Bahia',contract='CLT',sample_size=None,metric='median',value=8000,methodology='Autorrelato fictício.')
        p['salary_observations'] = [salary]
        self.company.revise(p)
        summary = self.company.summary(r['id'])
        self.assertEqual(summary['salary_observations'][0]['metric'], 'median')
        self.assertNotIn('minimum', summary['salary_observations'][0])
        for bad in (True, float('nan'), float('inf')):
            invalid = copy.deepcopy(p); invalid['expected_version']=2; invalid['salary_observations'][0]['value']=bad
            with self.assertRaises(ValueError): self.company.revise(invalid)

    def test_stale_writer_and_revoked_provenance_preserve_history(self):
        r,s,p = self.fixture(); self.company.revise(p)
        with self.assertRaises(ValueError): CompanyDossiers(self.root).revise(p)
        self.scopes.revoke(dict(scope_id=s['id'],expected_version=1))
        changed = copy.deepcopy(p)
        changed['evidence'][0]['statement'] = 'Nova observação sem autorização vigente.'
        with self.assertRaises(ValueError): self.company.revise(dict(changed, expected_version=2))
        self.assertEqual(self.company.get(r['id'])['version'], 2)
        self.assertEqual(self.company.get(r['id'],1)['evidence'], [])
        self.assertEqual(len(self.company.summary(r['id'])['evidence']), 1)

    def test_unknown_fields_and_missing_opportunity(self):
        r,s,p = self.fixture()
        with self.assertRaises(ValueError): self.company.revise(dict(p, extra=True))
        with self.assertRaises(ValueError): self.company.revise(dict(p, opportunity_link=dict(opportunity_id=42,evidence='Fictícia',url='https://fiction.example/job')))

    def test_legacy_and_profile_preserved(self):
        with self.company.profile._db(True) as db:
            db.execute('CREATE TABLE job_due_diligence(id INTEGER PRIMARY KEY,value TEXT)')
            db.execute('INSERT INTO job_due_diligence VALUES(1,?)', ('[{"id":"legacy","subject":"Fictícia"}]',))
        before = self.company.profile.get()
        legacy = DueDiligence(self.root).list()
        r,s,p = self.fixture(); self.company.revise(p)
        self.assertEqual(DueDiligence(self.root).list(), legacy)
        self.assertEqual(self.company.profile.get(), before)

    def test_malformed_persisted_record(self):
        self.fixture()
        with self.company.profile._db(True) as db: db.execute("UPDATE job_company_dossiers SET value='{}'")
        with self.assertRaises(ValueError): self.company.list()
