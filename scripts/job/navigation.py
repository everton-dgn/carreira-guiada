"""Read-only entry points for independently chosen tasks."""
import unicodedata

CHOICES = [('1', 'curriculum', 'Currículo'), ('2', 'practice', 'Entrevistas'),
           ('3', 'career', 'Guia de carreira'), ('4', 'search', 'Busca de vagas')]


def menu(selection=None):
    """Describe the available routes without persisting the selection."""
    choices = [{'number': n, 'focus': f, 'label': label} for n, f, label in CHOICES]
    message = 'O que você quer fazer?\n' + '\n'.join(f'{n}. {label}' for n, _, label in CHOICES)
    if selection is None:
        return {'message': message, 'choices': choices, 'selected': None}
    key = ''.join(c for c in unicodedata.normalize('NFKD', selection.strip().casefold()) if not unicodedata.combining(c))
    aliases = {'curriculo': 'curriculum', 'entrevista': 'practice', 'entrevistas': 'practice',
               'carreira': 'career', 'guia de carreira': 'career', 'busca': 'search', 'vagas': 'search', 'busca de vagas': 'search'}
    focus = aliases.get(key) or next((f for n, f, _ in CHOICES if key in (n, f)), None)
    return {'message': message if focus else 'Opção desconhecida. Escolha um número ou nome.\n' + message,
            'choices': choices, 'selected': focus}


def search(root, sections):
    """Discover public search readiness; consent never follows from discovery.

    The scope target binds all saved preferences and source URLs to a generation.
    Actual requests still require checking each URL immediately before use.
    """
    from .profile import QUESTIONS
    from .research_scope import ResearchScopes, job_search_target
    from .due_diligence import _url
    prefs = sections.get('preferences', {})
    for field in ('roles', 'modalities'):
        if field not in prefs:
            _, prompt, example = next(q for q in QUESTIONS['preferences'] if q[0] == field)
            return {'next_step': 'preferences', 'question': {'field': field, 'question': prompt, 'example': example}, 'message': prompt + ' ' + example}
    urls = sections.get('sources', {}).get('urls', [])
    if not urls:
        return {'next_step': 'sources', 'question': None, 'message': 'Quais sites quer usar? Cole os links ou peça ajuda para encontrar opções verificadas.'}
    try:
        urls = list(dict.fromkeys(_url(url) for url in urls))
    except ValueError:
        return {'next_step': 'sources', 'question': None, 'message': 'Para a pesquisa pública, informe URLs de fontes sem parâmetros.'}
    target = job_search_target(prefs, urls)
    scopes = ResearchScopes(root)
    with scopes.profile._db() as db:
        _, stopped = scopes._control(db)
    if stopped:
        return {'next_step': 'search_paused', 'question': None, 'message': 'A pesquisa está parada. Retome explicitamente antes de autorizar uma nova pesquisa.', 'filters': prefs, 'urls': urls}
    for scope in reversed(scopes.list()):
        if scope['purpose'] == 'job_search' and scope['target'] == target and scope['urls'] == urls:
            checks = [scopes.check({'scope_id': scope['id'], 'expected_version': scope['version'], 'purpose': 'job_search', 'target': target, 'url': url}) for url in urls]
            if all(c['allowed'] for c in checks):
                return {'next_step': 'search_ready', 'question': None, 'message': 'A pesquisa pública está autorizada para os filtros e sites combinados. Nenhuma candidatura foi autorizada.', 'scope': scope, 'filters': prefs, 'urls': urls}
    return {'next_step': 'search_scope_confirmation', 'question': None,
            'message': 'Confira os filtros e os sites e confirme se posso pesquisar vagas públicas neles.',
            'filters': prefs, 'urls': urls, 'scope_request': {'purpose': 'job_search', 'target': target, 'urls': urls}}
