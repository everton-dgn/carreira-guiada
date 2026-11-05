"""Email coverage checkpoints and expiring ownership for the active chat agent."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


def utcnow():
    return datetime.now(timezone.utc)


def stamp(value=None):
    return (value or utcnow()).isoformat(timespec="seconds")


class Monitor:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS monitor_runs (
            id TEXT PRIMARY KEY, started_at TEXT NOT NULL, expires_at TEXT NOT NULL,
            finished_at TEXT, status TEXT NOT NULL, note TEXT NOT NULL DEFAULT ''
          );
          CREATE TABLE IF NOT EXISTS monitor_accounts (
            provider TEXT NOT NULL, account TEXT NOT NULL, status TEXT NOT NULL,
            checked_at TEXT, covered_until TEXT, window_start TEXT, window_end TEXT,
            failures INTEGER NOT NULL DEFAULT 0, retry_after TEXT, note TEXT NOT NULL,
            run_id TEXT, PRIMARY KEY(provider, account)
          );
        """)

    @classmethod
    def readonly(cls, path):
        """Open existing checkpoints for status() only; None when nothing was recorded.

        Never creates the database file or tables (Monitor(path) would create
        the file with default permissions).
        """
        path = Path(path).expanduser().absolute()
        if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
            return None
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10, isolation_level=None)
        try:
            db.row_factory = sqlite3.Row
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except BaseException:
            db.close()
            raise
        if not {"monitor_runs", "monitor_accounts"} <= names:
            db.close()
            return None
        monitor = cls.__new__(cls)
        monitor.db = db
        return monitor

    def begin(self, minutes=30):
        if not 1 <= minutes <= 120:
            raise ValueError("A duração deve estar entre 1 e 120 minutos.")
        now = utcnow()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            active = self.db.execute(
                "SELECT * FROM monitor_runs WHERE status='running' AND expires_at>?",
                (stamp(now),),
            ).fetchone()
            if active:
                self.db.execute("COMMIT")
                return {"acquired": False, "run_id": active["id"], "expires_at": active["expires_at"]}
            self.db.execute(
                "UPDATE monitor_runs SET status='interrupted', finished_at=? "
                "WHERE status='running' AND expires_at<=?", (stamp(now), stamp(now)),
            )
            run_id = uuid4().hex
            self.db.execute("INSERT INTO monitor_runs VALUES(?,?,?,?,?,?)", (
                run_id, stamp(now), stamp(now + timedelta(minutes=minutes)), None, "running", "",
            ))
            self.db.execute("COMMIT")
            return {"acquired": True, "run_id": run_id, "expires_at": stamp(now + timedelta(minutes=minutes))}
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def _active(self, run_id):
        row = self.db.execute("SELECT * FROM monitor_runs WHERE id=?", (run_id,)).fetchone()
        if not row or row["status"] != "running" or row["expires_at"] <= stamp():
            raise ValueError("Rodada ausente, encerrada ou com prazo de execução vencido.")

    def account(self, run_id, provider, account, status, note="", window_start=None, window_end=None, query="recruitment-v1"):
        if provider not in {"gmail", "outlook"}:
            raise ValueError("Provedor inválido.")
        if not account or len(account) > 80 or not all(c.isalnum() or c in "_-" for c in account):
            raise ValueError("Use um alias local de conta, sem endereço de e-mail.")
        if status not in {"complete", "partial", "auth_required", "unavailable"}:
            raise ValueError("Estado de cobertura inválido.")
        if query != "recruitment-v1":
            raise ValueError("Use a consulta fixa recruitment-v1; buscas por empresa são cobertura parcial.")
        if len(note) > 300 or "@" in note or "http" in note.lower():
            raise ValueError("Use nota curta, sem endereços ou links.")
        start = end = None
        if window_start or window_end:
            if not window_start or not window_end:
                raise ValueError("Informe início e fim da janela.")
            try:
                start, end = (datetime.fromisoformat(v) for v in (window_start, window_end))
            except (ValueError, TypeError):
                raise ValueError("Datas da janela precisam usar ISO com fuso.") from None
            if start.tzinfo is None or end.tzinfo is None or start >= end or end > utcnow():
                raise ValueError("A janela precisa ter fuso, ordem válida e fim não futuro.")
            window_start, window_end = stamp(start.astimezone(timezone.utc)), stamp(end.astimezone(timezone.utc))
        if status == "complete" and (start is None or note != "recruitment-v1: todas as páginas conferidas"):
            raise ValueError("Cobertura completa exige janela e nota da consulta fixa com todas as páginas conferidas.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._active(run_id)
            old = self.db.execute("SELECT * FROM monitor_accounts WHERE provider=? AND account=?", (provider, account)).fetchone()
            covered = old["covered_until"] if old else None
            if status == "complete":
                if covered and window_start > covered:
                    raise ValueError("A janela deixa uma lacuna após a última cobertura completa.")
                covered = max(covered or window_end, window_end)
            failures = ((old["failures"] if old else 0) + 1) if status in {"auth_required", "unavailable"} else 0
            delay = min(24, 2 ** min(failures, 5)) if failures else 0
            retry = stamp(utcnow() + timedelta(hours=delay)) if delay else None
            self.db.execute("""INSERT INTO monitor_accounts VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(provider,account) DO UPDATE SET status=excluded.status,
                checked_at=excluded.checked_at, covered_until=excluded.covered_until,
                window_start=excluded.window_start, window_end=excluded.window_end,
                failures=excluded.failures,retry_after=excluded.retry_after,note=excluded.note,run_id=excluded.run_id""",
                (provider, account, status, stamp(), covered, window_start, window_end, failures, retry, note, run_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return self.status()

    def finish(self, run_id, note=""):
        if len(note) > 300 or "@" in note or "http" in note.lower():
            raise ValueError("Use nota curta sem dados pessoais.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._active(run_id)
            self.db.execute("UPDATE monitor_runs SET status='finished',finished_at=?,note=? WHERE id=?", (stamp(), note, run_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return {"run_id": run_id, "status": "finished"}

    def status(self):
        accounts = [dict(r) for r in self.db.execute("SELECT * FROM monitor_accounts ORDER BY provider,account")]
        runs = [dict(r) for r in self.db.execute("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 5")]
        for row in accounts:
            row["due"] = not row["retry_after"] or row["retry_after"] <= stamp()
        for row in runs:
            if row["status"] == "running" and row["expires_at"] <= stamp():
                row["status"] = "expired"
        return {"accounts": accounts, "runs": runs}
