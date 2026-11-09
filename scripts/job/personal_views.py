"""Private planning entry points and readable projections, without execution."""

from datetime import datetime

from .planning import PersonalPlan
from .personal_progress import PersonalProgress


def entry(root, focus):
    """Offer one contextual question without requiring the application profile."""
    reports = []
    if focus == 'plan':
        state = PersonalPlan(root).status()
        if not state['exists']:
            question = 'O que você quer conseguir primeiro? Por exemplo, preparar o currículo ou treinar uma entrevista. Pode dizer "não sei".'
            from .career import CareerGuide
            career = CareerGuide(root).status()['session']
            if career and career['answers'].get('goal', {}).get('value'):
                state['confirmed_context'] = career['answers']
                state['suggested_basis'] = [{'kind': 'career', 'id': career['id'], 'version': career['version']}]
                question = 'Você já contou seu objetivo no guia de carreira: ' + career['answers']['goal']['value'] + '. Quer usá-lo neste plano ou ajustar a direção?'
        elif state['state'] == 'paused':
            question = 'Seu plano está pausado. Quer retomá-lo, ajustar o próximo passo ou apenas consultar?'
        elif state['state'] == 'archived':
            question = 'Este plano está arquivado. Quer consultar o histórico ou começar outro?'
        elif not state.get('next_action') and any(a['state'] == 'deferred' for a in state['actions']):
            question = 'Há ação adiada no plano. Quer retomar uma delas, ajustar o combinado ou deixar para depois?'
        elif state['actions'] and all(a['state'] == 'completed' for a in state['actions']):
            question = 'As ações combinadas foram concluídas. Quer revisar este ciclo, escolher outro passo ou encerrar o plano?'
        elif not state.get('next_action') and state['actions']:
            question = 'Não há ação pendente. Quer revisar este ciclo, escolher outro passo ou encerrar o plano?'
        elif not state.get('next_action'):
            question = 'Qual pequeno passo cabe na sua rotina? Por exemplo, ensaiar uma resposta por cinco minutos.'
        elif any(ref['changed'] for ref in state.get('basis', [])):
            question = 'Uma fonte do plano mudou. Vamos conferir essa orientação antes de escolher o próximo passo?'
        else:
            question = 'Quer fazer esse passo agora, diminuí-lo ou escolher outra atividade?'
        label, step = 'Meu plano', 'personal_plan'
    else:
        progress = PersonalProgress(root)
        state = progress.status()
        if state['mode'] != 'off':
            reports = [event for event in progress.get()['events']
                       if not event['revoked'] and event['source']['kind'] == 'user_report']
        if state['mode'] == 'off':
            question = 'Quer guardar suas práticas, ver conquistas com evidências ou também usar pontos? Pode deixar desativado.'
        elif not state['practice_count'] and not reports:
            question = 'Quer registrar algo que você praticou? Por exemplo, uma resposta ensaiada ou um estudo. Pode deixar para depois.'
        elif state['mode'] == 'tracking' or not state['milestones']:
            question = 'Quer registrar outra prática, corrigir um registro ou ajustar este acompanhamento?'
        else:
            question = 'Quer registrar uma prática que você fez, conferir uma conquista ou ajustar este acompanhamento?'
        label, step = 'Minha evolução', 'personal_progress'
    value = {**state, 'view': focus, 'next_step': step, 'question': {'question': question},
             'welcome_back': None, 'resume_hint': question, 'resume_options': [],
             'automatic_execution_started': False}
    value['message'] = describe(value, reports) + '\n' + question
    if state.get('exists') or state.get('version', 0):
        saved = 'salvo' if focus == 'plan' else 'salva'
        value['welcome_back'] = f'{label} está {saved}. Você pode continuar, ajustar ou escolher outra atividade.'
        value['resume_options'] = ['continue', 'review', 'menu']
        value['resume_hint'] = value['message']
    return value


def describe(value, reports=()):
    """Keep evidence, unknown estimates and the next action visible in plain text."""
    if value['view'] == 'plan':
        lines = ['Meu plano']
        if not value.get('exists'):
            return '\n'.join(lines + ['Vamos escolher um objetivo e um primeiro passo que caiba na sua rotina.'])
        labels = {'active': 'em andamento', 'paused': 'pausado', 'archived': 'arquivado'}
        lines.append('Situação: ' + labels[value['state']] + '.')
        lines.append('Direção: ' + (value.get('direction') or 'a combinar') + '.')
        cycle = value.get('cycle')
        if cycle:
            lines.append('Ciclo atual: ' + cycle['title'])
            if cycle.get('review_on'):
                lines.append('Revisão combinada: ' + cycle['review_on'])
        action = value.get('next_action')
        if action:
            lines += ['Próximo passo: ' + action['title'], 'Para quê: ' + action['reason'],
                      'Termina quando: ' + action['criterion']]
            if action.get('smaller_step'):
                lines.append('Se hoje couber menos: ' + action['smaller_step'])
            if action.get('if_then'):
                lines.append('Se, então: ' + action['if_then'])
            estimate = action.get('estimated_minutes')
            lines.append('Estimativa: ' + ('a combinar' if estimate is None else f'{estimate} min'))
        other_actions = [item for item in value.get('actions', []) if not action or item['id'] != action['id']]
        action_labels = {'planned': 'Planejada', 'active': 'Em andamento', 'completed': 'Concluída',
                         'deferred': 'Adiada', 'cancelled': 'Cancelada'}
        if other_actions:
            lines.append('Outras ações salvas:' if action else 'Ações salvas:')
            for item in other_actions[:5]:
                lines.append(action_labels[item['state']] + ': ' + item['title'])
            if len(other_actions) > 5:
                lines.append(f'Mais {len(other_actions) - 5} ações salvas. Peça para ver todas quando quiser.')
        budget = value.get('budget') or {}
        capacity = budget.get('weekly_minutes')
        lines.append('Tempo disponível por semana: ' + ('a combinar' if capacity is None else f'{capacity} min') + '.')
        for period in budget.get('periods', []):
            planned, remaining = period['planned_minutes'], period['remaining_minutes']
            estimate = 'estimativa incompleta' if planned is None else f'{planned} min planejados'
            free = '; tempo livre a calcular' if remaining is None else f'; {remaining} min livres'
            lines.append(f"Semana de {period['period']}: {estimate}{free}.")
            if period['over_by_minutes']:
                lines.append(f"O plano ultrapassa sua disponibilidade em {period['over_by_minutes']} min. Podemos reduzir ou adiar uma ação.")
        if budget.get('without_period'):
            lines.append(f"{len(budget['without_period'])} ação(ões) ainda sem semana definida.")
        if any(ref['changed'] for ref in value.get('basis', [])):
            lines.append('Uma fonte do plano mudou. Confira a orientação antes de seguir a ação relacionada.')
        return '\n'.join(lines)
    mode = value['mode']
    if mode == 'off':
        return 'Minha evolução\nAcompanhamento desativado. Você pode usar todas as atividades sem pontos ou conquistas.'
    labels = {'tracking': 'práticas registradas', 'achievements': 'práticas e conquistas', 'points': 'práticas, conquistas e pontos'}
    lines = ['Minha evolução', 'Você escolheu: ' + labels[mode] + '.',
             f"Treinos com autoria confirmada: {value['practice_count']}.",
             f"Tempo informado por você: {value['reported_minutes']} min."]
    if reports:
        lines.append(f'Atividades relatadas por você: {len(reports)}.')
        lines.append('Últimos relatos salvos:')
        for event in reports[-3:]:
            description = ' '.join(event['source']['description'].split())
            if len(description) > 160:
                description = description[:157] + '...'
            day = datetime.fromisoformat(event['occurred_at']).strftime('%d/%m/%Y')
            duration = 'duração não informada' if event['reported_minutes'] is None else f"{event['reported_minutes']} min"
            lines.append(f'Relato de {day}: {description} ({duration}).')
        if len(reports) > 3:
            lines.append('Peça para ver os relatos anteriores quando quiser.')
    elif not value['practice_count']:
        lines.append('Ainda não há práticas registradas. Ativar o acompanhamento não registra um treino por si só.')
    if value.get('unreported_time_count'):
        lines.append(f"{value['unreported_time_count']} registro(s) sem duração informada; o total está incompleto.")
    if value.get('points') is not None:
        lines += [f"Pontos: {value['points']}.", 'Convenção v1: 10 por treino confirmado, sem relação com a duração.']
    for milestone in value.get('milestones', []):
        status = 'precisa de revisão' if milestone.get('needs_review') else 'registrado'
        lines.append(f"Marco: {milestone['title']} ({status}).")
        lines.append('Critério: ' + milestone['criterion'])
        lines.append('Avaliação contestável: ' + milestone['assessment'])
        evidence = milestone.get('evidence') or {}
        if evidence.get('answer_excerpt'):
            lines.append('Trecho da resposta: ' + evidence['answer_excerpt'])
            lines.append('Trecho do feedback: ' + evidence['feedback_excerpt'])
        if evidence.get('previous_answer_excerpt'):
            lines.append('Resposta anterior: ' + evidence['previous_answer_excerpt'])
            lines.append('Feedback anterior: ' + evidence['previous_feedback_excerpt'])
    lines.extend(value.get('evidence_warnings', []))
    lines.append('Esses registros não medem seu valor nem garantem contratação. Você pode corrigir ou contestar uma avaliação.')
    return '\n'.join(lines)


def dispatch(root, command, action, data=None):
    """Separate read-only display from explicit, version-checked mutations."""
    service = PersonalPlan(root) if command == 'plan' else PersonalProgress(root)
    if action in ('show', 'status'):
        return entry(root, command)
    if action == 'get':
        if command == 'progress':
            return service.get()
        if not isinstance(data, dict) or set(data) - {'id', 'version'}:
            raise ValueError('A IA precisa conferir o identificador e a versão do plano salvo.')
        result = service.get(data.get('id'), data.get('version'))
        if result is None:
            raise ValueError('Plano não encontrado. Vamos conferir os planos salvos antes de continuar.')
        return result
    if action == 'history':
        if command == 'progress':
            return service.history()
        if not isinstance(data, dict) or set(data) != {'id'}:
            raise ValueError('Informe o identificador do plano para consultar seu histórico.')
        return service.history(data['id'])
    result = getattr(service, action)(data)
    if command == 'plan' and action in ('start', 'resume'):
        from .intake import Intake
        Intake(root).select_existing_route('plan')
    return result
