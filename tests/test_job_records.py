import tempfile
import unittest
from pathlib import Path
from scripts.job.records import coverage, mail_coverage, ledger


class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="job-records-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_empty_queries_do_not_create_state(self):
        self.assertEqual(coverage(self.root), [])
        self.assertEqual(ledger(self.root, "steps"), [])
        self.assertEqual(mail_coverage(self.root, "show"), {"accounts": [], "runs": []})
        self.assertFalse((self.root / ".job").exists())

    def test_partial_search_preserves_checkpoint(self):
        entry = {"source": "portal-ficticio", "query": "atendimento remoto", "pages": 2,
                 "status": "partial", "checked_at": "2020-01-01T12:00:00Z",
                 "next_action": "Continuar na terceira página", "position": "Página dois conferida"}
        coverage(self.root, entry)
        saved = coverage(self.root)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["status"], "partial")
        self.assertEqual(saved[0]["next_action"], entry["next_action"])
        with self.assertRaises(ValueError):
            coverage(self.root, {**entry, "status": "complete", "pages": 0})
        self.assertEqual(len(coverage(self.root)), 1)

    def test_mail_partial_is_not_complete(self):
        run = mail_coverage(self.root, "begin", {"minutes": 10})
        self.assertTrue(run["acquired"])
        data = {"run_id": run["run_id"], "provider": "gmail", "account": "primary", "status": "partial", "note": "Consulta interrompida"}
        mail_coverage(self.root, "account", data)
        with self.assertRaises(ValueError):
            mail_coverage(self.root, "account", {**data, "status": "complete"})
        state = mail_coverage(self.root, "show")
        self.assertIsNone(state["accounts"][0]["covered_until"])
        self.assertEqual(state["accounts"][0]["status"], "partial")
        mail_coverage(self.root, "finish", {"run_id": run["run_id"]})


if __name__ == "__main__":
    unittest.main()
