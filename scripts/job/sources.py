"""Private, offline validation of user-selected search destinations."""
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def normalize_url(value):
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError('Copie um endereço HTTPS público da barra do navegador.')
    try:
        u = urlsplit(value)
        host = (u.hostname or '').encode('idna').decode('ascii').lower()
        port = u.port
    except (ValueError, UnicodeError):
        raise ValueError('Endereço inválido.') from None
    labels = host.split('.')
    if (u.scheme != 'https' or u.username is not None or u.password is not None or '#' in value
        or len(labels) < 2 or not re.fullmatch(r'[a-z]{2,63}', labels[-1])
        or labels[-1] in {'localhost', 'local', 'internal', 'lan', 'home', 'onion'}
        or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)
        or 'localhost' in labels or port == 0):
        raise ValueError('Use um endereço HTTPS público, sem credenciais, fragmentos ou endereço local.')
    path = u.path or '/'
    if '%' in path or any(part in {'.', '..'} for part in path.split('/')) or '//' in path:
        raise ValueError('Copie um endereço sem escapes ou atalhos no caminho.')
    pairs = parse_qsl(u.query, keep_blank_values=True)
    allowed = {'q', 'query', 'search', 'keyword', 'keywords', 'location', 'page', 'sort'}
    if any(k not in allowed or not re.fullmatch(r'[\w .,+-]{0,160}', v) for k, v in pairs):
        raise ValueError('Remova tokens e parâmetros privados do endereço antes de salvar.')
    return urlunsplit(('https', host + (':' + str(port) if port and port != 443 else ''), path, urlencode(pairs), ''))


def normalize_sources(urls):
    if not isinstance(urls, list):
        raise ValueError('Informe uma lista de endereços; use [] para deixar para depois.')
    return list(dict.fromkeys(normalize_url(url) for url in urls))


def research_target(value, urls):
    if not urls:
        raise ValueError('Antes de pesquisar, copie os endereços dos sites desejados, salve e aprove o perfil. Podemos continuar preparando o currículo.')
    target = normalize_url(value)
    parsed = urlsplit(target)
    for source in normalize_sources(urls):
        base = urlsplit(source)
        boundary = base.path.rstrip('/')
        if parsed.netloc == base.netloc and (parsed.path == boundary or parsed.path.startswith(boundary + '/')):
            return target
    raise ValueError('source_url precisa pertencer a um endereço aprovado no perfil, respeitando domínio, porta e caminho.')
