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
    start = command("start", "Ver o próximo passo do início guiado, sem iniciar envios")
    start.add_argument('--focus', choices=('prepare', 'search', 'practice', 'career', 'company'), default='prepare', help='Escolher preparo, busca, treino, guia de carreira ou pesquisa de empresa')
    command("status", "Conferir o progresso e as pendências")
    command("context", "Ler o contexto privado para o agente responsável")
    command("doctor", "Conferir requisitos e capacidades observadas")
    presence = command('presence', 'Preparar a revisão opcional do LinkedIn e GitHub')
    presence.add_argument('action', choices=('show', 'status', 'choose', 'source', 'draft', 'finish'))
    practice = command('practice', 'Treinar entrevistas em particular, sem candidaturas ou contas reais')
    practice.add_argument('action', choices=('catalog', 'show', 'status', 'choose', 'start', 'hint', 'answer', 'skip', 'feedback', 'advance', 'end-questions', 'finish'))
    diligence = command('research', 'Registrar análises verificadas de fontes, empresas e vagas')
    diligence.add_argument('action', choices=('save', 'list', 'get', 'suggestions'))
    scopes = command('research-scope', 'Combinar e conferir o alcance de uma pesquisa pública específica')
    scopes.add_argument('action', choices=('grant', 'get', 'list', 'check', 'revoke'))
    company = command('company', 'Guardar um dossiê privado de empresa, com fontes e dúvidas')
    company.add_argument('action', choices=('create', 'get', 'list', 'revise', 'summary'))
    career = command('career', 'Explorar caminhos profissionais e guardar um próximo passo')
    career.add_argument('action', choices=('start', 'get', 'status', 'answer', 'propose', 'choose', 'experiment', 'reflect', 'pause', 'resume'))
    offers = command('offers', 'Comparar propostas com premissas explícitas, sem aceitar ofertas')
    offers.add_argument('action', choices=('save', 'list', 'get', 'status', 'compare', 'equivalent'))
    tabs = command('tabs', 'Controlar o limite compartilhado de abas de trabalho')
    tabs.add_argument('action', choices=('status', 'reserve', 'update', 'release'))
    saved = command('checkpoint', 'Guardar o último progresso e a próxima ação para outra sessão')
    saved.add_argument('action', choices=('show', 'save'))
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
    for name in ("list", "sources", "facts", "fact", "draft", "fact-revoke", "fact-replace"):
        subs.add_parser(name, parents=[common])
    imp = subs.add_parser("import", parents=[common])
    imp.add_argument("--file", type=Path, help="Compatibilidade: prefira file e label por JSON via stdin")
    imp.add_argument("--label")
    approve = subs.add_parser("approve", parents=[common])
    approve.add_argument("id")
    for name in ('show', 'check'):
        show = subs.add_parser(name, parents=[common])
        show.add_argument("id")
    for name, help_text in (
        ("goal", "Registrar o objetivo autorizado, JSON via stdin"),
        ("goal-extend", "Adicionar ações ao objetivo ativo, JSON via stdin"),
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
    check = subs.add_parser("check", parents=[common])
    check.add_argument("id")
    show = subs.add_parser("show", parents=[common])
    show.add_argument("id")
    return main


def onboarding(root, focus='prepare'):
    from .career import CareerGuide, QUESTIONS as CAREER_QUESTIONS
    from .checkpoint import checkpoint
    from .company import CompanyDossiers
    from .profile import Profile
    career = CareerGuide(root).status()
    point = checkpoint(root)
    saved_career = career['session'] is not None and career['phase'] != 'finished'
    if focus == 'career' or (focus == 'prepare' and saved_career and (not point or point['phase'] == 'career')):
        message = career['message']
        question = career['question']
        if career['session'] is None:
            question = {'field': 'goal', 'question': CAREER_QUESTIONS['goal']}
        if question and question['question'] not in message:
            message += '\n' + question['question']
        return {'message': message, 'next_step': 'career_guidance', 'question': question,
                'career': career, 'welcome_back': 'Seu guia de carreira está salvo. Podemos continuar ou revisar suas respostas.' if career['session'] else None,
                'resume_hint': message, 'resume_options': ['continue', 'review'] if career['session'] else [],
                'automatic_execution_started': False}
    dossiers = CompanyDossiers(root).list()
    if focus == 'company' or (focus == 'prepare' and ((point and point['phase'] == 'company') or
                                                    (not point and dossiers and not Profile(root).get()['sections']))):
        message = ('Seus dossiês estão salvos. Diga qual empresa quer continuar analisando ou indique outra.' if dossiers else
                   'Qual empresa você quer conhecer e o que precisa esclarecer? Pode colar o site ou a vaga; se não tiver o link, diga o nome e o país.')
        return {'message': message, 'next_step': 'company_dossier', 'question': None,
                'companies': dossiers, 'welcome_back': 'Encontrei suas análises de empresas.' if dossiers else None,
                'resume_hint': message, 'resume_options': ['continue', 'review'] if dossiers else [],
                'automatic_execution_started': False}
    from .resumes import ResumeManager
    from .intake import Intake
    from .presence import Presence
    from .practice import Practice
    profile = Profile(root)
    status, data = profile.status(), profile.get()
    resumes = ResumeManager(root)
    intake = Intake(root).status()
    presence = Presence(root).status()
    practice = Practice(root).status()
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
    if focus == 'practice' or (focus == 'prepare' and practice['decision'] == 'now' and practice['phase'] in ('idle', 'questions', 'feedback')):
        next_step = 'interview_preparation'
        question = practice['question']
        message = practice['message']
        if question:
            message += '\n' + question['question']
    elif focus == 'search':
        if not status['approved']:
            next_step = status.get('next_section') or 'profile_approval'
            question = status['questions'][0] if status['questions'] else None
            message = question['question'] + ' ' + question['example'] if question else 'Confira o resumo dos filtros e permissões para aprovar a busca.'
        elif not data['sections'].get('sources', {}).get('urls'):
            from .profile import QUESTIONS
            field, prompt, example = QUESTIONS['sources'][0]
            example = 'Pode colar os endereços ou pedir ajuda para encontrar opções verificadas. Se preferir deixar a busca para depois, suas respostas ficam salvas.'
            next_step = 'sources'
            question = {'field': field, 'question': prompt, 'example': example}
            message = prompt + ' ' + example
        else:
            next_step = 'execution_readiness'
            message = 'Seu perfil e suas fontes estão prontos para a busca. Vou conferir as ferramentas; o currículo pode ficar para depois. Nenhum envio foi autorizado por esta consulta.'
    elif not data.get("sections") and not resumes.sources() and not resumes.facts() and not intake["mode"]:
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
    elif presence['decision'] is None:
        next_step = 'professional_presence'
        message = 'Quer revisar também sua apresentação no LinkedIn ou, se fizer sentido para sua área, no GitHub? Podemos fazer agora, deixar para depois ou pular.'
    elif presence['next_topic']:
        next_step = 'professional_presence'
        message = 'Vamos continuar a revisão do ' + ('LinkedIn' if presence['next_topic'] == 'linkedin' else 'GitHub') + '. As sugestões ficam salvas; nada é publicado por esta consulta.'
    elif practice['decision'] is None:
        next_step = 'interview_preparation'
        message = 'Quer treinar para as entrevistas? Posso ajudar na conversa com RH, na apresentação da sua trajetória ou na parte técnica. Podemos treinar agora, deixar para depois ou pular.'
    elif not data.get('sections', {}).get('sources', {}).get('urls'):
        from .profile import QUESTIONS
        field, prompt, example = QUESTIONS['sources'][0]
        example = 'Pode colar os endereços ou pedir ajuda para encontrar opções verificadas. Se quiser somente o currículo e os perfis por enquanto, podemos deixar a busca para depois.'
        question = {'field': field, 'question': prompt, 'example': example}
        next_step = 'sources'
        message = 'Seu currículo está pronto. Para começar a busca, precisamos combinar os sites. ' + prompt + ' ' + example
    else:
        message = "Seu perfil e currículo estão prontos. Vou conferir o acesso aos sites para seguir com o que combinamos. Se precisar de login, eu abro a página e explico o próximo passo."
        next_step = "execution_readiness"
    from .checkpoint import checkpoint
    from .offers import Offers
    from .due_diligence import DueDiligence
    additional_progress = bool(checkpoint(root) or Offers(root).status()['count'] or DueDiligence(root).list())
    saved = bool(data.get('sections') or intake['mode'] or versions or presence['decision'] or practice['decision'] or resumes.sources() or resumes.facts() or additional_progress)
    welcome = 'Encontrei seu progresso salvo. Quer continuar de onde parou ou revisar sua preparação? Revisar preserva as respostas e só muda o que você corrigir.' if saved else None
    if practice['decision'] in ('later', 'skip') and practice['phase'] in ('questions', 'feedback'):
        message += ' Seu treino adiado continua salvo e pode ser retomado quando quiser.'
        welcome += ' Há também um treino adiado com respostas salvas.'
    labels = {'curriculum_input': 'receber ou criar o currículo', 'curriculum_intake': 'continuar as informações profissionais',
              'identity': 'dados de contato', 'preferences': 'preferências de trabalho', 'sources': 'fontes de vagas',
              'permissions': 'permissões', 'connections': 'conexões de e-mail', 'profile_approval': 'conferir o perfil',
              'resume_approval': 'revisar o currículo', 'professional_presence': 'revisão opcional de LinkedIn e GitHub',
              'interview_preparation': 'preparação opcional para entrevistas',
              'execution_readiness': 'conferir conexões e continuar o objetivo'}
    return {"message": message, "next_step": next_step, "question": question, "profile": status,
            "intake": intake, "presence": presence, "practice": practice, "approved_resumes": approved,
            "resume_hint": ('Há análises ou um ponto de retomada salvo. Vou conferir o status antes de seguir.' if additional_progress and not data.get('sections') and practice['phase'] == 'idle' else 'Próxima etapa: ' + labels[next_step] + '.') if saved else None,
            "welcome_back": welcome, "resume_options": ['continue', 'review'] if saved else [],
            "automatic_execution_started": False}


def dispatch(args):
    root = getattr(args, "root", ROOT).resolve()
    if not root.is_dir():
        raise ValueError("A pasta do projeto não foi encontrada. Abra a pasta Carreira Guiada no seu aplicativo de IA.")
    if args.command == "start":
        return onboarding(root, args.focus)
    if args.command in ('career', 'company', 'research-scope'):
        from .career import CareerGuide
        from .company import CompanyDossiers
        from .research_scope import ResearchScopes
        service = {'career': CareerGuide, 'company': CompanyDossiers, 'research-scope': ResearchScopes}[args.command](root)
        if args.action in ('list', 'status'):
            return getattr(service, args.action)()
        data = payload()
        if args.action in ('get', 'summary'):
            key = 'scope_id' if args.command == 'research-scope' else 'id'
            optional = {'version'} if args.action == 'get' else set()
            if key not in data or set(data) - {key} - optional:
                raise ValueError('Informe o identificador do registro salvo; a IA pode consultar a lista para encontrá-lo.')
            result = getattr(service, args.action)(data[key], **({'version': data['version']} if 'version' in data else {}))
            if result is None:
                raise ValueError('Esse registro não foi encontrado. Vou conferir os registros salvos antes de continuar; nenhum dado foi alterado.')
            return result
        return getattr(service, args.action)(data)
    if args.command == 'checkpoint':
        from .checkpoint import checkpoint
        return checkpoint(root, payload() if args.action == 'save' else None)
    if args.command == 'research':
        from .due_diligence import DueDiligence
        research = DueDiligence(root)
        if args.action in ('list', 'suggestions'):
            return getattr(research, args.action)()
        data = payload()
        if args.action == 'save':
            return research.save(data)
        if set(data) != {'record_id'}:
            raise ValueError('Informe o identificador do parecer salvo.')
        result = research.get(data['record_id'])
        if result is None:
            raise ValueError('Parecer não encontrado. Consulte a lista de análises salvas.')
        return result
    if args.command == 'offers':
        from .offers import Offers
        offers = Offers(root)
        if args.action in ('list', 'status'):
            return getattr(offers, args.action)()
        data = payload()
        if args.action == 'save':
            return offers.save(data)
        required, optional = {'get': ({'offer_id'}, set()),
                              'compare': ({'ids'}, {'base_currency', 'rates'}),
                              'equivalent': ({'base_id', 'target_id'}, {'base_currency', 'rates'})}[args.action]
        if not required <= set(data) or set(data) - required - optional:
            raise ValueError('Confira os campos da comparação: ' + ', '.join(sorted(required)))
        return getattr(offers, args.action)(**data)
    if args.command == 'practice':
        from .practice import Practice
        practice = Practice(root)
        if args.action in ('catalog', 'show', 'status'):
            return practice.get() if args.action == 'show' else getattr(practice, args.action)()
        data = payload()
        fields = {'choose': ({'decision'}, set()),
                  'start': ({'track', 'mode'}, {'context', 'area', 'level', 'short', 'question_ids'}),
                  'hint': ({'session_id', 'question_id'}, set()),
                  'answer': ({'session_id', 'question_id', 'text'}, set()),
                  'skip': ({'session_id', 'question_id'}, set()),
                  'feedback': ({'session_id', 'question_id', 'version', 'strengths', 'improvements', 'suggestion', 'exercise'}, set()),
                  'advance': ({'session_id', 'question_id'}, set()),
                  'end-questions': ({'session_id'}, set()),
                  'finish': ({'session_id', 'report', 'next_steps'}, set())}
        required, optional = fields[args.action]
        if not required <= set(data) or set(data) - required - optional:
            raise ValueError('Confira os campos desta etapa do treino: ' + ', '.join(sorted(required)))
        return getattr(practice, args.action.replace('-', '_'))(**data)
    if args.command == 'presence':
        from .presence import Presence
        presence = Presence(root)
        if args.action in ('show', 'status'):
            return presence.get() if args.action == 'show' else presence.status()
        data = payload()
        fields = {'choose': {'decision', 'topics', 'confirmation'}, 'source': {'topic', 'source'}, 'draft': {'topic', 'content', 'source'},
                  'finish': {'topic', 'version', 'confirmation'}}[args.action]
        optional = {'source': {'material'}, 'draft': {'fact_ids'}}.get(args.action, set())
        if not fields <= set(data) or set(data) - fields - optional:
            raise ValueError('Informe exatamente os campos desta etapa: ' + ', '.join(sorted(fields)))
        return getattr(presence, args.action)(**data)
    if args.command == 'tabs':
        from .tabs import Tabs
        tabs = Tabs(root)
        if args.action == 'status':
            return tabs.status()
        data = payload()
        fields = {'reserve': {'owner', 'purpose', 'owned'},
                  'update': {'reservation', 'external_id', 'protected', 'evidence'},
                  'release': {'reservation', 'outcome', 'evidence'}}[args.action]
        if set(data) != fields:
            raise ValueError('Informe exatamente os campos desta etapa: ' + ', '.join(sorted(fields)))
        return getattr(tabs, args.action)(**data)
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
            if args.file is not None:
                return resumes.import_file(args.file, args.label)
            data = payload()
            if set(data) != {'file', 'label'} or not isinstance(data['file'], str) or not data['file'].strip():
                raise ValueError('Importação: informe file e label por JSON via stdin.')
            if args.label is not None:
                raise ValueError('Importação: use label no mesmo JSON do arquivo.')
            return resumes.import_file(Path(data['file']), data['label'])
        if args.action == 'check':
            return resumes.check(args.id)
        if args.action == "fact":
            data = payload()
            return resumes.add_fact(data.get("text"), data.get("source"), data.get("confirmed"))
        if args.action == "draft":
            data = payload()
            return resumes.draft(data.get("label"), data.get("markdown"), data.get("fact_ids"))
        if args.action in {"fact-revoke", "fact-replace"}:
            data = payload()
            allowed = {"fact_id", "source", "confirmed", "reason"} | ({"text"} if args.action == "fact-replace" else set())
            if not set(data) <= allowed:
                raise ValueError("Correção de fato: use somente " + ", ".join(sorted(allowed)) + ".")
            if args.action == "fact-revoke":
                return resumes.revoke_fact(data.get("fact_id"), data.get("source"), data.get("confirmed"), data.get("reason"))
            return resumes.replace_fact(data.get("fact_id"), data.get("text"), data.get("source"), data.get("confirmed"), data.get("reason"))
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
    if args.command == "goal-extend":
        return workflow.extend_goal(payload())
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
        if args.action == 'authorize':
            return workflow.authorize(payload())
        if args.action == 'show':
            return workflow.show_action(args.id)
        return getattr(workflow, args.action)(args.id, payload())
    raise ValueError("Comando desconhecido. Peça ajuda à IA para continuar.")


def render(value):
    if isinstance(value, dict) and value.get("message"):
        if value.get('example'):
            return value['message'] + '\n' + value['example']
        if value.get('welcome_back'):
            return value['welcome_back'] + '\n' + value['resume_hint']
        if value.get('session_id') and value.get('decision') not in ('later', 'skip') and isinstance(value.get('question'), dict):
            return value['message'] + '\n' + value['question']['question']
        return value['message']
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
