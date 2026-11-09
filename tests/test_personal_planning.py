import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from unittest.mock import patch
from pathlib import Path

from scripts.job.planning import PersonalPlan
from scripts.job.career import CareerGuide
from scripts.job.profile import Profile
from scripts.job.practice import Practice


class PlanningTests(unittest.TestCase):
    def setUp(self):
        """Create isolated private storage for each fictional planning scenario."""
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.plan = PersonalPlan(self.root)

    def tearDown(self):
        """Remove the temporary fixture after the scenario finishes."""
        self.tmp.cleanup()

    def add(self, s, ident, minutes, period):
        """Add one fictional practice action to a specified week."""
        return self.plan.action({'id': s['id'], 'expected_version': s['version'], 'action': {
            'id': ident, 'activity': 'practice', 'title': ident, 'reason': 'Aprender',
            'criterion': 'Terminar', 'estimated_minutes': minutes, 'period': period}})

    def test_empty_read_has_no_writes(self):
        """Reading a new plan must not initialize the private database."""
        self.assertIsNone(self.plan.get())
        self.assertFalse(self.plan.status()['exists'])
        self.assertFalse((self.root / '.job').exists())

    def test_budget_separate_weeks_and_completion(self):
        """Weekly capacity stays separate and completed work survives budget changes."""
        s = self.plan.start({'weekly_minutes': 90})
        s = self.add(s, 'a', 60, '2026-11-09')
        s = self.add(s, 'b', 30, '2026-11-16')
        status = self.plan.status()
        self.assertEqual([p['planned_minutes'] for p in status['budget']['periods']], [60, 30])
        self.assertEqual(status['budget']['periods'][0]['remaining_minutes'], 30)
        s = self.plan.transition({'id': s['id'], 'expected_version': s['version'], 'action_id': 'a', 'state': 'completed', 'evidence': {'kind': 'user_report', 'description': 'Fiz a atividade', 'criterion': 'Terminar'}})
        s = self.plan.update({'id': s['id'], 'expected_version': s['version'], 'weekly_minutes': 10})
        self.assertEqual(s['actions'][0]['state'], 'completed')
        self.assertEqual(self.plan.status()['budget']['periods'][0]['over_by_minutes'], 20)

    def test_unknown_and_no_period(self):
        """Unknown estimates and unscheduled actions remain explicitly unknown."""
        s = self.plan.start({})
        s = self.add(s, 'a', None, '2026-11-09')
        s = self.add(s, 'b', 10, None)
        b = self.plan.status()['budget']
        self.assertIsNone(b['periods'][0]['planned_minutes'])
        self.assertIsNone(b['periods'][0]['remaining_minutes'])
        self.assertEqual(b['without_period'][0]['id'], 'b')

    def test_versions_concurrency_invalid_and_pause(self):
        """Stale or invalid writes preserve history through pause and resume."""
        s = self.plan.start({'direction': 'Estudar'})
        first = s.copy()
        s = self.add(s, 'a', 30, None)
        with self.assertRaises(ValueError): self.plan.update({'id': s['id'], 'expected_version': 1, 'direction': 'Outro'})
        with self.assertRaises(ValueError): self.plan.update({'id': s['id'], 'expected_version': s['version'], 'weekly_minutes': True})
        with self.assertRaises(ValueError): self.plan.transition({'id': s['id'], 'expected_version': s['version'], 'action_id': 'a', 'state': 'completed'})
        self.assertEqual(self.plan.get(), s)
        s = self.plan.pause({'id': s['id'], 'expected_version': s['version']})
        self.assertEqual(self.plan.status()['state'], 'paused')
        self.assertEqual(self.plan.get(s['id'], 1), first)
        s = self.plan.resume({'id': s['id'], 'expected_version': s['version']})
        self.assertEqual(s['actions'][0]['state'], 'planned')
        self.assertEqual(len(self.plan.history(s['id'])), 4)

    def test_references_and_no_operational_effect(self):
        """Source references must exist and planning cannot change operational permissions."""
        with self.assertRaises(ValueError): self.plan.start({'basis': [{'kind': 'career', 'id': 'missing', 'version': 1}]})
        career = CareerGuide(self.root).start({})
        s = self.plan.start({'basis': [{'kind': 'career', 'id': career['id'], 'version': 1}]})
        before = Profile(self.root).get()
        s = self.add(s, 'a', 20, None)
        self.plan.transition({'id': s['id'], 'expected_version': s['version'], 'action_id': 'a', 'state': 'completed', 'evidence': {'kind': 'user_report', 'description': 'Feito', 'criterion': 'Terminar'}})
        self.assertEqual(Profile(self.root).get(), before)
        self.assertFalse(self.plan.status()['basis'][0]['changed'])

    def test_practice_reference_and_changed_source(self):
        """A new practice attempt marks advice based on the earlier answer stale."""
        practice = Practice(self.root)
        started = practice.start('presentation', 'coach', short=True)
        sid = started['session_id']
        qid = started['question']['id']
        practice.answer(sid, qid, 'Primeira resposta')
        ref = {'kind': 'practice', 'session_id': sid, 'question_id': qid, 'version': 1}
        s = self.plan.start({'basis': [ref]})
        self.assertFalse(self.plan.status()['basis'][0]['changed'])
        practice.answer(sid, qid, 'Outra resposta')
        self.assertTrue(self.plan.status()['basis'][0]['changed'])
        self.assertEqual(self.plan.get(s['id'], 1)['basis'], [ref])

    def test_review_archive_and_reuse(self):
        """Archival preserves reflections while allowing a distinct new plan."""
        s = self.plan.start({})
        self.assertEqual(self.plan.start({})['id'], s['id'])
        s = self.plan.review({'id': s['id'], 'expected_version': s['version'], 'observation': 'Ainda sem resultado', 'next_step': 'Continuar', 'decision': 'continue'})
        s = self.plan.archive({'id': s['id'], 'expected_version': s['version']})
        self.assertEqual(s['reflections'][0]['observation'], 'Ainda sem resultado')
        self.assertNotEqual(self.plan.start({})['id'], s['id'])

    def test_feedback_edit_marks_same_attempt_reference_stale(self):
        """A changed source must not silently keep the old planning advice current."""
        practice = Practice(self.root)
        started = practice.start('presentation', 'coach', short=True)
        sid, qid = started['session_id'], started['question']['id']
        practice.answer(sid, qid, 'Minha resposta fictícia')
        practice.feedback(sid, qid, 1, 'Clareza', 'Contexto', 'Explicar', 'Ensaiar')
        self.plan.start({'basis': [{'kind': 'practice', 'session_id': sid, 'question_id': qid, 'version': 1}]})
        self.assertFalse(self.plan.status()['basis'][0]['changed'])
        practice.feedback(sid, qid, 1, 'Clareza', 'Outro foco', 'Explicar', 'Ensaiar')
        self.assertTrue(self.plan.status()['basis'][0]['changed'])

    def test_week_must_start_on_monday(self):
        """Two dates inside one week cannot create two independent time budgets."""
        s = self.plan.start({'weekly_minutes': 90})
        with self.assertRaises(ValueError):
            self.add(s, 'a', 60, '2026-11-10')

    def test_concurrent_writers_cannot_replace_the_same_revision(self):
        """The database admits one update and rejects the stale competing writer."""
        plan = self.plan.start({})
        def write(direction):
            """Attempt a competing revision and report whether it was accepted."""
            try:
                PersonalPlan(self.root).update({'id': plan['id'], 'expected_version': 1, 'direction': direction})
                return 'saved'
            except ValueError:
                return 'stale'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, ['Atendimento', 'Administração']))
        self.assertCountEqual(results, ['saved', 'stale'])
        self.assertEqual(len(self.plan.history(plan['id'])), 2)

    def test_action_edit_preserves_omitted_source_and_its_snapshot(self):
        """Editing an estimate does not make unchanged advice appear stale."""
        practice = Practice(self.root)
        started = practice.start('presentation', 'coach', short=True)
        sid, qid = started['session_id'], started['question']['id']
        practice.answer(sid, qid, 'Minha resposta')
        plan = self.plan.start({})
        action = {'id': 'a', 'activity': 'practice', 'title': 'Treinar', 'reason': 'Aprender',
            'criterion': 'Ensaiar', 'estimated_minutes': 20, 'period': None,
            'source': {'kind': 'practice', 'session_id': sid, 'question_id': qid, 'version': 1}}
        plan = self.plan.action({'id': plan['id'], 'expected_version': plan['version'], 'action': action})
        action.pop('source')
        action['estimated_minutes'] = 10
        self.plan.action({'id': plan['id'], 'expected_version': plan['version'], 'action': action})
        self.assertFalse(self.plan.status()['basis'][0]['changed'])

    def test_failed_write_rolls_back_revision_and_keeps_previous_plan(self):
        """A database error after insertion cannot leave a false saved revision."""
        plan = self.plan.start({'direction': 'Atendimento'})
        save = PersonalPlan._save
        def fail_after_insert(db, value):
            """Inject a failure after insertion to exercise transaction rollback."""
            save(db, value)
            raise sqlite3.OperationalError('fictional disk failure')
        with patch.object(PersonalPlan, '_save', side_effect=fail_after_insert):
            with self.assertRaises(sqlite3.OperationalError):
                self.plan.update({'id': plan['id'], 'expected_version': 1, 'direction': 'Administração'})
        self.assertEqual(self.plan.get(), plan)
        self.assertEqual(len(self.plan.history(plan['id'])), 1)


if __name__ == '__main__': unittest.main()
