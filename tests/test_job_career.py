import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.job.career import CareerGuide, QUESTIONS
from scripts.job.profile import Profile


class CareerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.g = CareerGuide(self.root)

    def update(self, method, s, **data):
        return getattr(self.g, method)(dict(id=s['id'], expected_version=s['version'], **data))

    def ready(self):
        s = self.g.start({})
        for f in QUESTIONS: s = self.update('answer', s, field=f, value=None)
        return s

    def alternatives(self, s):
        return [dict(id='a', title='Explorar uma tarefa fictícia', gains=['Aprender'], costs=['Tempo'], gaps=['Experiência desconhecida'], basis=[dict(answer_field='goal', answer_version=s['answers']['goal']['version'])])]

    def selected(self):
        s = self.ready()
        s = self.update('propose', s, alternatives=self.alternatives(s))
        return self.update('choose', s, alternative_id='a', user_confirmation='Quero experimentar')

    def test_empty_reads(self):
        self.assertIsNone(self.g.get('missing'))
        self.assertEqual(self.g.status()['count'], 0)
        self.assertFalse((self.root/'.job').exists())

    def test_null_progression_and_history(self):
        s = self.g.start({})
        for f in QUESTIONS:
            self.assertEqual(self.g.status()['question']['field'], f)
            s = self.update('answer', s, field=f, value=None)
        self.assertIsNone(self.g.status()['question'])
        self.assertEqual(self.g.get(s['id'], 1)['answers'], {})
        self.assertEqual(self.g.start({}), s)
        self.assertEqual(Profile(self.root).get(), dict(version=0, approved_version=None, sections={}))

    def test_stale_versions_and_basis(self):
        s = self.ready()
        with self.assertRaises(ValueError): self.g.answer(dict(id=s['id'], expected_version=1, field='goal', value='Fictício'))
        a = self.alternatives(s); a[0]['basis'][0]['answer_version'] = 1
        with self.assertRaises(ValueError): self.update('propose', s, alternatives=a)
        self.assertEqual(self.g.get(s['id']), s)

    def test_pause_resume_and_correction(self):
        s = self.selected()
        old = s
        self.assertEqual(self.update('answer', s, field='goal', value=None), s)
        s = self.update('pause', s)
        self.g = CareerGuide(self.root)
        with self.assertRaises(ValueError): self.update('answer', s, field='goal', value='Novo')
        self.assertEqual(self.g.start({}), s)
        s = self.update('resume', s)
        s = self.update('answer', s, field='goal', value='Explorar trabalho fictício')
        self.assertEqual(s['alternatives'], [])
        self.assertIsNone(s['selection'])
        self.assertEqual(self.g.get(s['id'], old['version']), old)

    def test_experiment_and_reflection(self):
        s = self.selected()
        d = dict(activity='Atividade fictícia', duration_days=7, time_budget_minutes=120, learning_criterion='Anotar preferências', user_confirmation='Cabe no meu tempo')
        for key, val in [('duration_days',True),('duration_days',0),('duration_days',91),('time_budget_minutes',float('nan')),('time_budget_minutes',float('inf')),('user_confirmation','')]:
            with self.assertRaises(ValueError): self.update('experiment',s,**(d|{key:val}))
        s = self.update('experiment',s,**d)
        s = self.update('reflect',s,observations=None,learned=None,next_decision='defer')
        self.assertEqual(s['phase'],'finished')
        self.assertNotEqual(self.g.start({})['id'],s['id'])

    def test_no_auto_approval_or_incomplete_proposal(self):
        s = self.g.start({})
        with self.assertRaises(ValueError): self.update('propose',s,alternatives=[])
        s = self.ready()
        s = self.update('propose',s,alternatives=self.alternatives(s))
        with self.assertRaises(ValueError): self.update('choose',s,alternative_id='a',user_confirmation=True)
        with self.assertRaises(ValueError): self.update('answer',s,field='goal',value=['skill invented'])
        with self.assertRaises(ValueError): self.g.start({'approved':True})

    def test_corrupt_persisted_record_rejected(self):
        s = self.ready()
        with self.g.profile._db(True) as db:
            db.execute('UPDATE career_revisions SET value=? WHERE id=? AND version=?', ('{}',s['id'],s['version']))
        with self.assertRaises(ValueError): self.g.status()

    def test_scope_mismatch_rolls_back(self):
        import sys
        import types
        from unittest.mock import Mock
        checker = Mock()
        checker.check.return_value = {'allowed':False}
        module = types.ModuleType('scripts.job.research_scope')
        module.ResearchScopes = Mock(return_value=checker)
        s = self.ready(); a = self.alternatives(s)
        a[0]['market_evidence'] = [dict(statement='Relato fictício',url='https://example.org/career',checked_at='2000-01-01T12:00:00Z',scope_id='fictitious',scope_version=1,limitations=['Não validado ao vivo'])]
        with patch.dict(sys.modules, {'scripts.job.research_scope':module}):
            with self.assertRaises(ValueError): self.update('propose',s,alternatives=a)
        self.assertEqual(checker.check.call_args.args[0]['target'],dict(kind='career',id=s['id']))
        self.assertIsNotNone(checker.check.call_args.kwargs['db'])
        self.assertEqual(self.g.get(s['id']),s)

    def test_existing_operational_profile_unchanged(self):
        p = Profile(self.root)
        p.save('identity', {'name':'Pessoa Fictícia','email':'fiction@example.org'})
        p.save('permissions', {'research':'deny','apply':'ask'})
        before = p.get()
        self.selected()
        self.assertEqual(p.get(), before)

    def test_real_scope_target_mismatch_and_authorized_evidence(self):
        from scripts.job.research_scope import ResearchScopes
        s = self.ready()
        scopes = ResearchScopes(self.root)
        scope = scopes.grant(dict(purpose='career_exploration', target=dict(kind='career',id=s['id']), question='Explorar tarefa fictícia', urls=['https://example.org/career'],user_confirmation='Autorizo esta consulta fictícia'))
        a = self.alternatives(s)
        a[0]['market_evidence'] = [dict(statement='Evidência simulada',url='https://example.org/career',checked_at='2000-01-01T12:00:00Z',scope_id=scope['id'],scope_version=scope['version'],limitations=['Simulação local'])]
        s = self.update('propose',s,alternatives=a)
        self.assertEqual(s['phase'],'alternatives')
        scopes.revoke(dict(scope_id=scope['id'],expected_version=scope['version']))
        with self.assertRaises(ValueError): self.update('propose',s,alternatives=a)
        self.assertEqual(self.g.get(s['id']),s)
