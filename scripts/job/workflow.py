"""Operação do Carreira Guiada: objetivo, oportunidades, autorizações, resultados, parada e e-mails.

Tudo fica em ``.job/control.sqlite3`` (o banco do ``Store`` herdado). ``state()``
nunca cria ``.job``. Mutações usam uma transação; o ``Store`` aninha a dele em
savepoint, então oportunidade, etapa e ação são gravadas juntas ou nada é gravado.

Ciclo de uma ação externa
1. ``state()["control"]["generation"]`` informa a geração vigente.
2. ``authorize(payload)`` confere parada, geração, owner, objetivo, perfil aprovado,
   permissão, capacidade observada, elegibilidade, currículo aprovado com hash e
   duplicatas; só então grava a intenção ``authorized`` com prazo. Nada é executado.
3. O agente executa a ação no destino com as ferramentas autenticadas do ambiente.
4. ``complete(action_id, payload)`` registra ``confirmed`` ou ``not_received`` (ambos
   exigem conferência no destino) ou ``uncertain``.

Estados: authorized -> confirmed | uncertain | not_received; uncertain -> confirmed |
not_received. Ação ``authorized`` cujo prazo vence, aberta durante ``stop()`` ou cuja
capacidade foi revogada vira ``uncertain``. Incerteza bloqueia nova autorização da
mesma chave até haver evidência do destino. ``resume()`` cria geração nova; owners
de gerações anteriores são rejeitados.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import hashlib
from pathlib import Path
import re
import secrets
from string import ascii_lowercase

from scripts.candidaturas.monitor import Monitor
from scripts.candidaturas.store import Store, TERMINAL_STATES, _EMAIL, _SECRET, _instant, _public_url, _stamp, _text

ACTIONS = ("research", "register", "fill", "apply", "email_read", "email_reply", "email_trash", "schedule", "assessment")
BROWSER_ACTIONS = {"research", "register", "fill", "apply", "schedule", "assessment"}
OPPORTUNITY_ACTIONS = {"register", "fill", "apply"}
PROCESS_STEP_ACTIONS = {"schedule", "assessment"}
MESSAGE_ACTIONS = {"email_reply", "email_trash"}
REPEATABLE = {"research", "email_read"}
PER_ITEM_ACTIONS = {"email_reply", "schedule", "assessment"}
OUTCOMES = ("confirmed", "uncertain", "not_received")
DESTINATION_SOURCES = {"destination_page", "destination_email", "destination_listing"}
EVIDENCE_SOURCES = DESTINATION_SOURCES | {"agent_report"}
PROCESS_CATEGORIES = {"application_update", "interview", "assessment", "offer", "rejection", "recruiter_contact"}
CLEANABLE_CATEGORIES = {"job_alert", "newsletter", "marketing", "notification", "rejection"}
EMAIL_CATEGORIES = PROCESS_CATEGORIES | CLEANABLE_CATEGORIES | {"other"}
CAPABILITY_STATUSES = {"ready", "auth_required", "unavailable", "expired", "revoked"}
SOURCE = "workflow"

_OWNER = re.compile(r"chat:[a-z][a-z0-9_-]{0,62}")
_PROVIDER = re.compile(r"[a-z][a-z0-9_-]{0,39}")
_ACCOUNT = re.compile(r"[A-Za-z0-9_-]{1,80}")
_SCOPE = re.compile(r"[a-z0-9][a-z0-9:._-]{0,99}")
_SHA256 = re.compile(r"[0-9a-f]{64}")

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS wf_control (id INTEGER PRIMARY KEY CHECK(id=1), generation INTEGER NOT NULL, stopped INTEGER NOT NULL, stopped_at TEXT, stop_reason TEXT, resumed_at TEXT, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wf_goals (version INTEGER PRIMARY KEY, status TEXT NOT NULL, summary TEXT NOT NULL, criteria TEXT NOT NULL, profile_version INTEGER, created_at TEXT NOT NULL, superseded_at TEXT)",
    "CREATE TABLE IF NOT EXISTS wf_opportunities (job_id INTEGER PRIMARY KEY REFERENCES jobs(id), source_key TEXT NOT NULL, record TEXT NOT NULL, vacancy TEXT NOT NULL, evaluation TEXT, evaluated_profile_version INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wf_capabilities (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, provider TEXT NOT NULL, account TEXT NOT NULL, status TEXT NOT NULL, checked_at TEXT NOT NULL, valid_until TEXT NOT NULL, agent_provider TEXT, evidence TEXT NOT NULL, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wf_actions (id TEXT PRIMARY KEY, action TEXT NOT NULL, dedupe_key TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, generation INTEGER NOT NULL, job_id INTEGER, step_id INTEGER, store_owner TEXT, message_row INTEGER, capability_id INTEGER NOT NULL, profile_version INTEGER NOT NULL, permission TEXT NOT NULL, user_confirmation TEXT, evaluation TEXT, resume_id TEXT, resume_sha256 TEXT, item_details TEXT, goal_version INTEGER NOT NULL, authorized_at TEXT NOT NULL, expires_at TEXT NOT NULL, completed_at TEXT, evidence TEXT, evidence_source TEXT, evidence_url TEXT, checked_at TEXT, reason TEXT, resolved_by TEXT, updated_at TEXT NOT NULL)",
    "CREATE UNIQUE INDEX IF NOT EXISTS wf_actions_open ON wf_actions(dedupe_key) WHERE status IN ('authorized','uncertain')",
    "CREATE TABLE IF NOT EXISTS wf_action_events (id INTEGER PRIMARY KEY, action_id TEXT NOT NULL REFERENCES wf_actions(id), old_status TEXT, new_status TEXT NOT NULL, actor TEXT NOT NULL, generation INTEGER NOT NULL, detail TEXT, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wf_messages (message_row INTEGER PRIMARY KEY REFERENCES messages(id), category TEXT NOT NULL, received_at TEXT NOT NULL, link_evidence TEXT, status TEXT NOT NULL, trashed_at TEXT, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wf_cleanup_rules (version INTEGER PRIMARY KEY, categories TEXT NOT NULL, user_confirmation TEXT NOT NULL, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wf_runs (id TEXT PRIMARY KEY, status TEXT NOT NULL, provider TEXT NOT NULL, generation INTEGER NOT NULL, limits TEXT NOT NULL, loop_id TEXT, name TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, stopped_at TEXT, note TEXT, launch_output TEXT, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wf_vacancy_decisions (id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id), profile_version INTEGER NOT NULL, vacancy_sha256 TEXT NOT NULL, reasons TEXT NOT NULL, user_confirmation TEXT NOT NULL, created_at TEXT NOT NULL)",
)


def new_id(prefix):
    """ID só com letras: o Store recusa sequências longas de dígitos em texto livre."""
    return prefix + "".join(secrets.choice(ascii_lowercase) for _ in range(20))


def _fields(payload, allowed, required=(), name="payload"):
    if not isinstance(payload, dict):
        raise ValueError(f"{name}: envie um objeto JSON")
    unknown = sorted(str(key)[:40] for key in set(payload) - set(allowed))
    if unknown:
        raise ValueError(f"{name}: campos não reconhecidos: {', '.join(unknown)}")
    missing = [key for key in required if payload.get(key) is None]
    if missing:
        raise ValueError(f"{name}: campos obrigatórios ausentes: {', '.join(missing)}")
    return payload


def _int(value, field, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{field}: inteiro entre {low} e {high}")
    return value


def _match(pattern, value, field, hint):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{field}: {hint}")
    return value


def _owner(value):
    return _match(_OWNER, value, "owner", "use chat:<sessao>, letras minúsculas, dígitos, _ ou -")


def _moment(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field}: informe data e hora ISO com fuso")
    return _instant(value, field)


def _clean_json(value, field, limit=20_000):
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError):
        raise ValueError(f"{field}: use apenas valores JSON simples") from None
    if len(encoded) > limit:
        raise ValueError(f"{field}: conteúdo excede {limit} caracteres")
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str) and (_SECRET.search(item) or _EMAIL.search(item) or "\x00" in item):
            raise ValueError(f"{field}: remova contatos, credenciais ou códigos de acesso")
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return encoded


def _validate_vacancy(vacancy):
    """Valida o payload de vaga pelo próprio policy.evaluate, com preferências neutras."""
    from scripts.job.policy import evaluate
    neutral = {"roles": ["-"], "modalities": ["-"], "currencies": ["-"], "levels": [], "contracts": [], "locations": [],
               "technologies": [], "blocked_companies": [], "blocked_sectors": [], "blocked_platforms": [], "missing": "accept",
               "languages": [], "salary": {"missing": "accept", "estimated": "accept", "range": "ask", "floors": [], "public_expectation": None}}
    evaluate(neutral, vacancy)


def _tables(conn):
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','index')")}


def _capability_usable(conn, kind, provider, account, now):
    """Observação ``ready`` mais recente ainda válida e sem revogação posterior, ou None."""
    rows = conn.execute("SELECT * FROM wf_capabilities WHERE kind=? AND provider=? AND account=? ORDER BY checked_at, id", (kind, provider, account)).fetchall()
    ready = [row for row in rows if row["status"] == "ready"]
    if not ready:
        return None
    best = ready[-1]
    if any(row["status"] != "ready" and (row["checked_at"] >= best["checked_at"] or row["id"] > best["id"]) for row in rows):
        return None
    stamp = _stamp(now)
    return best if best["checked_at"] <= stamp < best["valid_until"] else None


class Workflow:
    """API de operação. ``root`` é a pasta do projeto; o estado fica em ``root/.job``.

    Todas as entradas inválidas geram ``ValueError`` com mensagem em português.
    ``clock`` (opcional, testes) devolve ``datetime`` com fuso.
    """

    def __init__(self, root: Path, *, clock=None):
        try:
            root = Path(root).expanduser().resolve(strict=True)
        except OSError:
            raise ValueError("root: pasta do projeto não encontrada") from None
        if not root.is_dir():
            raise ValueError("root: informe a pasta do projeto")
        self.root = root
        self.private = root / ".job"
        self.db_path = self.private / "control.sqlite3"
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._store = None

    def close(self):
        if self._store is not None:
            self._store.close()
            self._store = None

    def _now(self):
        return _instant(self._clock())

    def _check_private(self):
        for path in (self.private, self.db_path):
            if path.is_symlink():
                raise ValueError("estado: links simbólicos não são aceitos em .job")
        from .profile import Profile
        # The same directory, file and SQLite sidecar checks protect all modules.
        Profile(self.root).get()

    def _writer(self):
        if self._store is None:
            self._check_private()
            store = Store(self.db_path)
            try:
                with store.transaction():
                    for statement in _SCHEMA:
                        store.conn.execute(statement)
                    store.conn.execute("INSERT OR IGNORE INTO wf_control(id,generation,stopped,updated_at) VALUES(1,1,0,?)", (_stamp(self._now()),))
            except BaseException:
                store.close()
                raise
            self._store = store
        return self._store

    @contextmanager
    def _read(self):
        """Store somente leitura (ou None em instalação nova); nunca cria arquivos."""
        if self._store is not None:
            yield self._store
            return
        self._check_private()
        store = Store.open_readonly(self.db_path)
        try:
            yield store
        finally:
            if store is not None:
                store.close()

    @staticmethod
    def _control(conn):
        if conn is None or "wf_control" not in _tables(conn):
            return {"generation": 1, "stopped": False, "stopped_at": None, "stop_reason": None, "resumed_at": None}
        row = dict(conn.execute("SELECT * FROM wf_control WHERE id=1").fetchone())
        row["stopped"] = bool(row["stopped"])
        row.pop("id", None)
        row.pop("updated_at", None)
        return row

    @staticmethod
    def _goal(conn):
        if conn is None or "wf_goals" not in _tables(conn):
            return None
        row = conn.execute("SELECT * FROM wf_goals WHERE status='active' ORDER BY version DESC LIMIT 1").fetchone()
        if row is None:
            return None
        goal = dict(row)
        goal["criteria"] = json.loads(goal["criteria"])
        return goal

    def _progress(self, conn, goal, now):
        if goal is None or goal["criteria"].get("target_applications") is None:
            return None
        period = goal["criteria"].get("period_days")
        since = _stamp(now - timedelta(days=period)) if period else goal["created_at"]
        from .profile import Profile
        profile = Profile(self.root).get()
        preferences = profile.get("sections", {}).get("preferences")
        rows = conn.execute(
            "SELECT DISTINCT a.job_id, o.vacancy, a.item_details FROM wf_actions a "
            "JOIN wf_opportunities o ON o.job_id=a.job_id "
            "JOIN jobs j ON j.id=a.job_id "
            "WHERE a.action='apply' AND a.status='confirmed' "
            "AND a.goal_version=? AND j.identity_verified=1 "
            "AND NOT EXISTS (SELECT 1 FROM identity_conflicts c WHERE c.job_id=a.job_id)",
            (goal["version"],),
        ).fetchall()
        done = set()
        for row in rows:
            try:
                submitted = json.loads(row['item_details'] or '{}').get('submitted_at')
                if submitted is None or _moment(submitted, 'submitted_at') < _instant(since):
                    continue
                if preferences and self._evaluate_for(conn, row['job_id'], preferences, profile['version'], row['vacancy'])['decision'] == 'eligible':
                    done.add(row['job_id'])
            except ValueError:
                pass  # Perfil incompleto ou vaga sem avaliação válida não conta na meta.
        target = goal["criteria"]["target_applications"]
        return {"confirmed_applications": len(done), "target_applications": target, "period_days": period, "reached": len(done) >= target}

    def _approved_profile(self):
        try:
            from scripts.job.profile import Profile
        except ImportError:
            raise ValueError("perfil: módulo indisponível; ações externas bloqueadas") from None
        profile = Profile(self.root)
        data, status = profile.get(), profile.status()
        if not status.get("approved") or not data.get("version") or data.get("approved_version") != data.get("version"):
            raise ValueError("perfil: aprove a versão atual do perfil antes de qualquer ação externa")
        return data

    def _profile_status(self):
        try:
            from scripts.job.profile import Profile
            status = Profile(self.root).status()
        except (ImportError, ValueError) as exc:
            return {"available": False, "detail": str(exc)[:200]}
        return {"available": True, **{key: status.get(key) for key in ("approved", "version", "next_section", "missing", "questions")}}

    def _event(self, conn, action_id, old, new, actor, generation, detail, now):
        conn.execute("INSERT INTO wf_action_events(action_id,old_status,new_status,actor,generation,detail,created_at) VALUES(?,?,?,?,?,?,?)", (action_id, old, new, actor, generation, detail, _stamp(now)))

    # ----- objetivo e oportunidades ------------------------------------------------

    def configure_goal(self, payload: dict) -> dict:
        """Persiste o objetivo explícito.

        Payload: ``{summary: str, actions: [ação de ACTIONS, ...], period_days?: int 1..90,
        target_applications?: int 1..500 (só com apply), portals?: [str] (vazio = qualquer
        portal), replace_version?: int}``. Sem meta ou prazo o objetivo é aberto (modo
        chat); nada é inventado. Meta sem prazo conta desde a criação do objetivo.
        Retorna ``{version, status, summary, criteria, profile_version, created_at, unchanged}``.
        Objetivo ativo idêntico é idempotente; diferente só é substituído com
        ``replace_version`` igual à versão ativa (a anterior fica ``superseded``).
        """
        p = _fields(payload, {"summary", "actions", "period_days", "target_applications", "portals", "replace_version"}, ("summary", "actions"))
        summary = _text(p["summary"], "summary", limit=300)
        actions = p["actions"]
        if not isinstance(actions, list) or not actions or len(set(actions)) != len(actions) or set(actions) - set(ACTIONS):
            raise ValueError("actions: lista não vazia, sem repetição, com ações de " + ", ".join(ACTIONS))
        criteria = {"actions": [a for a in ACTIONS if a in actions],
                    "period_days": None if p.get("period_days") is None else _int(p["period_days"], "period_days", 1, 90),
                    "target_applications": None}
        if p.get("target_applications") is not None:
            if "apply" not in actions:
                raise ValueError("target_applications: só se aplica a objetivos com apply")
            criteria["target_applications"] = _int(p["target_applications"], "target_applications", 1, 500)
        portals = p.get("portals", [])
        if not isinstance(portals, list) or len(set(portals)) != len(portals):
            raise ValueError("portals: lista de portais sem repetição")
        criteria["portals"] = sorted(_text(portal, "portals", limit=100) for portal in portals)
        replace = p.get("replace_version")
        profile_version = None
        try:
            profile_version = self._approved_profile()["version"]
        except ValueError:
            pass
        store, now = self._writer(), self._now()
        with store.transaction():
            active = self._goal(store.conn)
            if active and active["summary"] == summary and active["criteria"] == criteria:
                return {**active, "unchanged": True}
            if active and replace != active["version"]:
                raise ValueError(f"objetivo: já existe objetivo ativo versão {active['version']} com outros critérios; envie replace_version para substituí-lo")
            if active is None and replace is not None:
                raise ValueError("replace_version: não há objetivo ativo para substituir")
            version = (store.conn.execute("SELECT MAX(version) FROM wf_goals").fetchone()[0] or 0) + 1
            if active:
                store.conn.execute("UPDATE wf_goals SET status='superseded', superseded_at=? WHERE version=?", (_stamp(now), active["version"]))
            store.conn.execute("INSERT INTO wf_goals(version,status,summary,criteria,profile_version,created_at) VALUES(?,?,?,?,?,?)", (version, "active", summary, json.dumps(criteria, sort_keys=True), profile_version, _stamp(now)))
            return {**self._goal(store.conn), "unchanged": False}

    def opportunity(self, payload: dict) -> dict:
        """Registra uma vaga (oportunidade), nunca uma candidatura.

        Payload: ``{company: str, title: str, portal: str, aliases: [job:portal:id |
        url:https://... | application:portal:id], vacancy: {payload de policy.evaluate},
        identity_verified?: bool (anúncio público conferido), evidence?: str (obrigatória
        se identity_verified), source_key?: str, notes?: [str]}``. Exige ao menos um
        alias ``job:`` ou ``url:``; ``application:`` sozinho identifica candidatura.
        Retorna ``{opportunity_id, identity_verified, conflicts, evaluation, profile_version, kind}``.
        ``evaluation`` usa o perfil aprovado; sem aprovação, ``decision`` fica null.
        """
        p = _fields(payload, {"company", "title", "portal", "aliases", "vacancy", "identity_verified", "evidence", "source_key", "notes"}, ("company", "title", "portal", "aliases", "vacancy"))
        aliases = p["aliases"]
        if not isinstance(aliases, list) or not any(isinstance(a, str) and a.startswith(("job:", "url:")) for a in aliases):
            raise ValueError("aliases: inclua job:portal:id ou url:https://...; application: identifica candidatura, não vaga")
        if not isinstance(p["vacancy"], dict):
            raise ValueError("vacancy: objeto obrigatório (veja policy.py)")
        vacancy_json = _clean_json(p["vacancy"], "vacancy")
        _validate_vacancy(p["vacancy"])
        verified = p.get("identity_verified", False)
        if type(verified) is not bool:
            raise ValueError("identity_verified: booleano obrigatório")
        if verified and not p.get("evidence"):
            raise ValueError("evidence: identidade verificada exige evidência do anúncio público")
        source_key = p.get("source_key") or min(a for a in aliases if a.startswith(("job:", "url:")))
        record = {"source_key": source_key, "company": p["company"], "title": p["title"], "portal": p["portal"], "aliases": aliases,
                  "identity_verified": verified, "evidence": p.get("evidence"), "notes": p.get("notes", []), "state": "discovered",
                  "eligible": None, "confirmed_at": None}
        evaluation, profile_version = {"decision": None, "reasons": ["Perfil ainda não aprovado; avaliação pendente."]}, None
        try:
            profile = self._approved_profile()
        except ValueError:
            profile = None
        if profile:
            from scripts.job.policy import evaluate
            evaluation, profile_version = evaluate(profile["sections"]["preferences"], p["vacancy"]), profile["version"]
            record["eligible"] = {"eligible": True, "discarded": False}.get(evaluation["decision"])
            if evaluation["decision"] == "discarded":
                record["state"] = "discarded"
        store, now = self._writer(), self._now()
        with store.transaction():
            matches = {row[0] for alias in aliases for row in store.conn.execute("SELECT job_id FROM aliases WHERE alias=?", (alias,))}
            if len(matches) == 1:
                previous = store.conn.execute("SELECT * FROM jobs WHERE id=?", (next(iter(matches)),)).fetchone()
                if "identity_verified" not in p:
                    record["identity_verified"] = bool(previous["identity_verified"])
                    if not record["evidence"]:
                        record["evidence"] = previous["evidence"]
                if previous["state"] not in {"discovered", "discarded"}:
                    record["state"] = previous["state"]
                    record["confirmed_at"] = previous["confirmed_at"]
                    record["evidence"] = record["evidence"] or previous["evidence"]
                stored_key = store.conn.execute("SELECT source_key FROM wf_opportunities WHERE job_id=?", (previous["id"],)).fetchone()
                if stored_key:
                    source_key = record["source_key"] = stored_key[0]
            job_id = store.import_records([record], SOURCE)["job_ids"][0]
            stored = {key: value for key, value in record.items()}
            store.conn.execute(
                "INSERT INTO wf_opportunities(job_id,source_key,record,vacancy,evaluation,evaluated_profile_version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(job_id) DO UPDATE SET source_key=excluded.source_key,record=excluded.record,vacancy=excluded.vacancy,evaluation=excluded.evaluation,evaluated_profile_version=excluded.evaluated_profile_version,updated_at=excluded.updated_at",
                (job_id, source_key, json.dumps(stored, ensure_ascii=False, sort_keys=True), vacancy_json, json.dumps(evaluation, ensure_ascii=False), profile_version, _stamp(now), _stamp(now)))
            if profile:
                effective = self._evaluate_for(store.conn, job_id, profile['sections']['preferences'], profile_version, vacancy_json)
                if effective != evaluation:
                    evaluation = effective
                    stored['eligible'] = evaluation['decision'] == 'eligible'
                    store.import_records([stored], SOURCE)
                    store.conn.execute('UPDATE wf_opportunities SET record=?,evaluation=? WHERE job_id=?',
                                       (json.dumps(stored, ensure_ascii=False), json.dumps(evaluation, ensure_ascii=False), job_id))
            job = store.conn.execute("SELECT identity_verified, state FROM jobs WHERE id=?", (job_id,)).fetchone()
            conflicts = [row[0] for row in store.conn.execute("SELECT detail FROM identity_conflicts WHERE job_id=? ORDER BY id", (job_id,))]
        return {"opportunity_id": job_id, "kind": "opportunity", "state": job["state"], "identity_verified": bool(job["identity_verified"]),
                "conflicts": conflicts, "evaluation": evaluation, "profile_version": profile_version}

    # ----- consulta ----------------------------------------------------------------

    @staticmethod
    def _evaluate_for(conn, job_id, preferences, version, vacancy_json):
        from .policy import evaluate
        result = evaluate(preferences, json.loads(vacancy_json))
        if result['decision'] != 'blocked' or 'wf_vacancy_decisions' not in _tables(conn):
            return result
        digest = hashlib.sha256(vacancy_json.encode()).hexdigest()
        row = conn.execute('SELECT id,reasons FROM wf_vacancy_decisions WHERE job_id=? AND profile_version=? AND vacancy_sha256=? ORDER BY id DESC LIMIT 1',
                           (job_id, version, digest)).fetchone()
        if row and set(json.loads(row['reasons'])) == set(result['reasons']):
            return {'decision': 'eligible', 'reasons': [], 'accepted_unknowns': result['reasons'], 'decision_id': row['id']}
        return result

    def decide_opportunity(self, payload):
        """Accept specified missing information for one vacancy and this profile only.

        Payload: opportunity_id, reasons (exact current pending reasons),
        user_confirmation. Does not override rejection, salary floors or identity.
        A changed profile or advertisement invalidates this decision.
        """
        p = _fields(payload, {'opportunity_id', 'reasons', 'user_confirmation'}, ('opportunity_id', 'reasons', 'user_confirmation'))
        job_id = _int(p['opportunity_id'], 'opportunity_id', 1, 10**12)
        confirmation = _text(p['user_confirmation'], 'user_confirmation', limit=500)
        reasons = p['reasons']
        if not isinstance(reasons, list) or not reasons or not all(isinstance(r, str) for r in reasons):
            raise ValueError('Confira os motivos pendentes antes de pedir a decisão para esta vaga.')
        profile = self._approved_profile()
        store = self._writer()
        with store.transaction():
            row = store.conn.execute('SELECT * FROM wf_opportunities WHERE job_id=?', (job_id,)).fetchone()
            if row is None:
                raise ValueError('Registre a vaga antes de registrar a decisão.')
            from .policy import evaluate
            evaluation = evaluate(profile['sections']['preferences'], json.loads(row['vacancy']))
            allowed = {'Remuneração ausente.', 'Remuneração estimada, sem confirmação.', 'Idiomas da vaga desconhecidos.', 'Tecnologias ausentes.'}
            if evaluation['decision'] != 'blocked' or set(reasons) != set(evaluation['reasons']):
                raise ValueError('A decisão não corresponde às informações pendentes atuais desta vaga.')
            if any(reason not in allowed and not reason.startswith('Informação ausente: ') for reason in reasons):
                raise ValueError('Esta pendência exige conferir a informação no anúncio ou no portal; não pode ser liberada por esta decisão.')
            from .profile import Profile
            current = Profile._read(store.conn)
            if current['version'] != profile['version'] or current['approved_version'] != profile['version']:
                raise ValueError('O perfil mudou; confira o resumo e a vaga antes de decidir.')
            digest = hashlib.sha256(row['vacancy'].encode()).hexdigest()
            store.conn.execute('INSERT INTO wf_vacancy_decisions(job_id,profile_version,vacancy_sha256,reasons,user_confirmation,created_at) VALUES(?,?,?,?,?,?)',
                               (job_id, profile['version'], digest, json.dumps(reasons, ensure_ascii=False), confirmation, _stamp(self._now())))
            result = self._evaluate_for(store.conn, job_id, profile['sections']['preferences'], profile['version'], row['vacancy'])
            record = json.loads(row['record'])
            record['eligible'] = True
            if record['state'] == 'blocked':
                record['state'] = 'discovered'
            store.import_records([record], SOURCE)
            store.conn.execute('UPDATE wf_opportunities SET record=?,evaluation=?,updated_at=? WHERE job_id=?',
                               (json.dumps(record, ensure_ascii=False), json.dumps(result, ensure_ascii=False), _stamp(self._now()), job_id))
        return {'opportunity_id': job_id, 'profile_version': profile['version'], 'evaluation': result}

    def state(self) -> dict:
        """Status seguro, somente leitura; em instalação nova devolve estado vazio sem criar ``.job``.

        Retorna ``{initialized, control: {generation, stopped, ...}, goal, progress,
        profile: {available, approved, version, next_section, missing, questions},
        counts, ledger (Store.summary), pending: [...], capabilities: [...],
        mail_coverage, runner, next_steps: [str], message}``. Não inclui identidade,
        contatos, preferências ou piso salarial.
        """
        now = self._now()
        with self._read() as store:
            conn = store.conn if store else None
            tables = _tables(conn) if conn else set()
            control, goal = self._control(conn), self._goal(conn)
            result = {"initialized": conn is not None, "control": control, "goal": goal, "progress": None, "ledger": None,
                      "counts": {"opportunities": 0, "actions": {}, "messages": 0}, "pending": [], "capabilities": [], "mail_coverage": None, "runner": None}
            if conn is not None:
                result["ledger"] = store.summary()
                from .profile import Profile
                profile = Profile(self.root).get()
                preferences = profile.get("sections", {}).get("preferences")
                confirmed = [job for job in store.list_jobs() if job["active"] and job["state"] == "confirmed" and job["identity_verified"] and not job["conflicts"]]
                compatible, unknown = [], 0
                for job in confirmed:
                    row = conn.execute("SELECT vacancy FROM wf_opportunities WHERE job_id=?", (job["id"],)).fetchone() if "wf_opportunities" in tables else None
                    try:
                        decision = self._evaluate_for(conn, job['id'], preferences, profile['version'], row[0])['decision'] if preferences and row else None
                    except ValueError:
                        decision = None
                    if decision == "eligible":
                        compatible.append(job)
                    elif decision in {None, "blocked"}:
                        unknown += 1
                result["ledger"].update(eligible_confirmed=len(compatible), compatible_unknown=unknown,
                                        period_confirmed=sum(job["confirmed_at"] is not None for job in compatible),
                                        evaluation_profile_version=profile["version"])
                result["counts"]["messages"] = result["ledger"]["messages"]
                for step in store.list_steps():
                    if step["state"] not in TERMINAL_STATES:
                        result["pending"].append({"type": "step", "step_id": step["id"], "opportunity_id": step["job_id"], "kind": step["kind"], "state": step["state"], "due_at": step["due_at"], "overdue": step["overdue"],
                                                  'company': step['company'], 'title': step['title'], 'summary': step['summary'], 'reason': step['reason']})
            if "wf_actions" in tables:
                result["progress"] = self._progress(conn, goal, now)
                result["counts"]["opportunities"] = conn.execute("SELECT COUNT(*) FROM wf_opportunities").fetchone()[0]
                result["counts"]["actions"] = {row[0]: row[1] for row in conn.execute("SELECT status, COUNT(*) FROM wf_actions GROUP BY status")}
                for row in conn.execute("SELECT * FROM wf_actions WHERE status IN ('authorized','uncertain') ORDER BY authorized_at"):
                    status = "uncertain" if row["status"] == "authorized" and row["expires_at"] <= _stamp(now) else row["status"]
                    result["pending"].append({"type": "action", "action_id": row["id"], "action": row["action"], "status": status, "opportunity_id": row["job_id"], "owner": row["owner"], "generation": row["generation"], "reason": row["reason"]})
                seen = set()
                for row in conn.execute("SELECT * FROM wf_capabilities ORDER BY id DESC"):
                    key = (row["kind"], row["provider"], row["account"])
                    if key not in seen:
                        seen.add(key)
                        usable = _capability_usable(conn, *key, now)
                        result["capabilities"].append({"kind": key[0], "provider": key[1], "account": key[2], "status": row["status"], "checked_at": row["checked_at"], "agent_provider": row["agent_provider"], "usable": usable is not None, "note": "Observação registrada; não comprova autenticação atual."})
                run = conn.execute("SELECT id,status,provider,generation,loop_id,created_at,expires_at,note FROM wf_runs ORDER BY created_at DESC LIMIT 1").fetchone()
                result["runner"] = dict(run) if run else None
        monitor = Monitor.readonly(self.db_path) if result["initialized"] else None
        if monitor is not None:
            try:
                result["mail_coverage"] = [{k: a[k] for k in ("provider", "account", "status", "checked_at", "covered_until", "due")} for a in monitor.status()["accounts"]]
            finally:
                monitor.db.close()
        result["profile"] = self._profile_status()
        result["next_steps"] = self._next_steps(result)
        result["message"] = "\n".join(["Situação do Carreira Guiada:"] + [f"- {step}" for step in result["next_steps"]])
        return result

    @staticmethod
    def _next_steps(s):
        steps = []
        if s['ledger']:
            ledger = s['ledger']
            steps.append(f"Nos registros: {ledger['confirmed']} candidatura(s) confirmada(s), {ledger['uncertain']} envio(s) em dúvida e {ledger['discarded']} vaga(s) descartada(s).")
        if s["control"]["stopped"]:
            steps.append('O trabalho está parado. Seu progresso está salvo; diga "continuar" quando quiser retomar.')
        if not s["profile"].get("approved"):
            section = s["profile"].get("next_section")
            labels = {'identity': 'seus dados de contato', 'preferences': 'o tipo de vaga que procura', 'sources': 'os endereços dos sites onde quer procurar vagas', 'permissions': 'o que posso fazer por você', 'connections': 'as contas que quer usar', 'limits': 'o funcionamento no chat'}
            steps.append(f"Vamos completar {labels.get(section, 'seu perfil')}." if section else "Confira o resumo do perfil e diga se está correto.")
        if s["goal"] is None:
            steps.append('Diga se quer apenas conhecer vagas ou também se candidatar. Não precisa escolher uma quantidade nem um prazo.')
        uncertain = [p for p in s["pending"] if p["type"] == "action" and p["status"] == "uncertain"]
        if uncertain:
            steps.append(f"Vou conferir {len(uncertain)} ação(ões) que ficaram sem confirmação antes de repetir qualquer uma delas.")
        for account in s.get('mail_coverage') or []:
            if account['status'] == 'partial':
                steps.append(f"A leitura dos e-mails da conta {account['account']} ficou incompleta. O ponto de retomada está salvo.")
            elif account['status'] in {'auth_required', 'unavailable'}:
                steps.append(f"Ainda não consegui conferir os e-mails da conta {account['account']}. Preciso verificar o acesso antes de continuar essa consulta.")
        for pending in s['pending']:
            if pending['type'] != 'step' or pending['state'] in {'action_started', 'uncertain'}:
                continue
            label = 'Depende de você' if pending['state'] == 'candidate_pending' else 'Etapa pendente'
            summary = pending.get('summary') or 'Conferir a próxima etapa no portal'
            if summary.startswith('Ação ') and summary.endswith(' registrada pelo fluxo'):
                summary = {'apply': 'Conferir o envio da candidatura', 'fill': 'Concluir o preenchimento do formulário',
                           'register': 'Concluir o cadastro no portal'}.get(pending['kind'], 'Conferir a próxima etapa no portal')
            steps.append(f"{label} em {pending['company']}: {summary}.")
        if not any(c["usable"] for c in s["capabilities"]):
            steps.append('Ainda preciso conferir o acesso aos sites ou ao e-mail. Se houver login, eu explico onde entrar; não me passe sua senha.')
        if s["progress"] and s["progress"]["reached"]:
            steps.append("Meta do período atingida.")
        if not s['pending'] and not s['control']['stopped'] and s['goal'] and s['profile'].get('approved') and any(c['usable'] for c in s['capabilities']) and not (s['progress'] and s['progress']['reached']):
            steps.append('Posso continuar a pesquisa e as etapas que você autorizou.')
        return steps

    # ----- autorização e resultado -------------------------------------------------

    def _expire(self, store, now):
        rows = store.conn.execute("SELECT * FROM wf_actions WHERE status='authorized' AND expires_at<=?", (_stamp(now),)).fetchall()
        for row in rows:
            self._to_uncertain(store, row, "Prazo da autorização venceu sem resultado conferido; confira o destino.", "system", now)

    def _to_uncertain(self, store, row, reason, actor, now):
        store.conn.execute("UPDATE wf_actions SET status='uncertain', reason=?, updated_at=? WHERE id=?", (reason, _stamp(now), row["id"]))
        self._event(store.conn, row["id"], row["status"], "uncertain", actor, row["generation"], reason, now)
        self._step_to(store, row, "uncertain", reason)
        if row["action"] == "apply":
            self._sync_job(store, row["job_id"], "pending_verification")

    def _step_to(self, store, row, target, evidence):
        if not row["step_id"]:
            return
        step = store.conn.execute("SELECT state, owner FROM steps WHERE id=?", (row["step_id"],)).fetchone()
        state = step["state"]
        owner = row["store_owner"] if step["owner"] == row["store_owner"] else None
        if state == "action_started" and target in ("uncertain", "pending"):
            store.transition_step(row["step_id"], "uncertain", evidence=evidence, owner=owner)
            state = "uncertain"
        if target == "pending" and state == "uncertain":
            store.transition_step(row["step_id"], "pending", evidence="not_received: " + evidence)
        if target == "completed" and state in ("action_started", "uncertain"):
            store.transition_step(row["step_id"], "completed", evidence=evidence, owner=owner if state == "action_started" else None)

    def _sync_job(self, store, job_id, state, evidence=None, confirmed_at=None):
        row = store.conn.execute("SELECT record FROM wf_opportunities WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            return
        record = json.loads(row["record"])
        record.update(state=state, confirmed_at=confirmed_at)
        if evidence:
            record["evidence"] = evidence
        store.import_records([record], SOURCE)

    def authorize(self, payload: dict) -> dict:
        """Grava a intenção de UMA ação externa antes de qualquer efeito. Não executa nada.

        Payload: ``{action: ACTIONS, owner: chat:<sessao>, generation: int
        (de state()), channel: {provider, account} (capacidade observada; derivada da
        mensagem quando omitida), opportunity_id?: int (register/fill/apply/schedule/
        assessment), step_key?: str (schedule/assessment ou fill complementar:
        etapa existente do Store), schedule?: {starts_at: ISO futuro com fuso},
        message?: {provider, account, message_id} (email_reply/email_trash),
        scope_key?: str (research/email_read; diferencia escopos),
        source_url?: str (obrigatória em research, dentro das fontes aprovadas), resume_id? +
        resume_sha256? (obrigatórios em fill/apply), user_confirmation?: str (obrigatório
        quando a permissão é ask e SEMPRE em email_reply/schedule/assessment, mesmo com
        allow; resumo da resposta explícita do usuário para este item),
        assistance_rules?: str (obrigatório em assessment: regra da avaliação
        que permite assistência), destination_platform?: str (plataforma de destino
        conferida; obrigatória em etapa complementar com bloqueios de plataforma),
        reply?: {recipient: "message_sender", content_sha256:
        sha256 do texto exato confirmado, summary: str} (obrigatório em email_reply),
        profile_version?: int, lease_seconds?: 60..3600 (padrão 900)}``.
        Bloqueia: parada, geração antiga, sem objetivo ou ação fora
        dele, meta atingida, perfil não aprovado, permissão deny/ask sem confirmação,
        capacidade ausente/expirada/revogada, conta não declarada no perfil, vaga não
        elegível ou com identidade não verificada, candidatura já confirmada ou incerta,
        currículo não aprovado/alterado/hash divergente, duplicata aberta ou incerta.
        Retorna ``{action_id, action, status: authorized, owner, generation, expires_at,
        dedupe_key, opportunity_id, profile_version, permission, resume}``.
        """
        p = _fields(payload, {"action", "owner", "generation", "channel", "opportunity_id", "step_key", "message", "scope_key", "resume_id", "resume_sha256", "user_confirmation", "profile_version", "lease_seconds", "assistance_rules", "reply", "schedule", "source_url", "destination_platform"}, ("action", "owner", "generation"))
        action = p["action"]
        if action not in ACTIONS:
            raise ValueError("action: use " + ", ".join(ACTIONS))
        owner, generation = _owner(p["owner"]), _int(p["generation"], "generation", 1, 10**9)
        lease = _int(p.get("lease_seconds", 900), "lease_seconds", 60, 3600)
        confirmation = _text(p.get("user_confirmation"), "user_confirmation", optional=True, limit=500)
        store = self._writer()
        control = self._control(store.conn)
        if control["stopped"]:
            raise ValueError("Parada ativa: nenhuma ação nova é autorizada antes de resume().")
        if generation != control["generation"]:
            raise ValueError("generation: geração antiga; consulte state() e use a geração vigente")
        profile = self._approved_profile()
        if p.get("profile_version") is not None and p["profile_version"] != profile["version"]:
            raise ValueError("profile_version: o perfil mudou; revise a versão aprovada atual")
        sections = profile["sections"]
        permissions = sections.get("permissions", {})
        permission = permissions.get(action, "ask")
        if permission == "deny":
            raise ValueError(f"permissão: {action} está negada no perfil")
        if permission == "allow" and action not in permissions.get("confirmed", []):
            raise ValueError(f"permissão: allow para {action} sem consentimento confirmado")
        if (permission == "ask" or action in PER_ITEM_ACTIONS) and not confirmation:
            raise ValueError(f"permissão: {action} exige confirmação do usuário para este item; informe user_confirmation no chat")
        details = None
        if action == 'research':
            from .sources import research_target
            details = {'source_url': research_target(p.get('source_url'), sections.get('sources', {}).get('urls', []))}
        elif p.get('source_url') is not None:
            raise ValueError('source_url só se aplica à pesquisa.')
        followup_fill = action == 'fill' and p.get('step_key') is not None
        process_action = action in PROCESS_STEP_ACTIONS or followup_fill
        if action == 'schedule':
            scheduling = _fields(p.get('schedule'), {'starts_at'}, ('starts_at',), 'schedule')
            starts = _moment(scheduling['starts_at'], 'schedule.starts_at')
            if starts <= self._now():
                raise ValueError('O horário da entrevista precisa estar no futuro, com o fuso confirmado.')
            details = {'starts_at': scheduling['starts_at']}
        elif p.get('schedule') is not None:
            raise ValueError('O horário de entrevista só se aplica ao agendamento.')
        if action == "assessment":
            details = {"assistance_rules": _text(p.get("assistance_rules"), "assistance_rules", limit=500)}
        elif p.get("assistance_rules") is not None:
            raise ValueError("assistance_rules: só se aplica a assessment")
        if action == "email_reply":
            reply = _fields(p.get("reply"), {"recipient", "content_sha256", "summary"}, ("recipient", "content_sha256", "summary"), "reply")
            if reply["recipient"] != "message_sender":
                raise ValueError("reply.recipient: resposta só ao remetente da mensagem registrada (message_sender)")
            details = {"recipient": "message_sender", "content_sha256": _match(_SHA256, reply["content_sha256"], "reply.content_sha256", "sha256 do texto exato confirmado pelo usuário"),
                       "summary": _text(reply["summary"], "reply.summary", limit=500)}
        elif p.get("reply") is not None:
            raise ValueError("reply: só se aplica a email_reply")
        destination = _text(p.get('destination_platform'), 'destination_platform', optional=True, limit=100)
        if destination is not None:
            if action not in OPPORTUNITY_ACTIONS | PROCESS_STEP_ACTIONS:
                raise ValueError('destination_platform: informe somente para uma ação no portal da vaga.')
            details = {**(details or {}), 'destination_platform': destination}
        resume = None
        if action in {'fill', 'apply'} or p.get("resume_id") is not None:
            resume = self._approved_resume(p.get("resume_id"), p.get("resume_sha256"))
        accounts = sections.get("connections", {}).get("accounts", [])
        now = self._now()
        with store.transaction():
            self._expire(store, now)
            control = self._control(store.conn)
            if control["stopped"] or generation != control["generation"]:
                raise ValueError("Parada ou nova geração registrada durante a autorização; ação recusada.")
            from .profile import Profile
            current_profile = Profile._read(store.conn)
            if current_profile["version"] != profile["version"] or current_profile["approved_version"] != profile["version"]:
                raise ValueError("O perfil mudou durante a autorização. Confira a versão atual antes de agir.")
            run = None
            goal = self._goal(store.conn)
            if goal is None or action not in goal["criteria"]["actions"]:
                raise ValueError(f"objetivo: {action} não faz parte do objetivo ativo")
            job, message, step_id, evaluation = None, None, None, None
            if action in OPPORTUNITY_ACTIONS | PROCESS_STEP_ACTIONS:
                job = self._eligible_job(store.conn, p.get("opportunity_id"), action, sections, goal, process_action=process_action, profile_version=profile['version'], destination_platform=destination)
                evaluation = job.pop("evaluation")
            if action in MESSAGE_ACTIONS:
                message = self._message_for(store.conn, p.get("message"), action)
                if message["job_id"] is not None:
                    job = dict(store.conn.execute("SELECT * FROM jobs WHERE id=?", (message["job_id"],)).fetchone())
            channel = p.get("channel") or ({"provider": message["provider"], "account": message["account"]} if message else None)
            kind = "browser" if action in BROWSER_ACTIONS else "mail"
            capability = self._channel(store.conn, kind, channel, action, accounts, message, run, now)
            if action == "research" and not p.get("scope_key"):
                raise ValueError("scope_key: identifique o portal e a consulta desta pesquisa")
            scope = _match(_SCOPE, p.get("scope_key", "default"), "scope_key", "texto curto em minúsculas, dígitos e : . _ -")
            if process_action:
                step_key = _text(p.get("step_key"), "step_key", limit=500)
                key = f"{action}:job:{job['id']}:step:{step_key}"
            elif action in OPPORTUNITY_ACTIONS:
                key = f"{action}:job:{job['id']}"
            elif action in MESSAGE_ACTIONS:
                key = f"{action}:message:{message['id']}"
                if action == "email_reply" and message["step_id"]:
                    step = store.conn.execute("SELECT id,kind FROM steps WHERE id=?", (message["step_id"],)).fetchone()
                    if step["kind"] in {"email_reply", "recruiter_contact", "reply", "response"}:
                        step_id = step["id"]
                        key = f"email_reply:step:{step_id}"
            elif action == "email_read":
                key = f"email_read:{channel['provider']}:{channel['account']}:{scope}"
            else:
                key = f"research:{channel['provider']}:{channel['account']}:{scope}"
            previous = store.conn.execute("SELECT status FROM wf_actions WHERE dedupe_key=? AND status IN ('authorized','uncertain','confirmed')", (key,)).fetchall()
            statuses = {row["status"] for row in previous}
            if "uncertain" in statuses:
                raise ValueError("duplicata: há resultado incerto para esta ação; confira o destino e registre confirmed ou not_received")
            if "authorized" in statuses:
                raise ValueError("duplicata: já existe autorização aberta para esta ação")
            if "confirmed" in statuses and action not in REPEATABLE and not (action == 'fill' and not process_action):
                raise ValueError("duplicata: esta ação já foi confirmada no destino")
            if action == "apply":
                progress = self._progress(store.conn, goal, now)
                if progress and progress["reached"]:
                    raise ValueError("objetivo: meta do período atingida; ajuste o objetivo para continuar")
            action_id = new_id("act_")
            store_owner = "wf-" + action_id
            if process_action:
                row = store.conn.execute("SELECT id,kind FROM steps WHERE job_id=? AND step_key=?", (job["id"], step_key)).fetchone()
                if row is None:
                    raise ValueError("step_key: etapa não encontrada para esta oportunidade")
                if followup_fill and row['kind'] not in {'form', 'additional_form', 'profile_update', 'fill'}:
                    raise ValueError('Esta etapa não é um formulário complementar. Confira se depende de resposta pessoal ou de autorização para um teste.')
                if action == 'schedule' and row['kind'] not in {'interview', 'schedule'}:
                    raise ValueError('O agendamento precisa estar vinculado ao convite para entrevista.')
                step_id = row["id"]
            elif action in OPPORTUNITY_ACTIONS:
                local_key = f"action:fill:{action_id}" if action == 'fill' else f"action:{action}"
                previous_fill = store.conn.execute("SELECT step_id FROM wf_actions WHERE job_id=? AND action='fill' AND dedupe_key=? AND status='not_received' ORDER BY rowid DESC LIMIT 1", (job['id'], key)).fetchone() if action == 'fill' else None
                if previous_fill:
                    old_step = store.conn.execute('SELECT state FROM steps WHERE id=?', (previous_fill['step_id'],)).fetchone()
                    if old_step and old_step['state'] == 'pending':
                        step_id = previous_fill['step_id']
                if step_id is None:
                    step_id = store.upsert_step({"job_id": job["id"], "step_key": local_key, "kind": action, "summary": f"Ação {action} registrada pelo fluxo"})["id"]
            elif action == "email_reply" and step_id is None:
                step_id = store.upsert_step({"job_id": job["id"], "step_key": f"reply:{message['id']}", "kind": "email_reply", "summary": "Resposta aprovada ao recrutador"})["id"]
            if step_id:
                store.claim_step(step_id, store_owner, lease_seconds=lease)
                store.transition_step(step_id, "action_started", owner=store_owner)
            expires = now + timedelta(seconds=lease)
            store.conn.execute(
                "INSERT INTO wf_actions(id,action,dedupe_key,status,owner,generation,job_id,step_id,store_owner,message_row,capability_id,profile_version,permission,user_confirmation,evaluation,resume_id,resume_sha256,item_details,goal_version,authorized_at,expires_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (action_id, action, key, "authorized", owner, generation, job["id"] if job else None, step_id, store_owner if step_id else None, message["id"] if message else None,
                 capability["id"], profile["version"], permission, confirmation, json.dumps(evaluation, ensure_ascii=False) if evaluation else None,
                 resume["id"] if resume else None, resume["sha256"] if resume else None, json.dumps(details, ensure_ascii=False) if details else None, goal["version"], _stamp(now), _stamp(expires), _stamp(now)))
            self._event(store.conn, action_id, None, "authorized", owner, generation, None, now)
        return {"action_id": action_id, "action": action, "status": "authorized", "owner": owner, "generation": generation, "expires_at": _stamp(expires),
                "dedupe_key": key, "opportunity_id": job["id"] if job else None, "profile_version": profile["version"], "permission": permission,
                "resume": {"id": resume["id"], "sha256": resume["sha256"]} if resume else None}

    def _approved_resume(self, resume_id, sha):
        if not isinstance(resume_id, str) or not resume_id:
            raise ValueError("resume_id: envio exige versão aprovada do currículo")
        _match(_SHA256, sha, "resume_sha256", "informe o sha256 do PDF aprovado")
        try:
            from scripts.job.resumes import ResumeManager
        except ImportError:
            raise ValueError("currículo: módulo indisponível; envio bloqueado") from None
        version = ResumeManager(self.root).get(resume_id)
        if version.get("status") != "approved":
            raise ValueError("currículo: somente versão aprovada pode ser enviada")
        if version.get("sha256") != sha or version.get("hashes", {}).get("pdf") != sha:
            raise ValueError("currículo: hash informado não corresponde ao PDF aprovado")
        return version

    def _eligible_job(self, conn, job_id, action, sections, goal, *, process_action=False, profile_version=None, destination_platform=None):
        if type(job_id) is not int:
            raise ValueError("opportunity_id: informe a oportunidade registrada")
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        opp = conn.execute("SELECT * FROM wf_opportunities WHERE job_id=?", (job_id,)).fetchone()
        if job is None or opp is None:
            raise ValueError("opportunity_id: registre a oportunidade com opportunity() antes")
        if not job["identity_verified"] or conn.execute("SELECT 1 FROM identity_conflicts WHERE job_id=?", (job_id,)).fetchone():
            raise ValueError("oportunidade: identidade da vaga não verificada ou em conflito")
        if goal["criteria"]["portals"] and job["portal"] not in goal["criteria"]["portals"]:
            raise ValueError("objetivo: portal fora do objetivo ativo")
        evaluation = None
        if action in {'fill', 'apply'} and not process_action:
            if action == 'fill' and job['state'] == 'confirmed':
                raise ValueError('A candidatura já foi enviada. Um pedido posterior precisa de uma etapa complementar própria.')
            conflicting = 'apply' if action == 'fill' else 'fill'
            if conn.execute("SELECT 1 FROM wf_actions WHERE job_id=? AND action=? AND status IN ('authorized','uncertain')", (job_id, conflicting)).fetchone():
                raise ValueError('Confira o preenchimento ou envio já em andamento antes de iniciar outra ação nesta vaga.')
        if process_action:
            if job["state"] != "confirmed":
                raise ValueError("oportunidade: etapa complementar exige candidatura confirmada")
            from .policy import category, categories
            vacancy = json.loads(opp['vacancy'])
            for setting, field in (('blocked_companies', 'company'), ('blocked_sectors', 'sector'), ('blocked_platforms', 'platform')):
                blocked = categories(sections['preferences'][setting])
                value = vacancy.get(field) or (job['company'] if field == 'company' else job['portal'] if field == 'platform' else None)
                if blocked and (value is None or category(value) in blocked):
                    raise ValueError('Bloqueio vigente da etapa: ' + field)
            if sections['preferences']['blocked_platforms'] and destination_platform is None:
                raise ValueError('destination_platform: confira a plataforma de destino da etapa antes de continuar.')
        if destination_platform is not None:
            from .policy import category, categories
            if category(destination_platform) in categories(sections['preferences']['blocked_platforms']):
                raise ValueError('Bloqueio: plataforma de destino da etapa')
        if not process_action or action == 'fill':
            if action == "apply" and job["state"] == "confirmed":
                raise ValueError("duplicata: candidatura já confirmada para esta oportunidade")
            if job["state"] == "pending_verification":
                raise ValueError("oportunidade: resultado incerto pendente; confira o destino antes")
            evaluation = self._evaluate_for(conn, job_id, sections['preferences'], profile_version, opp['vacancy'])
            if evaluation["decision"] != "eligible":
                raise ValueError("elegibilidade: vaga " + ("descartada" if evaluation["decision"] == "discarded" else "bloqueada") + ": " + "; ".join(evaluation["reasons"]))
        return {**dict(job), "evaluation": evaluation}

    def _message_for(self, conn, ref, action):
        ref = _fields(ref, {"provider", "account", "message_id"}, ("provider", "account", "message_id"), "message")
        row = conn.execute("SELECT m.*, w.category, w.status AS wf_status FROM messages m LEFT JOIN wf_messages w ON w.message_row=m.id WHERE m.provider=? AND m.account=? AND m.message_id=?", (ref["provider"], ref["account"], ref["message_id"])).fetchone()
        if row is None or row["category"] is None:
            raise ValueError("message: registre a mensagem com ingest_email() antes")
        if action == "email_reply":
            if row["job_id"] is None:
                raise ValueError("message: confira o vínculo com a oportunidade antes de responder")
            job = conn.execute("SELECT identity_verified FROM jobs WHERE id=?", (row["job_id"],)).fetchone()
            if not job or not job["identity_verified"] or conn.execute("SELECT 1 FROM identity_conflicts WHERE job_id=?", (row["job_id"],)).fetchone():
                raise ValueError("message: identidade da oportunidade não verificada ou em conflito")
        if action == "email_trash":
            if row["wf_status"] != "active":
                raise ValueError("limpeza: mensagem já tratada")
            rules = conn.execute("SELECT categories FROM wf_cleanup_rules ORDER BY version DESC LIMIT 1").fetchone()
            if rules is None or row["category"] not in json.loads(rules["categories"]):
                raise ValueError("limpeza: categoria não autorizada explicitamente pelo usuário")
            if row["category"] in PROCESS_CATEGORIES and row["job_id"] is None:
                raise ValueError("limpeza: mensagem de processo sem vínculo conferido")
            open_step = conn.execute("SELECT 1 FROM steps WHERE (id=? OR (? IS NOT NULL AND job_id=?)) AND state NOT IN ('completed','cancelled')", (row["step_id"], row["job_id"], row["job_id"])).fetchone()
            if open_step:
                raise ValueError("limpeza: há etapa pendente ligada a esta mensagem ou processo")
        return dict(row)

    def _channel(self, conn, kind, channel, action, accounts, message, run, now):
        channel = _fields(channel, {"provider", "account"}, ("provider", "account"), "channel")
        provider = _match(_PROVIDER, channel["provider"], "channel.provider", "alias curto em minúsculas")
        account = _match(_ACCOUNT, channel["account"], "channel.account", "alias local, sem endereço")
        if message and (provider, account) != (message["provider"], message["account"]):
            raise ValueError("channel: a conta usada difere da conta da mensagem")
        declared = [a for a in accounts if a.get("alias") == account]
        if kind == "mail" and not any(str(a.get("provider", "")).casefold() == provider for a in declared):
            raise ValueError("channel: conta de e-mail não declarada no perfil aprovado")
        # Browser aliases describe an observed session, not a mailbox account.
        # Its readiness is still required below; every action has its own consent.
        capability = _capability_usable(conn, kind, provider, account, now)
        if capability is None:
            raise ValueError(f"capacidade: {kind} {provider}/{account} sem observação válida; observe a sessão antes")
        if run is not None and capability["agent_provider"] != run["provider"].split("/", 1)[0]:
            raise ValueError("capacidade: observação não foi feita no provider do supervisor")
        return capability

    def complete(self, action_id: str, payload: dict) -> dict:
        """Registra o resultado de uma ação autorizada.

        Payload: ``{owner, generation, outcome: confirmed|uncertain|not_received,
        evidence: str curta sem dados pessoais, evidence_source: destination_page|
        destination_email|destination_listing|agent_report (padrão agent_report),
        checked_at?: ISO com fuso (obrigatório em confirmed/not_received),
        submitted_at?: ISO com fuso (somente apply confirmado: horário do envio
        comprovado no destino; ausente fica fora de metas por período),
        evidence_url?: URL https pública, destination?: "trash" (obrigatório em
        email_trash confirmado), resume_sha256?: str}``.
        ``confirmed`` e ``not_received`` exigem fonte ``destination_*``: relato do agente
        só vale como ``uncertain``. Ação ``authorized`` só aceita o próprio owner na
        geração vigente; ``uncertain`` pode ser resolvida por owner da geração vigente.
        Parada ativa recusa registros até ``resume()``. Resultado final repetido é
        idempotente; resultado diferente é recusado. Retorna a ação atualizada.
        """
        if not isinstance(action_id, str) or not action_id.startswith("act_"):
            raise ValueError("action_id: informe o ID devolvido por authorize")
        p = _fields(payload, {"owner", "generation", "outcome", "evidence", "evidence_source", "checked_at", "submitted_at", "evidence_url", "destination", "resume_sha256"}, ("owner", "generation", "outcome", "evidence"))
        owner, generation = _owner(p["owner"]), _int(p["generation"], "generation", 1, 10**9)
        outcome = p["outcome"]
        if outcome not in OUTCOMES:
            raise ValueError("outcome: use confirmed, uncertain ou not_received")
        evidence = _text(p["evidence"], "evidence", limit=1000)
        source = p.get("evidence_source", "agent_report")
        if source not in EVIDENCE_SOURCES:
            raise ValueError("evidence_source: use " + ", ".join(sorted(EVIDENCE_SOURCES)))
        url = _public_url(p.get("evidence_url"))
        now = self._now()
        checked = None
        if outcome != "uncertain":
            if source not in DESTINATION_SOURCES:
                raise ValueError("evidence_source: relato sem conferência no destino não confirma nem descarta; use uncertain")
            checked = _moment(p.get("checked_at"), "checked_at")
            if checked > now + timedelta(minutes=2):
                raise ValueError("checked_at: conferência no futuro")
        store = self._writer()
        with store.transaction():
            self._expire(store, now)
            row = store.conn.execute("SELECT * FROM wf_actions WHERE id=?", (action_id,)).fetchone()
            if row is None:
                raise ValueError("action_id: ação não encontrada")
            submitted = None
            if p.get('submitted_at') is not None:
                if row['action'] != 'apply' or outcome != 'confirmed':
                    raise ValueError('submitted_at: somente para candidatura confirmada.')
                submitted = _moment(p['submitted_at'], 'submitted_at')
                if not _instant(row['authorized_at']) <= submitted <= checked:
                    raise ValueError('submitted_at: o envio deve estar entre a autorização e a conferência.')
            if row["status"] in ("confirmed", "not_received"):
                if row["status"] == outcome:
                    return {**self._action_view(row), "duplicate": True}
                raise ValueError("estado: ação já encerrada com outro resultado")
            control = self._control(store.conn)
            if control["stopped"]:
                raise ValueError("Parada ativa: registros de resultado aguardam resume() e nova conferência no destino.")
            if generation != control["generation"]:
                raise ValueError("generation: executor de geração antiga rejeitado")
            if row["status"] == "authorized" and owner != row["owner"]:
                raise ValueError("owner: somente o responsável registra o resultado desta autorização")
            if row["status"] == "uncertain" and outcome == "uncertain":
                return {**self._action_view(row), "duplicate": True}
            if checked is not None and checked < _instant(row["authorized_at"]):
                raise ValueError("checked_at: conferência anterior à autorização")
            if p.get("resume_sha256") is not None and p["resume_sha256"] != row["resume_sha256"]:
                raise ValueError("resume_sha256: arquivo enviado difere do autorizado")
            if row["action"] == "email_trash" and outcome == "confirmed" and p.get("destination") != "trash":
                raise ValueError("destination: limpeza só move para a lixeira; exclusão permanente é proibida")
            if outcome == "uncertain":
                self._to_uncertain(store, row, evidence, owner, now)
                store.conn.execute("UPDATE wf_actions SET evidence=?, evidence_source=?, evidence_url=? WHERE id=?", (evidence, source, url, action_id))
            else:
                store.conn.execute("UPDATE wf_actions SET status=?, evidence=?, evidence_source=?, evidence_url=?, checked_at=?, completed_at=?, resolved_by=?, updated_at=? WHERE id=?",
                                   (outcome, evidence, source, url, _stamp(checked), _stamp(now), owner, _stamp(now), action_id))
                self._event(store.conn, action_id, row["status"], outcome, owner, generation, evidence, now)
                self._step_to(store, row, "completed" if outcome == "confirmed" else "pending", evidence)
                if row['action'] == 'schedule' and outcome == 'confirmed':
                    details = json.loads(row['item_details'])
                    invitation = store.conn.execute('SELECT step_key FROM steps WHERE id=?', (row['step_id'],)).fetchone()
                    store.upsert_step({'job_id': row['job_id'], 'step_key': 'attendance:' + invitation['step_key'],
                                       'kind': 'interview_attendance', 'state': 'candidate_pending',
                                       'due_at': details['starts_at'], 'summary': 'Participar da entrevista no horário confirmado',
                                       'reason': 'A entrevista é feita pela própria pessoa'})
                if row["action"] == "apply":
                    if outcome == "confirmed":
                        details = json.loads(row['item_details'] or '{}')
                        details['submitted_at'] = _stamp(submitted) if submitted is not None else None
                        store.conn.execute('UPDATE wf_actions SET item_details=? WHERE id=?', (json.dumps(details), action_id))
                        local_day = datetime.fromisoformat(p['submitted_at'].replace('Z', '+00:00')).date().isoformat() if submitted is not None else None
                        self._sync_job(store, row["job_id"], "confirmed", evidence, local_day)
                    else:
                        self._sync_job(store, row["job_id"], "discovered")
                if row["action"] == "email_trash" and outcome == "confirmed":
                    store.conn.execute("UPDATE wf_messages SET status='trashed', trashed_at=?, updated_at=? WHERE message_row=?", (_stamp(checked), _stamp(now), row["message_row"]))
            return self._action_view(store.conn.execute("SELECT * FROM wf_actions WHERE id=?", (action_id,)).fetchone())

    @staticmethod
    def _action_view(row):
        keys = ("id", "action", "status", "owner", "generation", "job_id", "step_id", "message_row", "profile_version", "permission", "resume_id", "resume_sha256",
                "goal_version", "authorized_at", "expires_at", "completed_at", "evidence_source", "checked_at", "reason", "resolved_by")
        view = {key: row[key] for key in keys}
        view["action_id"], view["opportunity_id"] = view.pop("id"), view.pop("job_id")
        return view

    # ----- parada e retomada -------------------------------------------------------

    def stop(self, reason: str = "Parada solicitada pelo usuário") -> dict:
        """Persiste a parada: novas autorizações e registros de resultado são recusados.

        Ações ``authorized`` abertas viram ``uncertain`` (o efeito pode ter ocorrido).
        Idempotente. Retorna ``{stopped: true, generation, stopped_at, uncertain: [ids],
        already_stopped, message}``.
        """
        reason = _text(reason, "reason", limit=300)
        store, now = self._writer(), self._now()
        with store.transaction():
            self._expire(store, now)
            control = self._control(store.conn)
            if control["stopped"]:
                return {"stopped": True, "generation": control["generation"], "stopped_at": control["stopped_at"], "uncertain": [], "already_stopped": True, "message": "A parada já estava registrada."}
            store.conn.execute("UPDATE wf_control SET stopped=1, stopped_at=?, stop_reason=?, updated_at=? WHERE id=1", (_stamp(now), reason, _stamp(now)))
            rows = store.conn.execute("SELECT * FROM wf_actions WHERE status='authorized'").fetchall()
            for row in rows:
                self._to_uncertain(store, row, "Parada registrada antes do resultado conferido; confira o destino.", "stop", now)
        return {"stopped": True, "generation": control["generation"], "stopped_at": _stamp(now), "uncertain": [row["id"] for row in rows], "already_stopped": False,
                "message": "Parada registrada. Nenhuma ação nova será autorizada até a retomada."}

    def resume(self) -> dict:
        """Retoma após ``stop()``: cria geração nova e revalida; não resolve incertezas.

        Retorna ``state()`` com ``resumed: true`` e ``uncertain: [ids]`` pendentes.
        """
        store, now = self._writer(), self._now()
        with store.transaction():
            self._expire(store, now)
            control = self._control(store.conn)
            if not control["stopped"]:
                raise ValueError("Não há parada ativa para retomar.")
            store.conn.execute("UPDATE wf_control SET generation=generation+1, stopped=0, resumed_at=?, updated_at=? WHERE id=1", (_stamp(now), _stamp(now)))
            uncertain = [row[0] for row in store.conn.execute("SELECT id FROM wf_actions WHERE status='uncertain' ORDER BY authorized_at")]
        return {**self.state(), "resumed": True, "uncertain": uncertain}

    # ----- capacidades e e-mail ----------------------------------------------------

    def capability(self, payload: dict) -> dict:
        """Registra uma observação de capacidade; disponibilidade de ferramenta não é sessão.

        Payload: ``{kind: browser|mail, provider: alias (mail: gmail|outlook), account:
        alias local (sem endereço; public = navegação sem login), status: ready|
        auth_required|unavailable|expired|revoked, checked_at: ISO com fuso (até 24 h),
        evidence: str curta, agent_provider?: provider base de IA em que foi observada
        (ex.: claude, codex; sem /modelo),
        valid_minutes?: 5..720 (padrão 60)}``. Status diferente de ready revoga a
        capacidade e torna ``uncertain`` as ações abertas que dependiam dela.
        Retorna ``{id, kind, provider, account, status, checked_at, valid_until, revoked_actions}``.
        """
        p = _fields(payload, {"kind", "provider", "account", "status", "checked_at", "evidence", "agent_provider", "valid_minutes"}, ("kind", "provider", "account", "status", "checked_at", "evidence"))
        if p["kind"] not in ("browser", "mail"):
            raise ValueError("kind: use browser ou mail")
        provider = _match(_PROVIDER, p["provider"], "provider", "alias curto em minúsculas")
        if p["kind"] == "mail" and provider not in ("gmail", "outlook"):
            raise ValueError("provider: e-mail usa gmail ou outlook")
        account = _match(_ACCOUNT, p["account"], "account", "alias local, sem endereço de e-mail")
        if p["status"] not in CAPABILITY_STATUSES:
            raise ValueError("status: use " + ", ".join(sorted(CAPABILITY_STATUSES)))
        agent = None if p.get("agent_provider") is None else _match(_PROVIDER, p["agent_provider"], "agent_provider", "alias curto em minúsculas")
        evidence = _text(p["evidence"], "evidence", limit=500)
        minutes = _int(p.get("valid_minutes", 60), "valid_minutes", 5, 720)
        now = self._now()
        checked = _moment(p["checked_at"], "checked_at")
        if checked > now + timedelta(minutes=2) or checked < now - timedelta(hours=24):
            raise ValueError("checked_at: observação no futuro ou com mais de 24 horas")
        store = self._writer()
        with store.transaction():
            self._expire(store, now)
            cursor = store.conn.execute("INSERT INTO wf_capabilities(kind,provider,account,status,checked_at,valid_until,agent_provider,evidence,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                                        (p["kind"], provider, account, p["status"], _stamp(checked), _stamp(checked + timedelta(minutes=minutes)), agent, evidence, _stamp(now)))
            revoked = []
            if p["status"] != "ready":
                rows = store.conn.execute("SELECT a.* FROM wf_actions a JOIN wf_capabilities c ON c.id=a.capability_id WHERE a.status='authorized' AND c.kind=? AND c.provider=? AND c.account=?", (p["kind"], provider, account)).fetchall()
                for row in rows:
                    self._to_uncertain(store, row, "Capacidade perdeu validade durante a ação; confira o destino.", "capability", now)
                    revoked.append(row["id"])
            row = dict(store.conn.execute("SELECT id,kind,provider,account,status,checked_at,valid_until,agent_provider FROM wf_capabilities WHERE id=?", (cursor.lastrowid,)).fetchone())
        return {**row, "revoked_actions": revoked}

    def ingest_email(self, payload: dict) -> dict:
        """Registra uma mensagem lida (sem corpo, tokens ou endereços) e seu vínculo.

        Payload: ``{provider: gmail|outlook, account: alias, message_id: str,
        category: EMAIL_CATEGORIES, received_at: ISO com fuso, summary?: str curta,
        safe_url?: URL https pública, opportunity_id?: int, link_evidence?: str
        (obrigatória com opportunity_id), step_key?: str (obrigatória em interview/
        assessment vinculados), step_kind?: str (padrão = category), due_at?: ISO}``.
        Duplicata idêntica é idempotente; categoria divergente é recusada.
        Retorna ``{message_row, provider, account, message_id, category, status,
        duplicate, link_pending, opportunity_id, step_id}``.
        """
        p = _fields(payload, {"provider", "account", "message_id", "category", "received_at", "summary", "safe_url", "opportunity_id", "link_evidence", "step_key", "step_kind", "due_at"}, ("provider", "account", "message_id", "category", "received_at"))
        if p["category"] not in EMAIL_CATEGORIES:
            raise ValueError("category: use " + ", ".join(sorted(EMAIL_CATEGORIES)))
        now = self._now()
        received = _moment(p["received_at"], "received_at")
        if received > now + timedelta(minutes=2):
            raise ValueError("received_at: data no futuro")
        job_id = p.get("opportunity_id")
        if job_id is not None and not p.get("link_evidence"):
            raise ValueError("link_evidence: vínculo com oportunidade exige prova")
        if p.get("step_key") is not None and job_id is None:
            raise ValueError("step_key: etapa exige oportunidade vinculada")
        if p["category"] in ("interview", "assessment") and job_id is not None and p.get("step_key") is None:
            raise ValueError("step_key: entrevista ou avaliação vinculada vira etapa individual")
        store_payload = {key: p[key] for key in ("provider", "account", "message_id", "summary", "safe_url", "link_evidence", "step_key", "due_at") if p.get(key) is not None}
        if job_id is not None:
            store_payload["job_id"] = job_id
        if p.get("step_key") is not None:
            store_payload["kind"] = p.get("step_kind") or p["category"]
        store = self._writer()
        with store.transaction():
            message = store.ingest_message(store_payload)
            existing = store.conn.execute("SELECT * FROM wf_messages WHERE message_row=?", (message["id"],)).fetchone()
            if existing and existing["category"] != p["category"]:
                raise ValueError("category: mensagem já registrada com outra categoria")
            if existing is None:
                store.conn.execute("INSERT INTO wf_messages(message_row,category,received_at,link_evidence,status,updated_at) VALUES(?,?,?,?,?,?)",
                                   (message["id"], p["category"], _stamp(received), _text(p.get("link_evidence"), "link_evidence", optional=True), "active", _stamp(now)))
            status = store.conn.execute("SELECT status FROM wf_messages WHERE message_row=?", (message["id"],)).fetchone()[0]
        return {"message_row": message["id"], "provider": message["provider"], "account": message["account"], "message_id": message["message_id"],
                "category": p["category"], "status": status, "duplicate": message["duplicate"], "link_pending": message["link_pending"],
                "opportunity_id": message["job_id"], "step_id": message["step_id"]}

    def cleanup_rules(self, payload: dict | None = None) -> dict:
        """Categorias de e-mail que o usuário autorizou explicitamente para lixeira.

        Sem payload, apenas consulta. Payload: ``{categories: [subconjunto de
        CLEANABLE_CATEGORIES], user_confirmation: str}``. Interview, assessment,
        offer e mensagens de processo sem vínculo nunca entram. Retorna
        ``{version, categories, created_at}`` (version 0 = nenhuma regra).
        """
        if payload is None:
            with self._read() as store:
                conn = store.conn if store else None
                if conn is None or "wf_cleanup_rules" not in _tables(conn):
                    return {"version": 0, "categories": [], "created_at": None}
                row = conn.execute("SELECT * FROM wf_cleanup_rules ORDER BY version DESC LIMIT 1").fetchone()
                return {"version": row["version"], "categories": json.loads(row["categories"]), "created_at": row["created_at"]} if row else {"version": 0, "categories": [], "created_at": None}
        p = _fields(payload, {"categories", "user_confirmation"}, ("categories", "user_confirmation"))
        categories = p["categories"]
        if not isinstance(categories, list) or len(set(categories)) != len(categories) or set(categories) - CLEANABLE_CATEGORIES:
            raise ValueError("categories: use apenas " + ", ".join(sorted(CLEANABLE_CATEGORIES)))
        confirmation = _text(p["user_confirmation"], "user_confirmation", limit=500)
        store, now = self._writer(), self._now()
        with store.transaction():
            version = (store.conn.execute("SELECT MAX(version) FROM wf_cleanup_rules").fetchone()[0] or 0) + 1
            store.conn.execute("INSERT INTO wf_cleanup_rules VALUES(?,?,?,?)", (version, json.dumps(sorted(categories)), confirmation, _stamp(now)))
        return {"version": version, "categories": sorted(categories), "created_at": _stamp(now)}
