"""Synthetic ledger tests. Temporary fixtures are removed after each test."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import stat
import sqlite3
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from candidaturas.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="candidaturas-store-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / "private" / "ledger.sqlite3"
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close()

    def record(self, **changes):
        result = dict(source_key="vaga-a", company="Empresa Exemplo", title="Frontend Sênior", portal="gupy", aliases=["job:gupy:123", "url:https://exemplo.gupy.io/jobs/123"], state="discovered", confirmed_at=None, evidence="Anúncio público verificado", eligible=True, identity_verified=True, notes=[])
        result.update(changes)
        return result

    def job(self, **changes):
        return self.store.import_records([self.record(**changes)], "synthetic")["job_ids"][0]

    def step(self, **changes):
        payload = dict(job_id=self.job(), step_key="interview-1", kind="interview", summary="Entrevista técnica", due_at="2026-09-15T14:00:00-03:00", safe_url="https://example.com/careers")
        payload.update(changes)
        return self.store.upsert_step(payload)

    def test_private_database_and_schema(self):
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(self.store.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.store.conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.store.conn.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_import_idempotency_exact_alias_and_no_title_merge(self):
        first = self.job()
        repeated = self.store.import_records([self.record()], "synthetic")
        self.assertEqual(repeated["unchanged"], 1)
        alternate = self.store.import_records([self.record(source_key="other-source")], "other")
        self.assertEqual(alternate["job_ids"], [first])
        different = self.store.import_records([self.record(source_key="another-job", aliases=["job:gupy:456"])], "synthetic")
        self.assertNotEqual(different["job_ids"], [first])
        self.assertEqual(self.store.summary()["opportunities"], 2)

    def test_confirmation_cannot_regress_or_be_dated_today(self):
        self.job(state="confirmed", confirmed_at=None, evidence="Portal confirmou a candidatura")
        self.store.import_records([self.record(state="candidate_pending")], "synthetic")
        job = self.store.list_jobs()[0]
        self.assertEqual(job["state"], "confirmed")
        self.assertIsNone(job["confirmed_at"])
        self.assertEqual(job["evidence"], "Portal confirmou a candidatura")
        self.assertEqual(self.store.summary(since="2026-09-01")["period_confirmed"], 0)
        self.assertEqual(self.store.summary()["confirmed_without_date"], 1)

    def test_period_counts_unique_verified_eligible_confirmations_only(self):
        records = [self.record(source_key=str(index), aliases=[f"job:gupy:{index}"], state="confirmed", confirmed_at=confirmed_at, eligible=eligible, identity_verified=verified) for index, confirmed_at, eligible, verified in [(1, "2026-09-10", True, True), (2, "2026-09-09", True, True), (3, "2026-09-10", None, True), (4, "2026-09-10", False, True), (5, "2026-09-10", True, False), (6, None, True, True)]]
        self.store.import_records(records, "synthetic")
        summary = self.store.summary("2026-09-10", "2026-09-10")
        self.assertEqual(summary["confirmed"], 5)
        self.assertEqual(summary["historical_confirmed_records"], 6)
        self.assertEqual(summary["eligible_confirmed"], 3)
        self.assertEqual(summary["period_confirmed"], 1)

    def test_conflicting_alias_preserves_evidence_and_blocks_verified_count(self):
        original = self.job(state="confirmed", confirmed_at="2026-09-10")
        result = self.store.import_records([self.record(source_key="conflicting", company="Outra Empresa", state="confirmed", confirmed_at="2026-09-10")], "other")
        self.assertEqual(result["conflicts"], 1)
        self.assertNotEqual(result["job_ids"], [original])
        self.assertEqual(self.store.summary()["identity_conflicts"], 2)
        self.assertEqual(self.store.summary()["period_confirmed"], 0)
        self.assertEqual(self.store.summary()["confirmed"], 0)
        self.assertEqual(self.store.summary()["historical_confirmed_records"], 2)

    def test_same_source_changed_identity_does_not_confirm_wrong_job(self):
        self.job()
        self.store.import_records([self.record(company="Outra Empresa", state="confirmed", confirmed_at="2026-09-10")], "synthetic")
        job = self.store.list_jobs()[0]
        self.assertEqual(job["company"], "Empresa Exemplo")
        self.assertEqual(job["state"], "discovered")
        self.assertIsNone(job["confirmed_at"])
        self.assertTrue(job["conflicts"])

    def test_unverified_alias_does_not_silently_merge(self):
        self.job()
        self.store.import_records([self.record(source_key="other", identity_verified=False)], "other")
        self.assertEqual(self.store.summary()["record_count"], 2)
        self.assertEqual(self.store.summary()["opportunities"], 0)
        self.assertEqual(self.store.summary()["identity_conflicts"], 2)

    def test_new_identity_reservation_revokes_prior_verification(self):
        self.job(state="confirmed", confirmed_at="2026-09-10")
        self.assertEqual(self.store.summary()["confirmed"], 1)
        self.store.import_records([self.record(state="confirmed", confirmed_at="2026-09-10", identity_verified=False, notes=["ID público requer nova verificação"])], "synthetic")
        self.assertEqual(self.store.summary()["confirmed"], 0)
        self.assertEqual(self.store.summary()["historical_confirmed_records"], 1)

    def test_application_id_alone_neither_verifies_nor_merges_vacancy(self):
        self.job(state="confirmed", confirmed_at="2026-09-10", aliases=["application:gupy:123"])
        self.assertEqual(self.store.summary()["confirmed"], 0)
        self.store.import_records([self.record(source_key="other", aliases=["application:gupy:123"])], "other")
        self.assertEqual(self.store.summary()["record_count"], 2)
        self.assertEqual(self.store.summary()["opportunities"], 0)

    def test_bulk_validation_is_atomic(self):
        with self.assertRaises(ValueError):
            self.store.import_records([self.record(), self.record(source_key="bad", state="invented")], "synthetic")
        self.assertEqual(self.store.list_jobs(), [])

    def test_snapshot_withdraws_rows_from_totals_without_erasing_evidence(self):
        original = [self.record(source_key="old-pending", aliases=["job:gupy:1"]), self.record(source_key="old-history", aliases=["job:gupy:2"], state="confirmed", confirmed_at="2026-09-10")]
        first = self.store.import_snapshot(original, "workspace-markdown")
        replacement = self.record(source_key="fixed-history", aliases=["job:gupy:3"], state="confirmed", confirmed_at="2026-09-10")
        self.store.import_snapshot([replacement], "workspace-markdown")
        jobs = self.store.list_jobs()
        self.assertEqual(len(jobs), 3)
        self.assertEqual([job["active"] for job in jobs], [False, False, True])
        self.assertEqual(jobs[1]["state"], "confirmed")
        self.assertEqual(jobs[1]["confirmed_at"], "2026-09-10")
        self.assertEqual(jobs[1]["evidence"], original[1]["evidence"])
        self.assertEqual(self.store.summary()["confirmed"], 1)
        self.assertEqual(self.store.summary()["opportunities"], 1)
        self.assertEqual(self.store.summary()["inactive_records"], 2)
        self.assertTrue(all(job["id"] not in first["job_ids"] for job in jobs if job["active"]))

    def test_snapshot_same_alias_retains_identity_and_snapshot_is_idempotent(self):
        first = self.store.import_snapshot([self.record()], "workspace-markdown")
        changed = self.record(source_key="changed-key", aliases=["job:gupy:123", "job:linkedin:456"])
        second = self.store.import_snapshot([changed], "workspace-markdown")
        self.assertEqual(first["job_ids"], second["job_ids"])
        self.assertEqual(self.store.summary()["record_count"], 1)
        self.assertEqual(sum(source["active"] for source in self.store.list_jobs()[0]["sources"]), 1)
        published = dict(self.store.conn.execute("SELECT * FROM source_snapshots").fetchone())
        self.assertEqual(self.store.import_snapshot([changed], "workspace-markdown")["unchanged"], 1)
        self.assertEqual(dict(self.store.conn.execute("SELECT * FROM source_snapshots").fetchone()), published)

    def test_empty_snapshot_preserves_other_sources_and_step_evidence(self):
        job_id = self.store.import_snapshot([self.record()], "workspace-markdown")["job_ids"][0]
        self.store.import_records([self.record(source_key="other-job", aliases=["job:gupy:456"])], "another-source")
        step = self.store.upsert_step(dict(job_id=job_id, step_key="test", kind="test"))
        self.store.ingest_message(dict(provider="gmail", account="principal", message_id="test-mail", job_id=job_id, step_key="test", kind="test"))
        self.store.import_snapshot([], "workspace-markdown")
        self.assertEqual(self.store.summary()["opportunities"], 1)
        self.assertEqual(self.store.summary()["pending_steps"], 1)
        self.assertEqual(self.store.list_steps()[0]["id"], step["id"])
        self.assertEqual(self.store.list_steps()[0]["messages"][0]["message_id"], "test-mail")
        self.assertFalse(self.store.list_jobs()[0]["active"])

    def test_snapshot_publication_failure_rolls_back_import_and_active_keys(self):
        self.store.import_snapshot([self.record()], "workspace-markdown")
        before = self.store.list_jobs()
        self.store.conn.execute("CREATE TRIGGER reject_snapshot BEFORE UPDATE ON source_snapshots BEGIN SELECT RAISE(ABORT, 'synthetic publication failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.import_snapshot([self.record(source_key="new", aliases=["job:gupy:456"])], "workspace-markdown")
        self.assertEqual(self.store.list_jobs(), before)

    def test_snapshot_bad_input_does_not_advance_coverage_or_deactivate(self):
        self.store.import_snapshot([self.record()], "workspace-markdown")
        with self.assertRaises(ValueError):
            self.store.import_snapshot([self.record(state="invalid")], "workspace-markdown")
        with self.assertRaises(ValueError):
            self.store.import_snapshot([self.record(), self.record()], "workspace-markdown")
        self.assertTrue(self.store.list_jobs()[0]["active"])

    def test_incremental_import_can_reactivate_a_withdrawn_source_record(self):
        self.store.import_snapshot([self.record()], "workspace-markdown")
        self.store.import_snapshot([], "workspace-markdown")
        self.store.import_records([self.record()], "workspace-markdown")
        self.assertEqual(self.store.summary()["opportunities"], 1)
        self.assertEqual(self.store.summary()["record_count"], 1)

    def test_existing_schema_one_database_accepts_snapshot_without_data_loss(self):
        job_id = self.job(state="confirmed", confirmed_at="2026-09-10", eligible=None)
        self.store.close()
        self.store = Store(self.path)
        self.store.import_snapshot([self.record(state="confirmed", confirmed_at="2026-09-10", eligible=None)], "synthetic")
        self.assertEqual(self.store.list_jobs()[0]["id"], job_id)
        self.assertEqual(self.store.summary()["compatible_unknown"], 1)
        self.assertEqual(self.store.conn.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_cross_mailbox_reminders_use_one_step_and_never_confirm(self):
        job_id = self.job()
        message = dict(provider="gmail", account="principal", message_id="mail-1", job_id=job_id, step_key="test-1", kind="test", summary="Responder ao teste")
        first = self.store.ingest_message(message)
        self.assertTrue(self.store.ingest_message(message)["duplicate"])
        second = self.store.ingest_message({**message, "provider": "outlook", "account": "secundaria", "message_id": "mail-2"})
        self.assertEqual(first["step_id"], second["step_id"])
        self.assertEqual(self.store.summary()["messages"], 2)
        self.assertEqual(self.store.summary()["pending_steps"], 1)
        self.assertEqual(self.store.summary()["confirmed"], 0)
        self.assertEqual(len(self.store.list_steps()[0]["messages"]), 2)

    def test_unlinked_message_never_creates_executable_step(self):
        result = self.store.ingest_message(dict(provider="gmail", account="principal", message_id="unknown", step_key="test-1", kind="test"))
        self.assertTrue(result["link_pending"])
        self.assertEqual(self.store.summary()["unlinked_messages"], 1)
        self.assertEqual(self.store.list_steps(), [])

    def test_message_can_be_linked_later_only_with_evidence(self):
        message = dict(provider="gmail", account="principal", message_id="unlinked", summary="Teste recebido")
        original = self.store.ingest_message(message)
        linked = {**message, "job_id": self.job(), "step_key": "test-1", "kind": "test"}
        with self.assertRaises(ValueError):
            self.store.ingest_message(linked)
        self.assertEqual(self.store.list_steps(), [])
        result = self.store.ingest_message({**linked, "link_evidence": "Portal confirmou empresa e candidatura da mensagem"})
        self.assertEqual(result["id"], original["id"])
        self.assertFalse(result["link_pending"])
        self.assertEqual(self.store.summary()["messages"], 1)
        self.assertEqual(self.store.summary()["pending_steps"], 1)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM message_links").fetchone()[0], 1)
        self.store.ingest_message(linked)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM message_links").fetchone()[0], 1)

    def test_message_cannot_silently_change_step_or_job(self):
        first = self.job()
        message = dict(provider="outlook", account="principal", message_id="linked", job_id=first, step_key="test-1", kind="test")
        self.store.ingest_message(message)
        second = self.job(source_key="other", aliases=["job:gupy:456"])
        with self.assertRaises(ValueError):
            self.store.ingest_message({**message, "job_id": second, "link_evidence": "Outro vínculo"})
        with self.assertRaises(ValueError):
            self.store.ingest_message({**message, "step_key": "test-2", "link_evidence": "Outra etapa"})

    def test_linked_message_updates_verified_deadline_without_duplicates(self):
        message = dict(provider="gmail", account="principal", message_id="deadline",
                       job_id=self.job(), step_key="test-1", kind="test", summary="Teste recebido")
        original = self.store.ingest_message(message)
        self.store.claim_step(original["step_id"], "chat:fixture")
        for due_at, expected in (("2026-09-16T14:00:00-03:00", "2026-09-16T17:00:00Z"),
                                 ("2026-09-17T14:00:00-03:00", "2026-09-17T17:00:00Z")):
            result = self.store.ingest_message({**message, "due_at": due_at})
            self.assertTrue(result["duplicate"])
            self.assertEqual((result["id"], result["step_id"]), (original["id"], original["step_id"]))
            step, = self.store.list_steps()
            self.assertEqual(datetime.fromisoformat(step["due_at"]), datetime.fromisoformat(expected))
            self.assertEqual(step["state"], "in_progress")
            self.assertEqual(step["owner"], "chat:fixture")
        self.store.ingest_message(message)
        self.assertEqual(datetime.fromisoformat(self.store.list_steps()[0]["due_at"]),
                         datetime(2026, 9, 17, 17, tzinfo=timezone.utc))
        self.assertEqual(self.store.summary()["messages"], 1)
        self.assertEqual(self.store.summary()["confirmed"], 0)

    def test_linked_message_rejects_conflicting_kind_and_invalid_deadline(self):
        message = dict(provider="gmail", account="principal", message_id="deadline",
                       job_id=self.job(), step_key="test-1", kind="test")
        self.store.ingest_message(message)
        for change in ({"kind": "interview"}, {"due_at": "2026-09-16T14:00:00"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.store.ingest_message({**message, **change})
        step, = self.store.list_steps()
        self.assertEqual(step["kind"], "test")
        self.assertIsNone(step["due_at"])
        self.assertEqual(self.store.summary()["messages"], 1)

    def test_linked_message_does_not_rewrite_completed_step(self):
        message = dict(provider="gmail", account="principal", message_id="deadline",
                       job_id=self.job(), step_key="test-1", kind="test")
        original = self.store.ingest_message(message)
        self.store.transition_step(original["step_id"], "completed", evidence="Conclusão fictícia conferida")
        before = self.store.list_steps()[0]
        self.store.ingest_message({**message, "due_at": "2026-09-16T14:00:00-03:00"})
        self.assertEqual(self.store.list_steps()[0], before)

    def test_provider_aliases_preserve_compound_public_ids(self):
        self.job(aliases=["job:github:example-org/jobs/1001", "job:inhire:example-company:fixture-uuid"])
        self.assertEqual(len(self.store.list_jobs()[0]["aliases"]), 2)

    def test_public_ids_in_evidence_are_not_phone_numbers(self):
        evidence = "linkedin:1000000001; aplicação 900000001; portal confirmou https://example.com/jobs/1000000002"
        self.job(evidence=evidence)
        self.assertEqual(self.store.list_jobs()[0]["evidence"], evidence)
        with self.assertRaises(ValueError):
            self.job(evidence=evidence + "; contato +55 (00) 90000-0000")

    def test_terminal_step_is_not_reopened_by_reminder(self):
        step = self.step()
        self.store.transition_step(step["id"], "completed", evidence="Portal confirmou conclusão")
        message = dict(provider="gmail", account="principal", message_id="reminder", job_id=step["job_id"], step_key=step["step_key"], kind=step["kind"])
        result = self.store.ingest_message(message)
        self.assertEqual(result["step_id"], step["id"])
        self.assertEqual(self.store.list_steps()[0]["state"], "completed")
        with self.assertRaises(ValueError):
            self.store.transition_step(step["id"], "pending", evidence="Lembrete repetido")

    def test_claim_is_exclusive_across_connections(self):
        step = self.step()
        barrier = threading.Barrier(2)
        outcomes = []

        def reserve(owner):
            connection = Store(self.path)
            try:
                barrier.wait(timeout=5)
                try:
                    connection.claim_step(step["id"], owner)
                    outcomes.append("claimed")
                except ValueError:
                    outcomes.append("rejected")
            finally:
                connection.close()

        threads = [threading.Thread(target=reserve, args=(owner,)) for owner in ("worker-a", "worker-b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertCountEqual(outcomes, ["claimed", "rejected"])

    def test_action_started_requires_active_owner_and_evidence_to_complete(self):
        step_id = self.step()["id"]
        with self.assertRaises(ValueError):
            self.store.transition_step(step_id, "action_started", owner="worker")
        self.store.claim_step(step_id, "worker")
        with self.assertRaises(ValueError):
            self.store.transition_step(step_id, "action_started", owner="other")
        self.store.transition_step(step_id, "action_started", owner="worker")
        with self.assertRaises(ValueError):
            self.store.transition_step(step_id, "completed", owner="worker")
        completed = self.store.transition_step(step_id, "completed", evidence="Destino confirmou a operação", owner="worker")
        self.assertEqual(completed["state"], "completed")
        self.assertIsNone(completed["owner"])

    def test_crash_after_action_never_automatically_retries(self):
        step_id = self.step()["id"]
        self.store.claim_step(step_id, "worker", lease_seconds=1)
        self.store.transition_step(step_id, "action_started", owner="worker")
        result = self.store.recover(datetime.now(timezone.utc) + timedelta(seconds=10))
        self.assertEqual(result["uncertain"], 1)
        self.assertEqual(self.store.list_steps()[0]["state"], "uncertain")
        with self.assertRaises(ValueError):
            self.store.claim_step(step_id, "worker")
        with self.assertRaises(ValueError):
            self.store.transition_step(step_id, "pending", evidence="Timeout local")
        self.store.transition_step(step_id, "pending", evidence="not_received: Lista do portal confirma ausência da operação")
        self.assertEqual(self.store.claim_step(step_id, "new-worker")["state"], "in_progress")

    def test_expired_reservation_requires_session_verification(self):
        step_id = self.step()["id"]
        self.store.claim_step(step_id, "worker", lease_seconds=1)
        result = self.store.recover(datetime.now(timezone.utc) + timedelta(seconds=10))
        self.assertEqual(result["recovered"], 1)
        self.assertEqual(self.store.list_steps()[0]["state"], "blocked")
        with self.assertRaises(ValueError):
            self.store.claim_step(step_id, "new-worker")
        with self.assertRaises(ValueError):
            self.store.transition_step(step_id, "pending")
        self.store.transition_step(step_id, "pending", evidence="Sessão encerrada e formulário sem transmissão")
        self.store.claim_step(step_id, "new-worker")

    def test_due_dates_require_timezone_and_sort_chronologically(self):
        with self.assertRaises(ValueError):
            self.step(due_at="2026-09-15T14:00:00")
        first = self.step(step_key="first", due_at="2026-09-15T14:00:00-03:00")
        second = self.step(step_key="second", due_at="2026-09-15T18:00:00+02:00")
        self.assertEqual([row["id"] for row in self.store.list_steps()], [second["id"], first["id"]])

    def test_sensitive_data_is_rejected(self):
        for changes in ({"evidence": "Contato pessoa@example.com"}, {"notes": ["token=segredo"]}, {"evidence": "Número 123.456.789-00"}, {"notes": ["Contato +55 (00) 90000-0000"]}, {"aliases": ["url:https://example.com/job?access_token=segredo"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.job(**changes)
        for safe_url in ("http://example.com/job", "https://user:pass@example.com/job", "https://example.com/job#secret", "https://example.com/job?session_id=abc"):
            with self.subTest(safe_url=safe_url), self.assertRaises(ValueError):
                self.step(safe_url=safe_url)
        with self.assertRaises(ValueError):
            self.store.ingest_message(dict(provider="gmail", account="pessoa@example.com", message_id="123"))

    def test_invalid_ids_and_periods_fail_explicitly(self):
        with self.assertRaises(ValueError):
            self.store.claim_step(999, "worker")
        with self.assertRaises(ValueError):
            self.store.summary("2026-09-20", "2026-09-10")
        with self.assertRaises(ValueError):
            self.job(eligible="true")
        with self.assertRaises(ValueError):
            self.job(confirmed_at="20260910")


if __name__ == "__main__":
    unittest.main()
