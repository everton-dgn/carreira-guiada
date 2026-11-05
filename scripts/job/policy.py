"""Filtros exatos, sem inferir profissão ou remuneração.

Preferences (todos os campos são obrigatórios ao aprovar):
roles, modalities, currencies, levels, contracts, locations, technologies,
blocked_companies, blocked_sectors, blocked_platforms: listas de strings únicas.
Listas vazias desativam aquele filtro, exceto roles/modalities/currencies,
que precisam conter escolhas. missing: 'ask'|'reject'|'accept'.
languages: [{name: str, level: int 1..6, required: bool}].
salary: {missing: 'ask'|'reject'|'accept', estimated: 'ask'|'reject'|'accept',
range: 'ask'|'minimum'|'maximum', floors: [{contract: str, currency: str,
period: 'hour'|'month'|'year', amount: número positivo}],
public_expectation: null|{currency: str, period: ..., amount: número positivo}}.

Vacancy: objeto com campos opcionais role, modality, currency (não utilizado;
a moeda deve constar em salary), level, contract, location, company, sector,
platform: string|null; technologies: [str]|null;
languages: [{name: str, level: int 1..6, required: bool}]|null;
salary: null|{min: número positivo|null, max: número positivo|null,
currency: str, period: 'hour'|'month'|'year', estimated: bool,
guaranteed_hours_per_month: número positivo|null (opcional)}.
Ao menos uma ponta salarial deve existir. Nomes e categorias são comparados
por igualdade normalizada de caixa e acentos. Valores com ponto e sem
espaços (domínios/identificadores) preservam acentos; não há busca por trechos.
range=maximum permanece compatível, mas tem o mesmo efeito de ask: teto
ou faixa cruzando piso exige confirmação do mínimo; minimum pode descartar. Idiomas required da vaga
são exigências; os restantes são diferenciais. Languages do perfil registra
proficiência e required indica exigência de uso daquele idioma na vaga.
Ausências nos campos de bloqueio também seguem missing. Sem horas garantidas,
remuneração horária não é convertida. Ano equivale a 12 meses, sem bônus.
blocked significa decisão humana pendente; discarded significa incompatível.
"""
import math
import unicodedata

LISTS = ('roles', 'modalities', 'currencies', 'levels', 'contracts', 'locations',
         'technologies', 'blocked_companies', 'blocked_sectors', 'blocked_platforms')
PERIODS = ('hour', 'month', 'year')


def category(value):
    """Chave de igualdade, preservando pontuação e identidade de domínios."""
    if value is None:
        return None
    folded = unicodedata.normalize('NFC', value).casefold()
    if '.' in folded and not any(c.isspace() for c in folded):
        return folded
    return ''.join(c for c in unicodedata.normalize('NFD', folded)
                   if not unicodedata.combining(c))


def categories(values):
    return {category(value) for value in values}


def obj(value, keys, required=()):
    if not isinstance(value, dict) or set(value) - set(keys) or set(required) - set(value):
        raise ValueError('Objeto inválido: confira campos obrigatórios e desconhecidos.')


def string(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError('Informe texto não vazio, sem espaços nas bordas.')


def strings(value):
    if not isinstance(value, list):
        raise ValueError('Informe uma lista de textos.')
    for item in value:
        string(item)
    if len(set(value)) != len(value):
        raise ValueError('A lista contém valores repetidos.')


def number(value):
    if type(value) not in (int, float) or value <= 0 or value > 1e100 or not math.isfinite(value):
        raise ValueError('Informe um número positivo e finito.')


def languages(value):
    if not isinstance(value, list):
        raise ValueError('Idiomas devem ser uma lista.')
    names = []
    for item in value:
        obj(item, ('name', 'level', 'required'), ('name', 'level', 'required'))
        string(item['name'])
        if type(item['level']) is not int or not 1 <= item['level'] <= 6 or type(item['required']) is not bool:
            raise ValueError('Idioma exige nível inteiro de 1 a 6 e required booleano.')
        names.append(category(item['name']))
    if len(set(names)) != len(names):
        raise ValueError('Idioma duplicado.')


def money(value, floor=False):
    keys = ('currency', 'period', 'amount') + (('contract',) if floor else ())
    obj(value, keys, keys)
    string(value['currency'])
    if floor:
        string(value['contract'])
    if value['period'] not in PERIODS:
        raise ValueError('Periodicidade inválida.')
    number(value['amount'])


def validate_preferences(value, complete=True):
    keys = LISTS + ('missing', 'languages', 'salary')
    obj(value, keys, keys if complete else ())
    for key in LISTS:
        if key in value:
            strings(value[key])
            if complete and key in ('roles', 'modalities', 'currencies') and not value[key]:
                raise ValueError('Preencha ' + key + '.')
    if 'missing' in value and value['missing'] not in ('ask', 'reject', 'accept'):
        raise ValueError('Política de informação ausente inválida.')
    if 'languages' in value:
        languages(value['languages'])
    if 'salary' in value:
        s = value['salary']
        keys = ('missing', 'estimated', 'range', 'floors', 'public_expectation')
        obj(s, keys, keys if complete else ())
        for key, options in (('missing', ('ask', 'reject', 'accept')), ('estimated', ('ask', 'reject', 'accept')), ('range', ('ask', 'minimum', 'maximum'))):
            if key in s and s[key] not in options:
                raise ValueError('Política salarial inválida.')
        if not isinstance(s.get('floors', []), list):
            raise ValueError('Pisos devem ser uma lista.')
        seen = set()
        for floor in s.get('floors', []):
            money(floor, True)
            key = (category(floor['contract']), category(floor['currency']), floor['period'])
            if key in seen:
                raise ValueError('Piso duplicado.')
            seen.add(key)
        if s.get('public_expectation') is not None:
            money(s['public_expectation'])


def evaluate(preferences, vacancy):
    """Retorna {decision: eligible|blocked|discarded, reasons: list[str]}.

    Valida todo o payload antes de avaliar, inclusive campos sem filtro ativo.
    Veja o esquema completo na docstring do módulo.
    """
    validate_preferences(preferences)
    scalar = ('role', 'modality', 'currency', 'level', 'contract', 'location', 'company', 'sector', 'platform')
    obj(vacancy, scalar + ('technologies', 'languages', 'salary'))
    for key in scalar:
        if vacancy.get(key) is not None:
            string(vacancy[key])
    if vacancy.get('technologies') is not None:
        strings(vacancy['technologies'])
    if vacancy.get('languages') is not None:
        languages(vacancy['languages'])
    salary = vacancy.get('salary')
    if salary is not None:
        keys = ('min', 'max', 'currency', 'period', 'estimated', 'guaranteed_hours_per_month')
        obj(salary, keys, keys[:5])
        string(salary['currency'])
        if salary['period'] not in PERIODS or type(salary['estimated']) is not bool:
            raise ValueError('Salário exige periodicidade válida e estimated booleano.')
        for key in ('min', 'max', 'guaranteed_hours_per_month'):
            if salary.get(key) is not None:
                number(salary[key])
        if salary['min'] is None and salary['max'] is None:
            raise ValueError('Informe ao menos uma ponta salarial.')
        if salary['min'] is not None and salary['max'] is not None and salary['min'] > salary['max']:
            raise ValueError('Faixa salarial invertida.')
    pending, rejected = [], []
    def policy(mode, reason):
        if mode == 'ask': pending.append(reason)
        elif mode == 'reject': rejected.append(reason)
    def absent(reason): policy(preferences['missing'], reason)
    for p, v in (('roles', 'role'), ('modalities', 'modality'), ('levels', 'level'), ('contracts', 'contract'), ('locations', 'location')):
        if preferences[p]:
            if vacancy.get(v) is None: absent('Informação ausente: ' + v)
            elif category(vacancy[v]) not in categories(preferences[p]): rejected.append('Fora da preferência: ' + v)
    for p, v in (('blocked_companies', 'company'), ('blocked_sectors', 'sector'), ('blocked_platforms', 'platform')):
        if preferences[p]:
            if vacancy.get(v) is None: absent('Bloqueio não verificável: ' + v)
            elif category(vacancy[v]) in categories(preferences[p]): rejected.append('Bloqueio: ' + v)
    if preferences['technologies']:
        if vacancy.get('technologies') is None: absent('Tecnologias ausentes.')
        elif not categories(preferences['technologies']) <= categories(vacancy['technologies']): rejected.append('Tecnologias exigidas ausentes.')
    if vacancy.get('languages') is None:
        absent('Idiomas da vaga desconhecidos.')
    else:
        known = {category(x['name']): x['level'] for x in preferences['languages']}
        offered = {category(x['name']) for x in vacancy['languages']}
        for lang in vacancy['languages']:
            if lang['required'] and known.get(category(lang['name']), 0) < lang['level']:
                rejected.append('Proficiência insuficiente: ' + lang['name'])
        for lang in preferences['languages']:
            if lang['required'] and category(lang['name']) not in offered:
                rejected.append('Idioma de trabalho ausente: ' + lang['name'])
    rules = preferences['salary']
    if salary is None:
        policy(rules['missing'], 'Remuneração ausente.')
    else:
        if category(salary['currency']) not in categories(preferences['currencies']):
            rejected.append('Moeda não aceita.')
        if salary['estimated']:
            policy(rules['estimated'], 'Remuneração estimada, sem confirmação.')
        floors = rules['floors']
        if floors and vacancy.get('contract') is None:
            pending.append('Contrato desconhecido para selecionar piso.')
        contract_floors = [f for f in floors if category(f['contract']) == category(vacancy.get('contract'))]
        matching_floors = [f for f in contract_floors if category(f['currency']) == category(salary['currency'])]
        if contract_floors and not matching_floors:
            pending.append('Piso em moeda diferente; conversão não autorizada.')
        for floor in matching_floors:
            factor = 1
            if floor['period'] != salary['period']:
                hours = salary.get('guaranteed_hours_per_month')
                if 'hour' in (floor['period'], salary['period']) and hours is None:
                    pending.append('Sem horas garantidas para converter remuneração.')
                    continue
                monthly = {'month': 1, 'year': 1 / 12, 'hour': hours or 1}
                factor = monthly[salary['period']] / monthly[floor['period']]
            low = salary['min'] * factor if salary['min'] is not None else None
            high = salary['max'] * factor if salary['max'] is not None else None
            if high is not None and high < floor['amount']:
                rejected.append('Remuneração abaixo do piso privado.')
            elif low is not None and low >= floor['amount']: pass
            elif rules['range'] == 'minimum' and low is not None:
                rejected.append('Mínimo da faixa abaixo do piso privado.')
            else: pending.append('Faixa salarial precisa de confirmação.')
    return {'decision': 'discarded' if rejected else 'blocked' if pending else 'eligible', 'reasons': rejected + pending}
