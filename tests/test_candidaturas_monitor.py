import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from scripts.candidaturas.monitor import Monitor, stamp, utcnow


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="candidaturas-monitor-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "control.sqlite3"
        self.monitor = Monitor(self.path)

    def tearDown(self):
        self.monitor.db.close()

    def window(self):
        return {"window_start": stamp(utcnow() - timedelta(days=1)), "window_end": stamp(utcnow() - timedelta(seconds=1))}

    def test_concurrent_monitor_cannot_acquire_live_run(self):
        first = self.monitor.begin()
        second = Monitor(self.path)
        self.assertTrue(first["acquired"])
        self.assertFalse(second.begin()["acquired"])
        second.db.close()

    def test_failure_preserves_completed_coverage(self):
        run = self.monitor.begin()["run_id"]
        result = self.monitor.account(run, "gmail", "primary", "complete", note="recruitment-v1: todas as páginas conferidas", **self.window())
        covered = result["accounts"][0]["covered_until"]
        result = self.monitor.account(run, "gmail", "primary", "unavailable", note="Falha de ferramenta")
        self.assertEqual(result["accounts"][0]["covered_until"], covered)
        self.assertFalse(result["accounts"][0]["due"])

    def test_partial_does_not_claim_coverage(self):
        run = self.monitor.begin()["run_id"]
        self.monitor.account(run, "outlook", "primary", "partial", **self.window())
        self.assertIsNone(self.monitor.status()["accounts"][0]["covered_until"])

    def test_complete_requires_window_and_rejects_gap(self):
        run = self.monitor.begin()["run_id"]
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "primary", "complete")
        self.monitor.account(run, "gmail", "primary", "complete", note="recruitment-v1: todas as páginas conferidas", window_start=stamp(utcnow() - timedelta(days=3)), window_end=stamp(utcnow() - timedelta(days=2)))
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "primary", "complete", note="recruitment-v1: todas as páginas conferidas", **self.window())

    def test_expired_run_cannot_write_and_next_run_recovers(self):
        run = self.monitor.begin()["run_id"]
        self.monitor.db.execute("UPDATE monitor_runs SET expires_at=? WHERE id=?", (stamp(utcnow() - timedelta(seconds=1)), run))
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "primary", "partial")
        self.assertTrue(self.monitor.begin()["acquired"])
        self.assertEqual(self.monitor.db.execute("SELECT status FROM monitor_runs WHERE id=?", (run,)).fetchone()[0], "interrupted")

    def test_gmail_failure_does_not_block_outlook(self):
        run = self.monitor.begin()["run_id"]
        self.monitor.account(run, "gmail", "primary", "auth_required")
        self.monitor.account(run, "outlook", "primary", "complete", note="recruitment-v1: todas as páginas conferidas", **self.window())
        self.assertEqual([a["status"] for a in self.monitor.status()["accounts"]], ["auth_required", "complete"])

    def test_finished_run_cannot_resume(self):
        run = self.monitor.begin()["run_id"]
        self.monitor.finish(run)
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "primary", "partial")

    def test_no_personal_account_address_or_secret_link(self):
        run = self.monitor.begin()["run_id"]
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "person@example.test", "partial")
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "primary", "partial", note="https://example.test?token=secret")

    def test_company_search_cannot_advance_shared_watermark(self):
        run = self.monitor.begin()["run_id"]
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "primary", "complete", note="Busca Empresa A", **self.window())
        with self.assertRaises(ValueError):
            self.monitor.account(run, "gmail", "primary", "complete", query="company-a", note="recruitment-v1: todas as páginas conferidas", **self.window())

    def test_invalid_date_error_does_not_echo_private_input(self):
        run = self.monitor.begin()["run_id"]
        with self.assertRaises(ValueError) as error:
            self.monitor.account(run, "gmail", "primary", "partial", window_start="https://example.test?token=private", window_end=stamp())
        self.assertNotIn("private", str(error.exception))
        self.assertNotIn("example.test", str(error.exception))


if __name__ == "__main__":
    unittest.main()
