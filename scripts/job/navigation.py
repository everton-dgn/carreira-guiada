"""Read-only entry points for independently chosen tasks."""
import unicodedata

CHOICES = [('1', 'curriculum', 'Currículo'), ('2', 'practice', 'Entrevistas'),
           ('3', 'career', 'Guia de carreira'), ('4', 'search', 'Busca de vagas')]
MORE = [('empresa', 'company', 'Empresa'), ('presença', 'presence', 'LinkedIn/GitHub'),
        ('propostas', 'offers', 'Propostas'), ('modelos', 'models', 'Preferências de modelos'),
        ('preparo', 'prepare', 'Preparo completo')]


def menu(selection=None):
    """Describe the available routes without persisting the selection."""
    choices = [{'number': n, 'focus': f, 'label': label} for n, f, label in CHOICES]
    message = 'O que você quer fazer?\n' + '\n'.join(f'{n}. {label}' for n, _, label in CHOICES)
    message += '\n5. Mais opções'
    message += '\nDiga o número ou o nome. Você pode mudar de atividade sem perder suas respostas.'
    if selection is None:
        return {'message': message, 'choices': choices, 'selected': None}
    key = ''.join(c for c in unicodedata.normalize('NFKD', selection.strip().casefold()) if not unicodedata.combining(c))
    if key in ('5', 'mais', 'mais opcoes', 'more'):
        choices = [{'number': n, 'focus': f, 'label': label} for n, f, label in MORE]
        return {'message': 'Mais opções:\n' + '\n'.join(label for _, _, label in MORE) + '\nDiga o nome da atividade.',
                'choices': choices, 'selected': None}
    aliases = {'curriculo': 'curriculum', 'entrevista': 'practice', 'entrevistas': 'practice',
               'carreira': 'career', 'guia de carreira': 'career', 'busca': 'search', 'vagas': 'search', 'busca de vagas': 'search',
               'prepare': 'prepare', 'preparo': 'prepare', 'preparo completo': 'prepare',
               'empresa': 'company', 'empresas': 'company', 'company': 'company',
               'presenca': 'presence', 'linkedin': 'presence', 'github': 'presence', 'linkedin/github': 'presence', 'presence': 'presence',
               'proposta': 'offers', 'propostas': 'offers', 'offers': 'offers',
               'modelos': 'models', 'modelo': 'models', 'preferencias de modelos': 'models', 'models': 'models'}
    focus = aliases.get(key) or next((f for n, f, _ in CHOICES if key in (n, f)), None)
    return {'message': message if focus else 'Opção desconhecida. Escolha um número ou nome.\n' + message,
            'choices': choices, 'selected': focus}


def resume_entry(result, focus):
    """Name a saved direct activity without starting it or repeating its question."""
    labels = {'curriculum': 'Currículo', 'search': 'Busca de vagas', 'company': 'Empresa',
              'presence': 'LinkedIn/GitHub', 'offers': 'Propostas', 'models': 'Preferências de modelos'}
    if focus not in labels:
        return result
    hints = {
        'curriculum_input': 'Podemos continuar a criação ou a importação do currículo.',
        'curriculum_intake': 'Suas respostas anteriores estão salvas; falta continuar as informações profissionais.',
        'resume_approval': 'O próximo passo é revisar o currículo e aprovar uma versão.',
        'curriculum_complete': 'Seu currículo aprovado continua disponível.',
        'preferences': 'O próximo passo é combinar o tipo de trabalho e a modalidade.',
        'sources': 'O próximo passo é escolher onde procurar vagas.',
        'search_scope_confirmation': 'Antes de pesquisar, precisamos conferir os filtros, os links e a autorização.',
        'search_ready': 'A consulta pública combinada está autorizada. Nenhuma candidatura foi iniciada.',
        'search_paused': 'A pesquisa continua parada. Abrir o menu não a retoma.',
        'execution_readiness': 'O próximo passo é conferir as conexões e as ações autorizadas da campanha.',
    }
    return {**result, 'welcome_back': f'Sua atividade salva é {labels[focus]}. Quer continuar, revisar suas respostas ou escolher outra atividade no menu?',
            'resume_options': ['continue', 'review', 'menu'], 'resume_hint': hints.get(result['next_step'], result['message'])}


def search(root, sections):
    """Discover public search readiness; consent never follows from discovery.

    The scope target binds all saved preferences and source URLs to a generation.
    Actual requests still require checking each URL immediately before use.
    """
    from .profile import QUESTIONS
    from .research_scope import ResearchScopes, job_search_target
    from .sources import normalize_sources
    prefs = sections.get('preferences', {})
    for field in ('roles', 'modalities'):
        if field not in prefs or (field == 'roles' and not prefs[field]):
            _, prompt, example = next(q for q in QUESTIONS['preferences'] if q[0] == field)
            return {'next_step': 'preferences', 'question': {'field': field, 'question': prompt, 'example': example}, 'message': prompt + ' ' + example}
    urls = sections.get('sources', {}).get('urls', [])
    if not urls:
        return {'next_step': 'sources', 'question': None, 'message': 'Quais sites quer usar? Cole os links ou peça ajuda para encontrar opções verificadas.'}
    try:
        urls = normalize_sources(urls)
    except ValueError:
        return {'next_step': 'sources', 'question': None, 'message': 'Informe links HTTPS públicos, sem credenciais ou parâmetros privados.'}
    target = job_search_target(prefs, urls)
    scopes = ResearchScopes(root)
    with scopes.profile._db() as db:
        _, stopped = scopes._control(db)
    if stopped:
        return {'next_step': 'search_paused', 'question': None, 'message': 'A pesquisa está parada. Retome explicitamente antes de autorizar uma nova pesquisa.', 'filters': prefs, 'urls': urls}
    for scope in reversed(scopes.list()):
        if scope['purpose'] == 'job_search' and scope['target'] == target and scope['urls'] == urls and scope.get('url_policy') == 'source_paths':
            checks = [scopes.check({'scope_id': scope['id'], 'expected_version': scope['version'], 'purpose': 'job_search', 'target': target, 'url': url}) for url in urls]
            if all(c['allowed'] for c in checks):
                return {'next_step': 'search_ready', 'question': None, 'message': 'A pesquisa pública está autorizada para os filtros e sites combinados. Nenhuma candidatura foi autorizada.', 'scope': scope, 'filters': prefs, 'urls': urls}
    return {'next_step': 'search_scope_confirmation', 'question': None,
            'message': 'Confira os filtros e os links. Posso consultar resultados, páginas seguintes e detalhes de vagas dentro desses mesmos endereços e caminhos?',
            'filters': prefs, 'urls': urls, 'scope_request': {'purpose': 'job_search', 'target': target, 'urls': urls, 'url_policy': 'source_paths'}}
