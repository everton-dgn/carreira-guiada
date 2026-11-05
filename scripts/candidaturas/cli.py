"""Local commands. The active chat agent uses authenticated browser tools."""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from .monitor import Monitor
from .registry import read_workspace, render_report
from .store import Store

ROOT = Path(__file__).resolve().parents[2]


def payload():
    raw = sys.stdin.read(100_001)
    if len(raw) > 100_000:
        raise ValueError("Entrada excede 100 KB.")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("A entrada precisa ser um objeto JSON.")
    return result


def parser():
    p = argparse.ArgumentParser(description="Contagem, etapas e retomada de candidaturas")
    p.add_argument("--root", type=Path, default=ROOT, help="Diretório dos três registros Markdown")
    p.add_argument("--db", type=Path, help="Banco alternativo, útil para testes isolados")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="Importar registros sem modificar os Markdown")
    report = commands.add_parser("report", help="Totais e ressalvas")
    report.add_argument("--since")
    report.add_argument("--until")
    report.add_argument("--markdown", action="store_true")
    jobs = commands.add_parser("jobs", help="Listar oportunidades locais")
    jobs.add_argument("--search", default="")
    jobs.add_argument("--all", action="store_true", help="Incluir versões históricas sem fonte ativa")
    commands.add_parser("steps", help="Listar etapas, inclusive resolvidas")
    commands.add_parser("step", help="Criar ou atualizar etapa com JSON no stdin")
    commands.add_parser("message", help="Registrar mensagem observada pelo navegador, JSON no stdin")
    transition = commands.add_parser("transition", help="Transição explícita de etapa")
    transition.add_argument("id", type=int)
    transition.add_argument("state")
    transition.add_argument("--owner")
    transition.add_argument("--evidence")
    claim = commands.add_parser("claim", help="Reservar uma etapa para um responsável")
    claim.add_argument("id", type=int)
    claim.add_argument("owner")
    claim.add_argument("--seconds", type=int, default=300)
    commands.add_parser("recover", help="Recuperar reservas vencidas sem repetir ações externas")
    monitor = commands.add_parser("monitor", help="Controle persistente da cobertura das consultas de e-mail")
    monitor.add_argument("action", choices=["begin", "account", "finish", "status"])
    monitor.add_argument("--run-id")
    return p


def run(args):
    root = args.root.resolve()
    path = args.db or root / ".job" / "control.sqlite3"
    store = Store(path)
    if args.command == "sync":
        records, warnings = read_workspace(root)
        if any("leitura indisponível" in warning for warning in warnings):
            raise ValueError("Importação incompleta: preservei o estado anterior; confira os três registros Markdown.")
        result = store.import_snapshot(records, "workspace-markdown")
        result.pop("job_ids", None)
        return {"import": result, "warnings": warnings, "summary": store.summary()}
    if args.command == "report":
        summary = store.summary(since=args.since, until=args.until)
        coverage = Monitor(path).status()
        if args.markdown:
            return render_report(summary, [j for j in store.list_jobs() if j.get("active", True)], store.list_steps()) + "\n\nCobertura do monitor:\n\n```json\n" + json.dumps(coverage, ensure_ascii=False, indent=2) + "\n```\n"
        return {"summary": summary, "monitor": coverage}
    if args.command == "jobs":
        term = args.search.casefold()
        return [j for j in store.list_jobs() if (args.all or j.get("active", True)) and term in (str(j.get("company", "")) + " " + str(j.get("title", "")) + " " + str(j.get("aliases", ""))).casefold()]
    if args.command == "steps":
        return store.list_steps()
    if args.command == "step":
        return store.upsert_step(payload())
    if args.command == "message":
        return store.ingest_message(payload())
    if args.command == "transition":
        return store.transition_step(args.id, args.state, evidence=args.evidence, owner=args.owner)
    if args.command == "claim":
        return store.claim_step(args.id, args.owner, lease_seconds=args.seconds)
    if args.command == "recover":
        return store.recover()
    if args.command == "monitor":
        monitor = Monitor(path)
        if args.action == "begin":
            return monitor.begin()
        if args.action == "status":
            return monitor.status()
        if not args.run_id:
            raise ValueError("Informe --run-id da rodada adquirida.")
        if args.action == "account":
            return monitor.account(args.run_id, **payload())
        return monitor.finish(args.run_id)
    raise ValueError("Comando não reconhecido.")


def main():
    os.umask(0o077)
    try:
        result = run(parser().parse_args())
        print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error, TypeError) as error:
        # Do not echo input payloads, account credentials or SQLite statements.
        message = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else "Operação recusada; confira campos, estado, permissões e disponibilidade do banco."
        print(json.dumps({"error": type(error).__name__, "message": message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
