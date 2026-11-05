"""Commands for the chat agent. The candidate can simply say 'iniciar'."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def payload():
    raw = sys.stdin.read(262_145)
    if len(raw) > 262_144:
        raise ValueError("A entrada excede 256 KB. Envie apenas os campos desta etapa.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("A entrada precisa ser um objeto JSON válido. Peça à IA para corrigir o comando; suas respostas anteriores foram preservadas.") from exc
    if not isinstance(value, dict):
        raise ValueError("A entrada precisa ser um objeto JSON.")
    return value


def parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=argparse.SUPPRESS, help="Pasta do projeto; a área privada fica dentro dela")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Resposta estruturada para o agente")
    main = argparse.ArgumentParser(description="Carreira Guiada: guia de candidaturas no chat", parents=[common])
    commands = main.add_subparsers(dest="command", required=True)
    def command(name, help_text):
        return commands.add_parser(name, help=help_text, parents=[common])
    command("start", "Ver o próximo passo do início guiado, sem iniciar envios")
    command("status", "Conferir o progresso e as pendências")
    command("context", "Ler o contexto privado para o agente responsável")
    command("doctor", "Conferir requisitos e capacidades observadas")
    for name in ("jobs", "steps", "step", "transition"):
        command(name, "Consultar ou registrar oportunidades e etapas")
    for name in ("coverage", "cleanup-rules"):
        item = command(name, "Consultar ou salvar regras e cobertura local")
        item.add_argument("action", choices=["show", "save"])
    item = command("mail-coverage", "Registrar a cobertura das consultas de e-mail")
    item.add_argument("action", choices=["show", "begin", "account", "finish"])
    profile = command("profile", "Salvar e confirmar respostas do onboarding")
    subs = profile.add_subparsers(dest="action", required=True)
    subs.add_parser("show", parents=[common])
    subs.add_parser("status", parents=[common])
    answer = subs.add_parser("answer", parents=[common])
    answer.add_argument("section", choices=["identity", "preferences", "sources", "permissions", "connections"])
    save = subs.add_parser("save", parents=[common])
    save.add_argument("section", choices=["identity", "preferences", "sources", "permissions", "limits", "connections"])
    approve = subs.add_parser("approve", parents=[common])
    approve.add_argument("--version", type=int, required=True)
    intake = command("intake", "Guardar as respostas da preparação do currículo")
    subs = intake.add_subparsers(dest="action", required=True)
    for name in ("show", "status", "choose", "answer"):
        subs.add_parser(name, parents=[common])
    command("evaluate", "Conferir uma vaga contra os filtros do perfil, JSON via stdin")
    resume = command("resume", "Importar, preparar e aprovar currículos")
    subs = resume.add_subparsers(dest="action", required=True)
    for name in ("list", "sources", "facts", "fact", "draft"):
        subs.add_parser(name, parents=[common])
    imp = subs.add_parser("import", parents=[common])
    imp.add_argument("--file", type=Path, required=True)
    imp.add_argument("--label", required=True)
    approve = subs.add_parser("approve", parents=[common])
    approve.add_argument("id")
    show = subs.add_parser("show", parents=[common])
    show.add_argument("id")
    for name, help_text in (
        ("goal", "Registrar o objetivo autorizado, JSON via stdin"),
        ("opportunity", "Registrar uma oportunidade, JSON via stdin"),
        ("decision", "Registrar uma decisão da pessoa somente para uma vaga"),
        ("capability", "Registrar uma capacidade verificada, JSON via stdin"),
        ("email", "Vincular uma mensagem e sua etapa, JSON via stdin"),
        ("stop", "Persistir a parada e impedir novas ações"),
        ("resume-work", "Retomar explicitamente, preservando resultados incertos"),
    ):
        command(name, help_text)
    action = command("action", "Registrar autorização e resultado de uma ação")
    subs = action.add_subparsers(dest="action", required=True)
    subs.add_parser("authorize", parents=[common])
    complete = subs.add_parser("complete", parents=[common])
    complete.add_argument("id")
    return main


def onboarding(root):
    from .profile import Profile
    from .resumes import ResumeManager
    from .intake import Intake
    profile = Profile(root)
    status, data = profile.status(), profile.get()
    resumes = ResumeManager(root)
    intake = Intake(root).status()
    question = None
    versions = resumes.list()
    approved = []
    for version in versions:
        if version["status"] == "approved":
            try:
                resumes.get(version["id"])
                approved.append(version["id"])
            except ValueError:
                pass
    if not data.get("sections") and not resumes.sources() and not resumes.facts() and not intake["mode"]:
        message = "Vamos preparar sua busca, uma etapa por vez. Você já tem um currículo? Anexe o arquivo no chat. Se ainda não tiver, diga 'quero criar meu currículo' e eu ajudo a montar."
        next_step = "curriculum_input"
    elif status['next_section'] == 'identity':
        next_step = 'identity'
        question = status['questions'][0]
        message = question['question'] + ' ' + question['example']
    elif intake['mode'] == 'create' and not intake['complete']:
        next_step = 'curriculum_intake'
        question = intake['question']
        message = question['question'] + ' ' + question['example']
    elif intake['mode'] == 'import' and not resumes.sources():
        next_step = 'curriculum_input'
        message = 'Anexe seu currículo aqui no chat, em PDF ou Word. Se não conseguir anexar, pode colar o texto e eu ajudo.'
    elif not status["approved"]:
        next_step = status.get("next_section") or "profile_approval"
        question = status['questions'][0] if status['questions'] else None
        message = question['question'] + ' ' + question['example'] if question else 'Vamos conferir o resumo do seu perfil. Você pode corrigir qualquer resposta antes de aprovar.'
    elif not approved:
        message = "Seu perfil foi confirmado. Agora vamos revisar o currículo juntos e aprovar a versão que será enviada."
        next_step = "resume_approval"
    elif not data.get('sections', {}).get('sources', {}).get('urls'):
        from .profile import QUESTIONS
        field, prompt, example = QUESTIONS['sources'][0]
        question = {'field': field, 'question': prompt, 'example': example}
        next_step = 'sources'
        message = 'Seu currículo está pronto. Para começar a busca, precisamos combinar os sites. ' + prompt + ' ' + example
    else:
        message = "Seu perfil e currículo estão prontos. Vou conferir o acesso aos sites para seguir com o que combinamos. Se precisar de login, eu abro a página e explico o próximo passo."
        next_step = "execution_readiness"
    return {"message": message, "next_step": next_step, "question": question, "profile": status,
            "intake": intake, "approved_resumes": approved, "automatic_execution_started": False}


def dispatch(args):
    root = getattr(args, "root", ROOT).resolve()
    if not root.is_dir():
        raise ValueError("A pasta do projeto não foi encontrada. Abra a pasta Carreira Guiada no seu aplicativo de IA.")
    if args.command == "start":
        return onboarding(root)
    if args.command in {"jobs", "steps", "step", "transition"}:
        from .records import ledger
        return ledger(root, args.command, payload() if args.command in {"step", "transition"} else None)
    if args.command == "coverage":
        from .records import coverage
        return coverage(root, payload() if args.action == "save" else None)
    if args.command == "mail-coverage":
        from .records import mail_coverage
        return mail_coverage(root, args.action, None if args.action == "show" else payload())
    if args.command == "profile":
        from .profile import Profile
        profile = Profile(root)
        if args.action == "show":
            return profile.get()
        if args.action == "status":
            return profile.status()
        if args.action == "save":
            return profile.save(args.section, payload())
        if args.action == "answer":
            data = payload()
            return profile.answer(args.section, data.get('field'), data.get('value'), confirmed=data.get('confirmed', False))
        return profile.approve(args.version)
    if args.command == "intake":
        from .intake import Intake
        intake = Intake(root)
        if args.action in {'show', 'status'}:
            return intake.get() if args.action == 'show' else intake.status()
        data = payload()
        return intake.choose(data.get('mode')) if args.action == 'choose' else intake.answer(data.get('field'), data.get('text'))
    if args.command == "evaluate":
        from .policy import evaluate
        from .profile import Profile
        data = payload()
        vacancy = data.get("vacancy", data)
        preferences = Profile(root).get().get("sections", {}).get("preferences", {})
        return evaluate(preferences, vacancy)
    if args.command == "resume":
        from .resumes import ResumeManager
        resumes = ResumeManager(root)
        if args.action in {"list", "sources", "facts"}:
            return getattr(resumes, args.action)()
        if args.action == "import":
            return resumes.import_file(args.file, args.label)
        if args.action == "fact":
            data = payload()
            return resumes.add_fact(data.get("text"), data.get("source"), data.get("confirmed"))
        if args.action == "draft":
            data = payload()
            return resumes.draft(data.get("label"), data.get("markdown"), data.get("fact_ids"))
        if args.action == "show":
            return resumes.get(args.id)
        return resumes.approve(args.id)
    if args.command == "doctor":
        from .doctor import doctor
        return doctor(root)
    from .workflow import Workflow
    workflow = Workflow(root)
    try:
        return dispatch_workflow(workflow, root, args)
    finally:
        workflow.close()


def dispatch_workflow(workflow, root, args):
    if args.command == "cleanup-rules":
        return workflow.cleanup_rules(payload() if args.action == "save" else None)
    if args.command == "status":
        return workflow.state()
    if args.command == "context":
        from .profile import Profile
        from .resumes import ResumeManager
        return {"profile": Profile(root).get(), "resumes": ResumeManager(root).list(), "workflow": workflow.state(), "notice": "Contexto privado. Compartilhe somente os campos necessários com o destino autorizado. O piso salarial não é a pretensão."}
    if args.command == "goal":
        return workflow.configure_goal(payload())
    if args.command == "opportunity":
        return workflow.opportunity(payload())
    if args.command == 'decision':
        return workflow.decide_opportunity(payload())
    if args.command == "capability":
        return workflow.capability(payload())
    if args.command == "email":
        return workflow.ingest_email(payload())
    if args.command == "stop":
        return workflow.stop()
    if args.command == "resume-work":
        return workflow.resume()
    if args.command == "action":
        return workflow.authorize(payload()) if args.action == "authorize" else workflow.complete(args.id, payload())
    raise ValueError("Comando desconhecido. Peça ajuda à IA para continuar.")


def render(value):
    if isinstance(value, dict) and value.get("message"):
        return value["message"]
    return json.dumps(value, ensure_ascii=False, indent=2)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = dispatch(args)
    except (ValueError, OSError, sqlite3.Error, ImportError) as exc:
        message = str(exc)
        if isinstance(exc, ImportError):
            message = "Falta uma dependência do projeto. Peça à IA para verificar o ambiente com uv sync e continuar."
        if getattr(args, "json", False):
            print(json.dumps({"error": message}, ensure_ascii=False))
        else:
            print(message, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2) if getattr(args, "json", False) else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
