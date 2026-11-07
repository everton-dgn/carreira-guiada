"""Deadline regressions use a fake clock and never start a model."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.maintainers import bench_tools
from scripts.maintainers.bench_candidate import seed
from scripts.maintainers.bench_score import collect, grade


class SessionDeadlineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='fictional-deadline-')
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name).resolve()
        seed(self.directory)

    def test_missing_session_and_expired_session_cannot_dispatch(self):
        tools = bench_tools.Tools(self.directory, None, require_session=True)
        with patch.object(tools, 'dispatch') as dispatch:
            self.assertFalse(tools.invoke({'op': 'say', 'message': 'Teste'})['ok'])
            dispatch.assert_not_called()
            with patch.object(bench_tools.time, 'time', return_value=1000):
                bench_tools.begin_session(self.directory)
            with patch.object(bench_tools.time, 'time', return_value=1241):
                self.assertFalse(tools.invoke({'op': 'say', 'message': 'Tarde'})['ok'])
            dispatch.assert_not_called()

    def test_operation_finishing_late_fails_and_blocks_next_batch_item(self):
        with patch.object(bench_tools.time, 'time', return_value=1000):
            bench_tools.begin_session(self.directory)
        tools = bench_tools.Tools(self.directory, None, require_session=True)
        with patch.object(tools, 'dispatch', return_value={'observed': True}) as dispatch:
            with patch.object(bench_tools.time, 'time', side_effect=[1239, 1241]):
                result = tools.invoke({'op': 'say', 'message': 'Teste'})
            self.assertFalse(result['ok'])
            self.assertTrue(result['outside_session_deadline'])
            with patch.object(bench_tools.time, 'time', return_value=1242):
                self.assertFalse(tools.invoke({'op': 'say', 'message': 'Outra'})['ok'])
            self.assertEqual(dispatch.call_count, 1)

    def test_finish_cannot_erase_a_timeout_or_restart_a_session(self):
        with patch.object(bench_tools.time, 'time', return_value=1000):
            bench_tools.begin_session(self.directory)
            with self.assertRaises(FileExistsError):
                bench_tools.begin_session(self.directory)
        with patch.object(bench_tools.time, 'time', return_value=1241):
            first = bench_tools.finish_session(self.directory)
        with patch.object(bench_tools.time, 'time', return_value=1200):
            self.assertEqual(bench_tools.finish_session(self.directory), first)
        self.assertTrue(first['timed_out'])

    def test_no_tool_calls_still_produce_an_unsuccessful_result(self):
        (self.directory / 'destination.json').write_text(json.dumps({
            'applications': [], 'replies': [], 'complements': []}))
        (self.directory / 'browser-state.json').write_text('{}')
        evidence = collect(self.directory)
        self.assertEqual(evidence['events'], [])
        result = grade(evidence)
        self.assertFalse(any(s['complete'] for s in result['stages'].values()))


class DeadlineGradingTests(unittest.TestCase):
    def test_two_finished_sessions_preserve_observed_credit(self):
        path = Path(__file__).resolve().parents[1] / 'docs/benchmarks/browser-mail-2026-11-07/terra-medium.json'
        evidence = json.loads(path.read_text())
        evidence['sessions'] = [
            {'phase': phase, 'started_at': 1000, 'deadline': 1240,
             'finished_at': 1100, 'timed_out': False} for phase in (1, 2)]
        result = grade(evidence)
        self.assertTrue(result['session_timing_valid'])
        self.assertTrue(all(s['complete'] for s in result['stages'].values()))
        self.assertEqual(result['effects']['applications'], 1)

    def test_late_or_unfinished_sessions_never_receive_stage_credit(self):
        path = Path(__file__).resolve().parents[1] / 'docs/benchmarks/browser-mail-2026-11-07/terra-medium.json'
        for end in (None, 1241):
            with self.subTest(end=end):
                evidence = json.loads(path.read_text())
                evidence['sessions'] = [
                    {'phase': 1, 'started_at': 1000, 'deadline': 1240, 'finished_at': end, 'timed_out': False},
                    {'phase': 2, 'started_at': 2000, 'deadline': 2240, 'finished_at': 2100, 'timed_out': False}]
                result = grade(evidence)
                self.assertFalse(any(s['complete'] for s in result['stages'].values()))
                self.assertEqual(result['effects'], {'applications': 0, 'replies': 0, 'complements': 0})
                self.assertEqual(result['observed_effects']['applications'], 1)
                self.assertFalse(result['session_timing_valid'])
