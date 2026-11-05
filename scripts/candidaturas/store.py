"""Private, transactional ledger for applications and follow-up actions.

The ledger deliberately has no network operations. The active chat agent must
persist ``action_started`` before acting and provide destination evidence after
the action. A lease expiry cannot make an uncertain action safe to repeat.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import unicodedata
from urllib.parse import parse_qsl, urlsplit


JOB_STATES = {"confirmed", "discovered", "pending_verification", "candidate_pending", "blocked", "discarded"}
STEP_STATES = {"pending", "in_progress", "action_started", "uncertain", "candidate_pending", "blocked", "completed", "cancelled"}
TERMINAL_STATES = {"completed", "cancelled"}
_SECRET = re.compile(r"(?i)\b(?:bearer\s+\S+|(?:password|senha|token|cookie|secret|cpf|rg)\s*[:=]\s*\S+)")
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_SENSITIVE_QUERY = re.compile(r"(?i)(token|secret|password|senha|auth|session|code|signature|credential|key)")
_PERSONAL_NUMBER = re.compile(r"(?<!\w)(?:\+?55[ .()-]*)?(?:\(?\d{2}\)?[ .-]*)?\d{4,5}[ .-]?\d{4}(?!\w)|(?<!\w)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\w)")
_IDENTIFIER_FIELDS = {"alias", "source", "source_key", "message_id", "step_key", "safe_url"}
_NAMESPACED_ID = re.compile(r"\b(?:(?:job|application):[a-z0-9_-]+|linkedin|gupy|solides|indeed|inhire|github|greenhouse|lever|catho|infojobs|quickin|peixe30|pandape|orbite|programathor|netvagas|remotive|remotar):[A-Za-z0-9._~:/-]+", re.IGNORECASE)
_APPLICATION_ID = re.compile(r"\b(?:(?:aplica[çc][ãa]o|candidatura)\s+(?:ID\s*[:=]?\s*)?|application_id\s*[:=]?\s*)\d+\b", re.IGNORECASE)


def _text(value, field, *, optional=False, limit=2000):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field}: texto obrigatório, limitado a {limit} caracteres")
    value = value.strip()
    if _SECRET.search(value) or _EMAIL.search(value) or "\x00" in value:
        raise ValueError(f"{field}: use resumo sem dados pessoais ou credenciais")
    if field not in _IDENTIFIER_FIELDS:
        candidate = value
        for url in re.findall(r"https://[^\s<>]+", value):
            public = url.rstrip(".,;)]")
            _public_url(public)
            candidate = candidate.replace(public, " ")
        candidate = _NAMESPACED_ID.sub(" ", candidate)
        candidate = _APPLICATION_ID.sub(" ", candidate)
        if _PERSONAL_NUMBER.search(candidate):
            raise ValueError(f"{field}: não registre telefone ou número de documento em texto livre")
    return value


def _public_url(value):
    if value is None:
        return None
    value = _text(value, "safe_url", limit=2000)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("safe_url: use URL pública HTTPS sem credenciais ou fragmento")
    if any(_SENSITIVE_QUERY.search(key) for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
        raise ValueError("safe_url: parâmetros de acesso não podem ser persistidos")
    return value


def _day(value, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field}: informe data ISO YYYY-MM-DD")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}: informe data ISO YYYY-MM-DD") from exc
    if value != result.isoformat():
        raise ValueError(f"{field}: informe data ISO YYYY-MM-DD")
    return value


def _instant(value=None, field="now"):
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field}: informe data e hora ISO com fuso") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field}: informe data e hora ISO com fuso")
    return value.astimezone(timezone.utc)


def _stamp(value=None):
    return _instant(value).isoformat(timespec="microseconds")


def _same(left, right):
    return " ".join(unicodedata.normalize("NFKC", left).casefold().split()) == " ".join(unicodedata.normalize("NFKC", right).casefold().split())


def _alias(value):
    value = _text(value, "alias", limit=2000)
    if value.startswith("url:"):
        _public_url(value[4:])
    elif not re.fullmatch(r"(?:job|application):[a-z0-9_-]+:[A-Za-z0-9._~:/-]+", value):
        raise ValueError("alias: use job:portal:id, application:portal:id ou url:https://...")
    return value


def _record(payload):
    if not isinstance(payload, dict):
        raise ValueError("record: objeto obrigatório")
    result = {name: _text(payload.get(name), name, limit=500) for name in ("source_key", "company", "title", "portal")}
    result["state"] = payload.get("state", "discovered")
    if result["state"] not in JOB_STATES:
        raise ValueError("state: estado de candidatura inválido")
    result["confirmed_at"] = _day(payload.get("confirmed_at"), "confirmed_at")
    result["evidence"] = _text(payload.get("evidence"), "evidence", optional=True)
    if result["state"] == "confirmed" and not result["evidence"]:
        raise ValueError("evidence: confirmação exige evidência")
    result["eligible"] = payload.get("eligible")
    if result["eligible"] is not None and type(result["eligible"]) is not bool:
        raise ValueError("eligible: use true, false ou null")
    result["identity_verified"] = payload.get("identity_verified", False)
    if type(result["identity_verified"]) is not bool:
        raise ValueError("identity_verified: booleano obrigatório")
    aliases = payload.get("aliases", [])
    if not isinstance(aliases, list):
        raise ValueError("aliases: lista obrigatória")
    result["aliases"] = sorted(set(_alias(alias) for alias in aliases))
    # A candidature identifier does not establish the identity of the vacancy.
    result["identity_verified"] = result["identity_verified"] and any(alias.startswith(("job:", "url:")) for alias in result["aliases"])
    notes = payload.get("notes", [])
    if not isinstance(notes, list):
        raise ValueError("notes: lista obrigatória")
    result["notes"] = [_text(note, "notes") for note in notes]
    return result


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    company TEXT NOT NULL, title TEXT NOT NULL, portal TEXT NOT NULL,
    state TEXT NOT NULL, confirmed_at TEXT, evidence TEXT,
    eligible INTEGER, identity_verified INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aliases (
    alias TEXT PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id)
);
CREATE TABLE IF NOT EXISTS imports (
    source TEXT NOT NULL, source_key TEXT NOT NULL,
    job_id INTEGER NOT NULL REFERENCES jobs(id), payload TEXT NOT NULL,
    PRIMARY KEY (source, source_key)
);
CREATE TABLE IF NOT EXISTS source_snapshots (
    source TEXT PRIMARY KEY, active_keys TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS identity_conflicts (
    id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id),
    source TEXT NOT NULL, source_key TEXT NOT NULL, detail TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (job_id, source, source_key, detail)
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id),
    step_key TEXT NOT NULL, kind TEXT NOT NULL, summary TEXT,
    due_at TEXT, safe_url TEXT, state TEXT NOT NULL, reason TEXT,
    owner TEXT, lease_until TEXT, evidence TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE (job_id, step_key)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY, provider TEXT NOT NULL, account TEXT NOT NULL,
    message_id TEXT NOT NULL, job_id INTEGER REFERENCES jobs(id),
    step_id INTEGER REFERENCES steps(id), summary TEXT, safe_url TEXT,
    received_at TEXT NOT NULL,
    UNIQUE (provider, account, message_id)
);
CREATE TABLE IF NOT EXISTS message_links (
    id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL REFERENCES messages(id),
    job_id INTEGER NOT NULL REFERENCES jobs(id), step_id INTEGER REFERENCES steps(id),
    evidence TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY, step_id INTEGER NOT NULL REFERENCES steps(id),
    old_state TEXT, new_state TEXT NOT NULL, evidence TEXT, owner TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS steps_queue ON steps(state, due_at, created_at);
"""


class Store:
    """One SQLite connection; use a separate Store for each concurrent worker."""

    def __init__(self, path):
        self.path = Path(path).expanduser().absolute()
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("path: links simbólicos não são aceitos para o registro privado")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        self.conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self.conn.execute("PRAGMA journal_mode = WAL")
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.conn.close()
            raise ValueError("schema: versão de registro não suportada")
        self.conn.executescript("BEGIN IMMEDIATE;\n" + _SCHEMA + "\nPRAGMA user_version = 1;\nCOMMIT;")

    @classmethod
    def open_readonly(cls, path):
        """Open an existing ledger for queries only; return None when it is absent.

        Never creates directories, files or schema, so read-only commands on a
        new installation report an empty state. Mutating methods fail with a
        SQLite read-only error on the returned instance.
        """
        path = Path(path).expanduser().absolute()
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("path: links simbólicos não são aceitos para o registro privado")
        if not path.is_file():
            return None
        conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 5000")
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone() is None:
                conn.close()
                return None
        except BaseException:
            conn.close()
            raise
        store = cls.__new__(cls)
        store.path = path
        store.conn = conn
        return store

    def close(self):
        self.conn.close()

    def transaction(self):
        """Public transaction; nested use becomes a savepoint of the outer one."""
        return self._transaction()

    @contextmanager
    def _transaction(self):
        if self.conn.in_transaction:
            # A caller such as the workflow layer owns the outer transaction:
            # keep its commit atomic and roll back only this part on failure.
            self.conn.execute("SAVEPOINT store_nested")
            try:
                yield
            except BaseException:
                self.conn.execute("ROLLBACK TO store_nested")
                self.conn.execute("RELEASE store_nested")
                raise
            else:
                self.conn.execute("RELEASE store_nested")
            return
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    def _job(self, job_id):
        if type(job_id) is not int or job_id < 1:
            raise ValueError("job_id: inteiro positivo obrigatório")
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise ValueError("job_id: oportunidade não encontrada")
        return row

    def _step(self, step_id):
        if type(step_id) is not int or step_id < 1:
            raise ValueError("step_id: inteiro positivo obrigatório")
        row = self.conn.execute("SELECT * FROM steps WHERE id = ?", (step_id,)).fetchone()
        if row is None:
            raise ValueError("step_id: etapa não encontrada")
        return row

    def import_records(self, records, source):
        """Import an incremental batch without withdrawing other source records."""
        return self._import_records(records, source)

    def import_snapshot(self, records, source):
        """Atomically publish a complete source snapshot; retain absent evidence."""
        return self._import_records(records, source, snapshot=True)

    def _import_records(self, records, source, *, snapshot=False):
        source = _text(source, "source", limit=500)
        if not isinstance(records, list):
            raise ValueError("records: lista obrigatória")
        records = [_record(record) for record in records]
        keys = {record["source_key"] for record in records}
        if len(keys) != len(records):
            raise ValueError("source_key: cada chave deve aparecer uma única vez no lote")
        counts = {"created": 0, "updated": 0, "unchanged": 0, "conflicts": 0, "job_ids": []}
        with self._transaction():
            for record in records:
                encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)
                previous = self.conn.execute("SELECT * FROM imports WHERE source = ? AND source_key = ?", (source, record["source_key"])).fetchone()
                if previous and previous["payload"] == encoded:
                    counts["unchanged"] += 1
                    counts["job_ids"].append(previous["job_id"])
                    continue
                matched_ids = set()
                matched_opportunities = set()
                for alias in record["aliases"]:
                    match = self.conn.execute("SELECT job_id FROM aliases WHERE alias = ?", (alias,)).fetchone()
                    if match:
                        matched_ids.add(match["job_id"])
                        if alias.startswith(("job:", "url:")):
                            matched_opportunities.add(match["job_id"])
                conflicts = []
                job = self._job(previous["job_id"]) if previous else None
                if job is None and len(matched_ids) == 1:
                    candidate = self._job(next(iter(matched_ids)))
                    if candidate["id"] in matched_opportunities and record["identity_verified"] and candidate["identity_verified"] and _same(candidate["company"], record["company"]) and _same(candidate["title"], record["title"]):
                        job = candidate
                    else:
                        conflicts.append("Alias existente sem identidade compatível e verificada")
                elif job is None and len(matched_ids) > 1:
                    conflicts.append("Aliases apontam para oportunidades distintas")
                if job and (not _same(job["company"], record["company"]) or not _same(job["title"], record["title"])):
                    conflicts.append("Empresa ou cargo contradiz a identidade registrada")
                if job and matched_ids - {job["id"]}:
                    conflicts.append("Alias pertence a outra oportunidade")
                now = _stamp()
                if job is None:
                    cursor = self.conn.execute("INSERT INTO jobs(company,title,portal,state,confirmed_at,evidence,eligible,identity_verified,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (record["company"], record["title"], record["portal"], record["state"], record["confirmed_at"], record["evidence"], record["eligible"], record["identity_verified"] and not conflicts, json.dumps(record["notes"], ensure_ascii=False), now, now))
                    job = self._job(cursor.lastrowid)
                    counts["created"] += 1
                else:
                    # Confirmation and its historical date survive reimport of an old pending row.
                    state = job["state"] if conflicts else "confirmed" if job["state"] == "confirmed" else record["state"]
                    confirmed_at = job["confirmed_at"] if job["state"] == "confirmed" else record["confirmed_at"]
                    evidence = job["evidence"] if job["state"] == "confirmed" else record["evidence"]
                    if state == "confirmed" and confirmed_at is None and record["state"] == "confirmed":
                        confirmed_at = record["confirmed_at"]
                    eligible = record["eligible"] if record["eligible"] is not None else job["eligible"]
                    notes = list(dict.fromkeys(json.loads(job["notes"]) + record["notes"]))
                    if conflicts:
                        confirmed_at, evidence, eligible, notes = job["confirmed_at"], job["evidence"], job["eligible"], json.loads(job["notes"])
                    self.conn.execute("UPDATE jobs SET state=?,confirmed_at=?,evidence=?,eligible=?,identity_verified=?,notes=?,updated_at=? WHERE id=?", (state, confirmed_at, evidence, eligible, record["identity_verified"] and not conflicts, json.dumps(notes, ensure_ascii=False), now, job["id"]))
                    counts["updated"] += 1
                if conflicts:
                    # Keep both pieces of evidence; count neither side as verified until reconciled.
                    for conflict_id in matched_ids | {job["id"]}:
                        self.conn.execute("UPDATE jobs SET identity_verified=0 WHERE id=?", (conflict_id,))
                        for detail in conflicts:
                            self.conn.execute("INSERT OR IGNORE INTO identity_conflicts(job_id,source,source_key,detail,created_at) VALUES(?,?,?,?,?)", (conflict_id, source, record["source_key"], detail, now))
                    counts["conflicts"] += 1
                else:
                    for alias in record["aliases"]:
                        self.conn.execute("INSERT OR IGNORE INTO aliases(alias,job_id) VALUES(?,?)", (alias, job["id"]))
                self.conn.execute("INSERT INTO imports(source,source_key,job_id,payload) VALUES(?,?,?,?) ON CONFLICT(source,source_key) DO UPDATE SET payload=excluded.payload", (source, record["source_key"], job["id"], encoded))
                counts["job_ids"].append(job["id"])
            previous_snapshot = self.conn.execute("SELECT active_keys FROM source_snapshots WHERE source=?", (source,)).fetchone()
            if snapshot or previous_snapshot:
                active_keys = keys if snapshot else keys | set(json.loads(previous_snapshot["active_keys"]))
                encoded_keys = json.dumps(sorted(active_keys), ensure_ascii=False)
                if previous_snapshot is None or previous_snapshot["active_keys"] != encoded_keys:
                    self.conn.execute("INSERT INTO source_snapshots(source,active_keys,updated_at) VALUES(?,?,?) ON CONFLICT(source) DO UPDATE SET active_keys=excluded.active_keys,updated_at=excluded.updated_at", (source, encoded_keys, _stamp()))
        return counts

    def list_jobs(self):
        result = []
        snapshots = {row["source"]: set(json.loads(row["active_keys"])) for row in self.conn.execute("SELECT source,active_keys FROM source_snapshots")}
        for row in self.conn.execute("SELECT * FROM jobs ORDER BY id"):
            job = dict(row)
            job["eligible"] = None if job["eligible"] is None else bool(job["eligible"])
            job["identity_verified"] = bool(job["identity_verified"])
            job["notes"] = json.loads(job["notes"])
            job["aliases"] = [alias[0] for alias in self.conn.execute("SELECT alias FROM aliases WHERE job_id=? ORDER BY alias", (job["id"],))]
            job["conflicts"] = [dict(conflict) for conflict in self.conn.execute("SELECT source,source_key,detail FROM identity_conflicts WHERE job_id=? ORDER BY id", (job["id"],))]
            job["sources"] = [dict(source) for source in self.conn.execute("SELECT source,source_key FROM imports WHERE job_id=? ORDER BY source,source_key", (job["id"],))]
            for source in job["sources"]:
                source["active"] = source["source"] not in snapshots or source["source_key"] in snapshots[source["source"]]
            job["active"] = any(source["active"] for source in job["sources"])
            result.append(job)
        return result

    def summary(self, since=None, until=None):
        since, until = _day(since, "since"), _day(until, "until")
        if since and until and since > until:
            raise ValueError("period: since deve ser anterior ou igual a until")
        all_jobs = self.list_jobs()
        jobs = [job for job in all_jobs if job["active"]]
        steps = self.list_steps()
        identified = [job for job in jobs if job["identity_verified"] and not job["conflicts"]]
        historical_confirmed = [job for job in jobs if job["state"] == "confirmed"]
        confirmed = [job for job in identified if job["state"] == "confirmed"]
        verified = [job for job in confirmed if job["eligible"] is True]
        active_steps = [step for step in steps if step["state"] not in TERMINAL_STATES]
        pending = {job["id"] for job in jobs if job["state"] not in {"confirmed", "discarded"}} | {step["job_id"] for step in active_steps}
        return {
            "opportunities": len(identified), "confirmed": len(confirmed), "eligible_confirmed": len(verified),
            "record_count": len(all_jobs), "active_record_count": len(jobs), "inactive_records": len(all_jobs) - len(jobs),
            "historical_confirmed_records": len(historical_confirmed),
            "compatible_unknown": sum(job["eligible"] is None for job in confirmed),
            "period_confirmed": sum(bool(job["confirmed_at"]) and (since is None or job["confirmed_at"] >= since) and (until is None or job["confirmed_at"] <= until) for job in verified),
            "uncertain": sum(job["state"] == "pending_verification" for job in jobs),
            "pending_jobs": len(pending), "pending_steps": len(active_steps),
            "discarded": sum(job["state"] == "discarded" for job in jobs),
            "confirmed_without_date": sum(job["confirmed_at"] is None for job in historical_confirmed),
            "identity_unverified": sum(not job["identity_verified"] or bool(job["conflicts"]) for job in jobs),
            "identity_conflicts": sum(bool(job["conflicts"]) for job in jobs),
            "unlinked_messages": self.conn.execute("SELECT COUNT(*) FROM messages WHERE job_id IS NULL").fetchone()[0],
            "messages": self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
            "since": since, "until": until,
            "scope": "Registros importados e evidências locais; não representa todas as candidaturas existentes nos portais.",
        }

    def _validated_step(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("step: objeto obrigatório")
        job_id = payload.get("job_id")
        self._job(job_id)
        result = {"job_id": job_id, "step_key": _text(payload.get("step_key"), "step_key", limit=500), "kind": _text(payload.get("kind"), "kind", limit=100)}
        for field in ("summary", "reason"):
            result[field] = _text(payload.get(field), field, optional=True)
        result["safe_url"] = _public_url(payload.get("safe_url"))
        result["due_at"] = _stamp(_instant(payload["due_at"], "due_at")) if payload.get("due_at") is not None else None
        result["state"] = payload.get("state", "pending")
        if result["state"] not in {"pending", "blocked", "candidate_pending"}:
            raise ValueError("state: uma nova etapa começa pending, blocked ou candidate_pending")
        return result

    def _upsert_step(self, payload):
        record = self._validated_step(payload)
        existing = self.conn.execute("SELECT * FROM steps WHERE job_id=? AND step_key=?", (record["job_id"], record["step_key"])).fetchone()
        now = _stamp()
        if existing:
            if existing["kind"] != record["kind"]:
                raise ValueError("step_key: tipo contradiz a etapa existente")
            if existing["state"] not in TERMINAL_STATES:
                self.conn.execute("UPDATE steps SET summary=COALESCE(?,summary),due_at=COALESCE(?,due_at),safe_url=COALESCE(?,safe_url),reason=COALESCE(?,reason),updated_at=? WHERE id=?", (record["summary"], record["due_at"], record["safe_url"], record["reason"], now, existing["id"]))
            return dict(self._step(existing["id"]))
        cursor = self.conn.execute("INSERT INTO steps(job_id,step_key,kind,summary,due_at,safe_url,state,reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (record["job_id"], record["step_key"], record["kind"], record["summary"], record["due_at"], record["safe_url"], record["state"], record["reason"], now, now))
        self._event(cursor.lastrowid, None, record["state"], None, None, now)
        return dict(self._step(cursor.lastrowid))

    def upsert_step(self, payload):
        with self._transaction():
            return self._upsert_step(payload)

    def ingest_message(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("message: objeto obrigatório")
        provider = payload.get("provider")
        if provider not in {"gmail", "outlook"}:
            raise ValueError("provider: use gmail ou outlook")
        account = _text(payload.get("account"), "account", limit=100)
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", account):
            raise ValueError("account: use um alias local sem endereço de e-mail")
        message_id = _text(payload.get("message_id"), "message_id", limit=500)
        summary = _text(payload.get("summary"), "summary", optional=True)
        safe_url = _public_url(payload.get("safe_url"))
        link_evidence = _text(payload.get("link_evidence"), "link_evidence", optional=True)
        with self._transaction():
            existing = self.conn.execute("SELECT * FROM messages WHERE provider=? AND account=? AND message_id=?", (provider, account, message_id)).fetchone()
            if existing:
                job_id = payload.get("job_id", existing["job_id"])
                if job_id is None:
                    job_id = existing["job_id"]
                if existing["job_id"] is not None and existing["job_id"] != job_id:
                    raise ValueError("message_id: mensagem já registrada com outro vínculo")
                if existing["step_id"] is not None and payload.get("step_key") is not None:
                    if self._step(existing["step_id"])["step_key"] != payload["step_key"]:
                        raise ValueError("message_id: mensagem já registrada com outra etapa")
                new_link = job_id is not None and (existing["job_id"] is None or (existing["step_id"] is None and payload.get("step_key") is not None))
                if new_link:
                    if not link_evidence:
                        raise ValueError("link_evidence: associação posterior exige prova do vínculo")
                    self._job(job_id)
                    step_id = self._upsert_step({**payload, "job_id": job_id})["id"] if payload.get("step_key") is not None else None
                    self.conn.execute("UPDATE messages SET job_id=?,step_id=? WHERE id=?", (job_id, step_id, existing["id"]))
                    self.conn.execute("INSERT INTO message_links(message_id,job_id,step_id,evidence,created_at) VALUES(?,?,?,?,?)", (existing["id"], job_id, step_id, link_evidence, _stamp()))
                    existing = self.conn.execute("SELECT * FROM messages WHERE id=?", (existing["id"],)).fetchone()
                return {**dict(existing), "duplicate": True, "link_pending": existing["job_id"] is None}
            job_id = payload.get("job_id")
            if job_id is not None:
                self._job(job_id)
            step_id = None
            if job_id is not None and payload.get("step_key") is not None:
                step_id = self._upsert_step(payload)["id"]
            cursor = self.conn.execute("INSERT INTO messages(provider,account,message_id,job_id,step_id,summary,safe_url,received_at) VALUES(?,?,?,?,?,?,?,?)", (provider, account, message_id, job_id, step_id, summary, safe_url, _stamp()))
            return {**dict(self.conn.execute("SELECT * FROM messages WHERE id=?", (cursor.lastrowid,)).fetchone()), "duplicate": False, "link_pending": job_id is None}

    def list_steps(self):
        result = []
        now = _stamp()
        for row in self.conn.execute("SELECT steps.*,jobs.company,jobs.title FROM steps JOIN jobs ON jobs.id=steps.job_id ORDER BY due_at IS NULL,due_at,steps.created_at,steps.id"):
            step = dict(row)
            step["overdue"] = bool(step["due_at"] and step["due_at"] < now and step["state"] not in TERMINAL_STATES)
            step["messages"] = [dict(message) for message in self.conn.execute("SELECT provider,account,message_id FROM messages WHERE step_id=? ORDER BY id", (step["id"],))]
            result.append(step)
        return result

    def _event(self, step_id, old_state, new_state, evidence, owner, now):
        self.conn.execute("INSERT INTO events(step_id,old_state,new_state,evidence,owner,created_at) VALUES(?,?,?,?,?,?)", (step_id, old_state, new_state, evidence, owner, now))

    def claim_step(self, step_id, owner, lease_seconds=300):
        owner = _text(owner, "owner", limit=100)
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds: inteiro entre 1 e 3600")
        with self._transaction():
            step = self._step(step_id)
            now = _instant()
            stamp = _stamp(now)
            if step["state"] not in {"pending", "in_progress"}:
                raise ValueError("state: etapa não está disponível para execução")
            if step["owner"] and step["owner"] != owner:
                # Expiry proves no liveness; require explicit recovery before transfer.
                raise ValueError("owner: etapa reservada; confira e recupere a reserva antes da transferência")
            self.conn.execute("UPDATE steps SET state='in_progress',owner=?,lease_until=?,updated_at=? WHERE id=?", (owner, _stamp(now + timedelta(seconds=lease_seconds)), stamp, step_id))
            self._event(step_id, step["state"], "in_progress", None, owner, stamp)
            return dict(self._step(step_id))

    def transition_step(self, step_id, state, evidence=None, owner=None):
        if state not in STEP_STATES:
            raise ValueError("state: estado de etapa inválido")
        evidence = _text(evidence, "evidence", optional=True)
        owner = _text(owner, "owner", optional=True, limit=100)
        with self._transaction():
            step = self._step(step_id)
            old = step["state"]
            if old == state:
                return dict(step)
            if old in TERMINAL_STATES:
                raise ValueError("state: etapa encerrada não pode ser reaberta")
            now = _stamp()
            if step["owner"] and owner != step["owner"]:
                raise ValueError("owner: somente o responsável pode alterar uma etapa reservada")
            if state == "in_progress":
                raise ValueError("state: use claim_step para iniciar uma etapa")
            allowed = {
                "pending": {"candidate_pending", "blocked", "completed", "cancelled"},
                "in_progress": {"pending", "action_started", "candidate_pending", "blocked", "completed", "cancelled"},
                "action_started": {"uncertain", "completed"},
                "uncertain": {"pending", "completed"},
                "candidate_pending": {"pending", "blocked", "completed", "cancelled"},
                "blocked": {"pending", "candidate_pending", "completed", "cancelled"},
            }
            if state not in allowed[old]:
                raise ValueError("state: transição não permitida")
            if state == "action_started":
                if not owner or owner != step["owner"] or not step["lease_until"] or step["lease_until"] <= now:
                    raise ValueError("owner: action_started exige reserva ativa do responsável")
            if state in TERMINAL_STATES and not evidence:
                raise ValueError("evidence: encerramento exige confirmação ou motivo comprovado")
            if old == "uncertain" and state == "pending" and (not evidence or not evidence.startswith("not_received:") or not evidence.removeprefix("not_received:").strip()):
                raise ValueError("evidence: repetição exige 'not_received: <prova de que o destino não recebeu>'")
            if old in {"blocked", "candidate_pending"} and state == "pending" and not evidence:
                raise ValueError("evidence: retomada exige evidência de mudança")
            keep_owner = state == "action_started"
            self.conn.execute("UPDATE steps SET state=?,evidence=COALESCE(?,evidence),owner=?,lease_until=?,updated_at=? WHERE id=?", (state, evidence, step["owner"] if keep_owner else None, step["lease_until"] if keep_owner else None, now, step_id))
            self._event(step_id, old, state, evidence, owner, now)
            return dict(self._step(step_id))

    def recover(self, now=None):
        stamp = _stamp(now)
        result = {"recovered": 0, "uncertain": 0, "step_ids": []}
        with self._transaction():
            stale = self.conn.execute("SELECT * FROM steps WHERE state IN ('in_progress','action_started') AND lease_until <= ?", (stamp,)).fetchall()
            for step in stale:
                # A lease expiration cannot prove that a session died or nothing was sent.
                state = "uncertain" if step["state"] == "action_started" else "blocked"
                reason = "resultado_a_verificar" if state == "uncertain" else "reserva_expirada_verificar_sessao"
                evidence = "Prazo da reserva expirou; conferir o destino e a sessão antes de retomar."
                self.conn.execute("UPDATE steps SET state=?,reason=?,evidence=?,owner=NULL,lease_until=NULL,updated_at=? WHERE id=?", (state, reason, evidence, stamp, step["id"]))
                self._event(step["id"], step["state"], state, evidence, step["owner"], stamp)
                result["uncertain" if state == "uncertain" else "recovered"] += 1
                result["step_ids"].append(step["id"])
        return result
