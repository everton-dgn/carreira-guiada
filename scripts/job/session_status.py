"""Read-only presentation of saved work, never a claim of live execution."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .checkpoint import DEPENDENCIES, activity_of, checkpoints
from .intake import Intake
from .profile import Profile
from .resumes import ResumeManager

LABELS = {'menu': 'Escolher uma atividade', 'prepare': 'Preparo completo',
          'curriculum': 'Currículo', 'practice': 'Entrevistas', 'career': 'Guia de carreira',
          'search': 'Busca e candidaturas', 'company': 'Análise de empresa',
          'presence': 'LinkedIn e GitHub', 'offers': 'Comparação de propostas', 'models': 'Escolha de modelos'}
HELP = 'Pode pedir "andamento", "o que precisa de mim", "detalhes", "menu" ou "parar".'
ACTION_LABELS = {'research': 'pesquisa', 'register': 'cadastro', 'fill': 'preenchimento',
                 'apply': 'candidatura', 'email_read': 'consulta de e-mail', 'email_reply': 'resposta por e-mail',
                 'email_trash': 'organização de e-mail', 'schedule': 'agendamento', 'assessment': 'avaliação'}


def moment(value):
    """Parse a dated observation only when its timezone is explicit."""
    try:
        result = datetime.fromisoformat(value)
        return result if result.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def display_time(value, zone, now):
    """Show a local, dated observation; its age does not prove activity."""
    date = moment(value)
    if date is None:
        return 'horário não informado'
    try:
        tz = ZoneInfo(zone) if zone else timezone.utc
        label = zone or 'UTC'
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        tz, label = timezone.utc, 'UTC'
    local = date.astimezone(tz)
    delta = (now - date).total_seconds()
    age = f'; há {int(delta // 60)} min' if 60 <= delta < 3600 else f'; há {int(delta // 3600)} h' if 3600 <= delta < 86400 else ''
    return local.strftime('%d/%m/%Y às %H:%M') + f' ({label})' + age


def short_reference(value):
    """Keep names on one line as quoted context, not free-form next actions."""
    return ' '.join(str(value or '').split())[:120]


def selected_activity(root, state, focus=None, start=None):
    """Prefer explicit focus, then saved route, then the existing entry-point fallback."""
    if focus is not None:
        if focus not in LABELS:
            raise ValueError('Atividade desconhecida para consultar o andamento.')
        return focus
    try:
        route = Intake(root).get().get('route')
    except (ValueError, TypeError, AttributeError):
        route = None
        state['optional_data_issues'].append({'area': 'intake', 'message':
            'As respostas de preparação precisam de reparo. Os registros foram preservados; confira uma cópia privada antes de corrigir.'})
    if route == 'prepare' and state['profile'].get('approved') and state.get('goal'):
        return 'search'
    if route in LABELS and (route != 'prepare' or not start):
        return route
    if start:
        inferred = {'career_guidance': 'career', 'company_dossier': 'company',
                    'interview_preparation': 'practice', 'offers': 'offers',
                    'model_preferences': 'models', 'professional_presence': 'presence',
                    'resume_approval': 'curriculum', 'curriculum_input': 'curriculum',
                    'curriculum_intake': 'curriculum', 'curriculum_complete': 'curriculum',
                    'identity': 'prepare', 'preferences': 'prepare', 'permissions': 'prepare',
                    'connections': 'prepare', 'profile_approval': 'prepare',
                    'sources': 'search', 'execution_readiness': 'search'}.get(start.get('next_step'))
        if inferred:
            return inferred
        if start.get('menu') and start['message'] == start['menu']['message']:
            return 'menu'
    point = state.get('checkpoint')
    career = state.get('career') or {}
    if career.get('session') and not career.get('paused') and career.get('phase') != 'finished' and (not point or point['phase'] == 'career'):
        return 'career'
    if point and activity_of(point) in {'company', 'presence', 'offers', 'curriculum'}:
        return activity_of(point)
    if state.get('companies') and not state.get('goal') and state['profile'].get('version') == 0:
        return 'company'
    practice = state.get('practice') or {}
    if practice.get('decision') == 'now' and practice.get('phase') in {'idle', 'questions', 'feedback'}:
        return 'practice'
    if state.get('goal'):
        return 'search'
    if not state['initialized'] and not point and not state['profile'].get('version'):
        return 'menu'
    return 'prepare'


def _activity(root, state, activity):
    """Build the activity's next step from domain records, without executing it."""
    result = {'phase': 'ready', 'condition': 'ready', 'advance': None,
              'next_action': 'Escolha o próximo passo com a IA.', 'needs_user': False}
    if activity == 'menu':
        result.update(condition='waiting_user', needs_user=True, next_action='Escolha currículo, entrevistas, carreira ou busca de vagas no menu.')
    elif activity == 'curriculum':
        intake = Intake(root).status()
        versions = ResumeManager(root).list()
        approved = []
        for version in versions:
            if version['status'] == 'approved':
                try:
                    ResumeManager(root).get(version['id'])
                    approved.append(version)
                except ValueError:
                    pass
        if approved:
            result.update(phase='approved', condition='completed', advance='Há uma versão aprovada e conferida do currículo.', next_action='Você pode revisar o currículo ou escolher outra atividade.')
        elif intake['question']:
            result.update(phase=intake['question']['field'], condition='waiting_user', needs_user=True,
                          advance=f"{5 - len(intake['questions'])} de 5 respostas profissionais registradas (incluindo escolhas de pular).",
                          next_action=intake['question']['question'])
        elif intake['complete'] or versions or ResumeManager(root).sources():
            result.update(phase='review', next_action='Vamos preparar ou revisar a versão com os fatos confirmados antes de pedir sua aprovação.')
        else:
            result.update(phase='input', condition='waiting_user', needs_user=True,
                          next_action='Anexe seu currículo ou diga que quer criar um.')
    elif activity == 'practice':
        practice = state['practice']
        result.update(phase=practice['phase'])
        if practice['phase'] == 'finished':
            result.update(condition='completed', advance='O treino tem um fechamento salvo.', next_action='Você pode consultar o feedback ou escolher outro treino.')
        elif practice.get('decision') in {'later', 'skip'}:
            result.update(condition='paused', next_action='Diga "continuar meu treino" para retomar a atividade salva.')
        elif practice.get('next_step') == 'answer' and practice.get('question'):
            result.update(condition='waiting_user', needs_user=True, next_action=practice['question']['question'],
                          advance=f"Pergunta {practice['position']} de {practice['total']} do treino salvo.")
        elif practice.get('next_step') in {'feedback', 'advance', 'finish'}:
            result.update(advance='Sua resposta continua salva.', next_action=practice['message'])
        else:
            result.update(condition='waiting_user', needs_user=True, advance='Há um treino salvo; falta escolher o tema.' if practice.get('decision') == 'now' else None,
                          next_action='Escolha um tema de entrevista ou peça ajuda para começar.')
    elif activity == 'career':
        career = state.get('career') or {}
        result.update(phase=career.get('phase', 'idle'))
        if career.get('paused'):
            result.update(condition='paused', next_action='Diga "continuar meu guia de carreira" para retomar.')
        elif career.get('phase') == 'finished':
            result.update(condition='completed', advance='Sua reflexão e a decisão de próximo passo estão salvas.', next_action='Consulte o que aprendeu ou explore outro caminho.')
        elif career.get('question'):
            result.update(condition='waiting_user', needs_user=True, advance='Suas respostas anteriores estão salvas; seguimos uma pergunta por vez.' if career.get('session') else None,
                          next_action=career['question']['question'])
        else:
            result.update(condition='waiting_user' if not career.get('session') else 'ready', needs_user=not career.get('session'),
                          next_action=career.get('message') or 'Conte o que quer decidir sobre sua carreira.')
    elif activity == 'search':
        if state['control']['stopped']:
            result.update(condition='paused', next_action='Diga "continuar as candidaturas" se quiser retomar a campanha.')
        elif state.get('goal'):
            result['next_action'] = 'Conferir as pendências e as conexões antes da próxima ação autorizada.'
        else:
            from .navigation import search
            entry = search(root, Profile(root).get()['sections'])
            needs_user = entry['next_step'] != 'search_ready'
            result.update(phase=entry['next_step'], condition='waiting_user' if needs_user else 'ready',
                          needs_user=needs_user, next_action=entry['message'])
    elif activity == 'prepare':
        section = state['profile'].get('next_section')
        result.update(phase=section or 'review', condition='waiting_user', needs_user=True,
                      advance='Vamos completar apenas as informações que faltam.' if section else None,
                      next_action=(state['profile'].get('questions') or [{}])[0].get('question') or 'Confira a preparação e escolha o próximo passo.')
        if state['profile'].get('approved') and not state.get('goal'):
            result['next_action'] = 'Diga se quer apenas conhecer vagas ou também se candidatar.'
    elif activity == 'company':
        dossiers = state.get('companies') or []
        result.update(condition='waiting_user', needs_user=True,
                      advance=(f'{len(dossiers)} análises de empresas salvas.' if len(dossiers) > 1 else 'Uma análise de empresa salva.') if dossiers else None,
                      next_action='Escolha qual análise salva quer continuar.' if dossiers else 'Diga qual empresa quer analisar e o que precisa esclarecer.')
        if len(dossiers) == 1:
            result.update(condition='ready', needs_user=False, next_action='Conferir as fontes e as dúvidas pendentes da análise salva antes de concluir.')
    elif activity == 'presence':
        from .presence import Presence
        presence = Presence(root).status()
        topic = {'linkedin': 'LinkedIn', 'github': 'GitHub'}.get(presence['next_topic'])
        if presence['decision'] in {'later', 'skip'}:
            result.update(condition='paused', next_action='Diga qual perfil quer retomar quando decidir continuar.')
        elif topic:
            result.update(phase=presence['next_topic'], advance=f'Revisão de {topic} escolhida e ainda pendente.',
                          next_action=f'Conferir o material salvo de {topic} e preparar a revisão; pedir somente o que faltar.')
        elif presence['decision'] == 'now' and presence['reviews']:
            result.update(condition='completed', advance='As revisões escolhidas estão salvas.', next_action='Você pode consultar as sugestões ou escolher outra atividade. Publicar exige autorização própria.')
        else:
            result.update(condition='waiting_user', needs_user=True, next_action='Escolha LinkedIn ou GitHub e o material que quer revisar.')
    elif activity == 'offers':
        from .offers import Offers
        offers = Offers(root).status()
        if offers['count']:
            incomplete = sum(offer['incomplete'] for offer in offers['offers'])
            result.update(advance=f"{offers['count']} {'proposta salva' if offers['count'] == 1 else 'propostas salvas'}; {incomplete} com premissas pendentes.",
                          next_action='Conferir as premissas que faltam nas propostas salvas.' if incomplete else 'Conferir as premissas e comparar as propostas escolhidas.')
        else:
            result.update(condition='waiting_user', needs_user=True, next_action='Conte quais propostas quer comparar.')
    elif activity == 'models':
        from .models import Models
        guidance = Models(root).guidance()
        if guidance['decision'] == 'unasked':
            result.update(condition='waiting_user', needs_user=True, next_action=guidance['question'])
        elif guidance['decision'] == 'repair_needed':
            result.update(condition='needs_verification', next_action=guidance['message'])
        else:
            result.update(advance='Sua escolha sobre modelos está registrada.', next_action=guidance['message'])
    return result


def project(root, state, now, focus=None, start=None):
    """Project saved state into a compact message and separately requested details."""
    activity = selected_activity(root, state, focus, start)
    try:
        current = _activity(root, state, activity)
    except (ValueError, KeyError, TypeError, AttributeError):
        if activity not in {'curriculum', 'presence', 'offers', 'models'}:
            raise
        current = {'phase': 'review', 'condition': 'needs_verification', 'advance': None,
                   'next_action': 'Conferir os registros desta atividade com a IA antes de continuar.', 'needs_user': False}
        state['optional_data_issues'].append({'area': activity, 'message':
            'Os dados desta atividade precisam de reparo. Os registros foram preservados.'})
    notes = checkpoints(root, tolerate_invalid=True)
    point = notes.get(activity)
    zone = Profile(root).get()['sections'].get('identity', {}).get('timezone')
    valid_scope = point is not None and (activity != 'search' or point.get('campaign_generation') == state['control']['generation'])
    dependencies = []
    actionable_scope = valid_scope and not (activity == 'search' and state['control']['stopped'])
    if actionable_scope and point.get('dependency') and current['condition'] != 'completed':
        dependency = point['dependency']
        dependencies.append({'source': 'checkpoint', 'activity': activity, 'needs_user': point['needs_user'],
                             'instruction': DEPENDENCIES[dependency['reason']], 'reference': dependency.get('reference'),
                             'due_at': dependency.get('due_at'), 'recorded': True})
        if point['needs_user'] and current['condition'] not in {'completed', 'paused'}:
            current['condition'] = 'waiting_user'
            current.update(needs_user=True, next_action=DEPENDENCIES[dependency['reason']])
    if actionable_scope and point.get('condition') == 'waiting_tool' and current['condition'] not in {'paused', 'completed'}:
        current.update(condition='needs_verification', needs_user=False,
                       next_action='Conferir o retorno da ferramenta antes de continuar esta etapa.')
    for key, note in notes.items():
        if key == activity or not note['needs_user'] or not note.get('dependency'):
            continue
        if key == 'search' and (state['control']['stopped'] or note.get('campaign_generation') != state['control']['generation']):
            continue
        try:
            if _activity(root, state, key)['condition'] == 'completed':
                continue
        except (ValueError, KeyError, TypeError, AttributeError):
            state['optional_data_issues'].append({'area': key, 'message':
                f'Os dados de {LABELS[key]} precisam de reparo. A pendência não pôde ser conferida; os registros foram preservados.'})
            continue
        dependency = note['dependency']
        dependencies.append({'source': 'checkpoint', 'activity': key, 'needs_user': True,
                             'instruction': DEPENDENCIES[dependency['reason']], 'reference': dependency.get('reference'),
                             'due_at': dependency.get('due_at'), 'recorded': True})
    for item in state['pending']:
        if item['type'] == 'step' and item['state'] == 'candidate_pending':
            instruction = {'self_report': 'Responder o questionário pessoal no portal verificado.',
                           'interview_attendance': 'Participar da entrevista no horário combinado.',
                           'assessment': 'Conferir as instruções da avaliação pessoal no portal verificado.'}.get(item['kind'],
                           'Confira a etapa pendente no canal verificado; peça os detalhes à IA.')
            dependencies.append({'source': 'step', 'activity': 'search', 'needs_user': True,
                                 'instruction': instruction,
                                 'reference': item.get('company'), 'due_at': item.get('due_at'), 'step_id': item['step_id']})
    dependencies.sort(key=lambda item: moment(item.get('due_at')) or datetime.max.replace(tzinfo=timezone.utc))
    saved = {'at': point['saved_at'], 'display': display_time(point['saved_at'], zone, now),
             'activity_matches': True, 'campaign_matches': valid_scope,
             'note_is_not_authorization': True} if point else None
    current.update(activity=activity, label=LABELS[activity], campaign_stopped=bool(state['control']['stopped']),
                   execution='unverified', last_saved=saved, dependencies=dependencies,
                   user_actions=[item for item in dependencies if item['needs_user']],
                   help=HELP, progress=state.get('progress') if activity == 'search' else None)
    lines = ['Atividade: ' + current['label'] + '.']
    if current['campaign_stopped']:
        lines.append('Campanha de candidaturas parada. As demais atividades podem ser retomadas separadamente.')
    if current['advance']:
        lines.append('Último avanço confirmado: ' + current['advance'])
    if current['progress']:
        p = current['progress']
        scope = f"nos últimos {p['period_days']} dias" if p['period_days'] else 'desde o início do objetivo'
        lines.append(f"Meta: {p['confirmed_applications']} de {p['target_applications']} candidaturas confirmadas {scope}.")
    dependency_lines = []
    for item in dependencies:
        prefix = 'Precisa de você' if item['needs_user'] else 'Conferência pendente'
        if item['activity'] != activity:
            prefix += ' em ' + LABELS[item['activity']]
        reference = f" (referência: {short_reference(item['reference'])!r})" if item.get('reference') else ''
        overdue = moment(item.get('due_at')) is not None and moment(item['due_at']) < now
        item['overdue'] = overdue
        due = f" {'Prazo vencido' if overdue else 'Prazo'}: {display_time(item['due_at'], zone, now)}." if item.get('due_at') else ''
        dependency_lines.append(prefix + reference + ': ' + item['instruction'] + due)
    lines.extend(dependency_lines[:3])
    if len(dependencies) > 3:
        lines.append(f'Há mais {len(dependencies) - 3} dependências; peça os detalhes.')
    uncertain = sum(p['type'] == 'action' and p.get('status') == 'uncertain' for p in state['pending'])
    if uncertain:
        lines.append(f"{uncertain} {'ação' if uncertain == 1 else 'ações'} sem confirmação: conferir no destino antes de repetir.")
    other_steps = [item for item in state['pending'] if item['type'] == 'step' and item['state'] != 'candidate_pending']
    if other_steps:
        lines.append(f"{len(other_steps)} {'etapa complementar pendente' if len(other_steps) == 1 else 'etapas complementares pendentes'}; consulte os detalhes antes de agir.")
    prefix = 'Precisa de você: ' if current['needs_user'] else 'Próximo passo: '
    if not any(item['instruction'] == current['next_action'] for item in dependencies[:3]):
        lines.append(prefix + current['next_action'])
    if saved:
        lines.append('Último ponto salvo desta atividade: ' + saved['display'] + '. Execução atual não verificada.')
    elif state.get('checkpoint'):
        previous = state['checkpoint']
        lines.append('Último ponto salvo de outra atividade: ' + LABELS.get(activity_of(previous), 'campanha') + '. Consulte os detalhes para retomar esse contexto.')
    if valid_scope and point.get('condition') == 'waiting_tool':
        lines.append('A última nota registrou espera por ferramenta. Falta conferir o resultado atual.')
    if activity != 'career' and (state.get('career') or {}).get('paused'):
        lines.append('Seu guia de carreira está pausado e pode ser retomado separadamente.')
    if activity != 'practice' and state['practice'].get('decision') in {'later', 'skip'} and state['practice'].get('session_id'):
        lines.append('Seu treino adiado continua salvo.')
    for account in state.get('mail_coverage') or []:
        if account['status'] == 'partial':
            lines.append('A leitura dos e-mails ficou incompleta; falta retomar a consulta registrada.')
        elif account['status'] in {'auth_required', 'unavailable'}:
            lines.append('O acesso ao e-mail precisa ser conferido; essa consulta continua pendente.')
    lines.extend(issue['message'] for issue in state.get('optional_data_issues', []))
    details = list(lines)
    ledger = state.get('ledger')
    if ledger:
        details.append(f"Histórico local: {ledger['confirmed']} candidatura(s) confirmada(s), {ledger['uncertain']} oportunidade(s) com envio incerto e {ledger['discarded']} descartada(s).")
    for item in state['pending']:
        if item['type'] == 'action':
            label = ACTION_LABELS.get(item['action'], 'ação')
            status = 'resultado sem confirmação' if item['status'] == 'uncertain' else 'autorização registrada, execução não comprovada'
            reference = f" em {short_reference(item['company'])!r}" if item.get('company') else ''
            expiry = ' Autorização vencida; confira o destino antes de qualquer nova tentativa.' if item.get('authorization_expired') else ''
            details.append(f"Ação {item['action_id']}: {label}{reference}; {status}.{expiry}")
    step_states = {'pending': 'aguarda próxima etapa', 'in_progress': 'reservada; execução atual não verificada',
                   'blocked': 'bloqueada, exige conferência', 'action_started': 'ação iniciada; falta confirmação',
                   'uncertain': 'resultado incerto; conferir antes de repetir'}
    for item in other_steps:
        status = step_states.get(item['state'], 'pendente de conferência')
        overdue = moment(item.get('due_at')) is not None and moment(item['due_at']) < now
        due = (' Prazo vencido: ' if overdue else ' Prazo: ') + display_time(item['due_at'], zone, now) + '.' if item.get('due_at') else ''
        details.append(f"Etapa {item['step_id']} em {short_reference(item['company'])!r}: {status}.{due}")
    for key, note in notes.items():
        if key != activity:
            details.append(f"Outra atividade salva: {LABELS.get(key, key)}, {display_time(note['saved_at'], zone, now)}.")
        details.append(f"Nota de {LABELS[key]} (contexto registrado, a conferir): {short_reference(note['summary'])!r}.")
        details.append(f"Próxima ação anotada, sem autorização: {short_reference(note['next_action'])!r}.")
    details.extend(dependency_lines[3:])
    runner = state.get('runner')
    if runner:
        details.append('Registro de executor em ' + display_time(runner['created_at'], zone, now) + '. A presença desse registro não confirma uma sessão ativa.')
    details.append('Notas e registros não comprovam execução ativa, autorização atual ou recebimento de um envio.')
    return current, '\n'.join(lines + [HELP]), '\n'.join(details + [HELP])
