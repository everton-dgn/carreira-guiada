"""Local queue and search coverage for the chat coordinator."""
import json
from .profile import Profile
from .workflow import Workflow, _fields
from scripts.candidaturas.store import _text, _instant, _stamp


def coverage(root, data=None):
    """Read or append source coverage. Complete means this query, not all vacancies.

    Write payload: source, query, pages (nonnegative integer), status
    (complete|partial|unavailable), checked_at (ISO with zone), next_action,
    optional position (safe short description, never a token/session cursor).
    """
    profile = Profile(root)
    with profile._db(write=data is not None) as db:
        if db is None:
            return []
        if data is None:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='job_search_coverage'").fetchone():
                return []
            return [json.loads(r[0]) for r in db.execute("SELECT payload FROM job_search_coverage ORDER BY id")]
        data = dict(_fields(data, {"source", "query", "pages", "status", "checked_at", "next_action", "position"},
                            ("source", "query", "pages", "status", "checked_at", "next_action")))
        if type(data["pages"]) is not int or data["pages"] < 0:
            raise ValueError("Informe quantas páginas foram realmente conferidas.")
        if data["status"] not in {"complete", "partial", "unavailable"}:
            raise ValueError("Informe se a consulta foi completa, parcial ou indisponível.")
        if data["status"] == "complete" and data["pages"] < 1:
            raise ValueError("Uma consulta completa exige conferir ao menos a página de resultados.")
        for key in ("source", "query", "next_action", "position"):
            if key in data:
                data[key] = _text(data[key], key, limit=500)
        checked = _instant(data["checked_at"], "checked_at")
        if checked > _instant():
            raise ValueError("A consulta não pode ter data no futuro.")
        data["checked_at"] = _stamp(checked)
        db.execute("CREATE TABLE IF NOT EXISTS job_search_coverage (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        cursor = db.execute("INSERT INTO job_search_coverage(payload) VALUES(?)", (json.dumps(data, ensure_ascii=False),))
        return {"id": cursor.lastrowid, **data}


def ledger(root, command, data=None):
    """Queue maintenance. External effects must still use Workflow.authorize/complete."""
    workflow = Workflow(root)
    try:
        if command in {"jobs", "steps"}:
            with workflow._read() as store:
                return [] if store is None else getattr(store, "list_" + command)()
        store = workflow._writer()
        if command == "step":
            return store.upsert_step(data)
        if command == "transition":
            data = _fields(data, {"id", "state", "evidence", "user_confirmation"}, ("id", "state", "evidence"))
            if data['state'] == 'completed':
                with store.transaction():
                    step = store._step(data['id'])
                    if step['state'] != 'candidate_pending':
                        raise ValueError('Somente uma etapa que dependia da pessoa pode ser concluída por seu relato.')
                    confirmation = _text(data.get('user_confirmation'), 'user_confirmation', limit=400)
                    evidence = _text(data['evidence'], 'evidence', limit=400)
                    return store.transition_step(data['id'], 'completed', evidence=evidence + ' Relato da pessoa: ' + confirmation)
            if data["state"] not in {"pending", "candidate_pending", "blocked", "cancelled"}:
                raise ValueError("Resultado de efeito externo exige action complete; aqui só registre pendências ou cancelamento.")
            return store.transition_step(data["id"], data["state"], evidence=data["evidence"])
        raise ValueError("Comando de registro desconhecido.")
    finally:
        workflow.close()


def mail_coverage(root, action, data=None):
    """Expose the inherited mail monitor without a second database."""
    from scripts.candidaturas.monitor import Monitor
    workflow = Workflow(root)
    monitor = None
    try:
        if action == "show":
            workflow._check_private()
            monitor = Monitor.readonly(workflow.db_path)
            return monitor.status() if monitor else {"accounts": [], "runs": []}
        workflow._writer()
        monitor = Monitor(workflow.db_path)
        if action == "begin":
            data = _fields(data, {"minutes"})
            minutes = data.get("minutes", 30)
            if type(minutes) is not int:
                raise ValueError("Duração da consulta precisa ser um número inteiro de minutos.")
            return monitor.begin(minutes)
        if action == "account":
            data = _fields(data, {"run_id", "provider", "account", "status", "note", "window_start", "window_end", "query"},
                           ("run_id", "provider", "account", "status"))
            return monitor.account(**data)
        data = _fields(data, {"run_id", "note"}, ("run_id",))
        return monitor.finish(**data)
    finally:
        if monitor:
            monitor.db.close()
        workflow.close()
