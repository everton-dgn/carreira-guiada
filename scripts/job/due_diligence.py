"""Private, offline records of observed public due diligence."""
import json
from datetime import datetime, timezone
from uuid import uuid4

from .profile import Profile
from .resumes import _text
from .sources import normalize_url


def _url(value):
    value = _text(value, 'a URL', 2000)
    if '?' in value:
        raise ValueError('Use uma URL pública sem parâmetros.')
    return normalize_url(value)


def _date(value):
    value = _text(value, 'a data com fuso', 100)
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.utcoffset() is None or date > datetime.now(timezone.utc):
            raise ValueError()
    except (ValueError, OverflowError):
        raise ValueError('Informe uma data válida, com fuso e sem data futura.') from None
    return value


def _texts(value, name, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= 100:
        raise ValueError('Informe uma lista válida para ' + name)
    return [_text(item, name, 2000) for item in value]


def _salary(item):
    fields = {'url', 'checked_at', 'role', 'location', 'seniority', 'contract', 'currency', 'period', 'minimum', 'maximum', 'sample_size'}
    if not isinstance(item, dict) or set(item) != fields:
        raise ValueError('Observação salarial incompleta.')
    out = {key: _text(item[key], key, 300) for key in ('role', 'location', 'seniority', 'contract', 'currency', 'period')}
    out.update(url=_url(item['url']), checked_at=_date(item['checked_at']))
    for key in ('minimum', 'maximum'):
        value = item[key]
        if type(value) not in (int, float) or not 0 <= value <= 1e12:
            raise ValueError('Valor salarial inválido.')
        out[key] = value
    if out['minimum'] > out['maximum']:
        raise ValueError('Faixa salarial inválida.')
    size = item['sample_size']
    if size is not None and (type(size) is not int or not 1 <= size <= 1000000000):
        raise ValueError('Amostra inválida.')
    out['sample_size'] = size
    return out


class DueDiligence:
    def __init__(self, root):
        self.profile = Profile(root)

    @staticmethod
    def _read(db):
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE name='job_due_diligence'").fetchone():
            return []
        row = db.execute('SELECT value FROM job_due_diligence WHERE id=1').fetchone()
        return json.loads(row[0]) if row else []

    def list(self):
        with self.profile._db() as db:
            return self._read(db)

    def get(self, record_id):
        return next((item for item in self.list() if item['id'] == record_id), None)

    def save(self, data):
        required = {'kind', 'subject', 'url', 'checked_at', 'identity', 'official_origin', 'data_requests', 'red_flags', 'evidence', 'uncertainties'}
        if not isinstance(data, dict) or not required <= set(data) or set(data) - required - {'salary_observations'}:
            raise ValueError('Parecer incompleto ou com campos desconhecidos.')
        if data['kind'] not in ('site', 'company', 'vacancy'):
            raise ValueError('Tipo inválido.')
        for key in ('identity', 'official_origin'):
            if data[key] not in ('confirmed', 'unknown', 'contradictory'):
                raise ValueError('Verificação inválida.')
        if data['data_requests'] not in ('ordinary', 'unknown', 'dangerous'):
            raise ValueError('Solicitação de dados inválida.')
        evidence = data['evidence']
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 100:
            raise ValueError('Informe evidências observadas.')
        clean_evidence = []
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {'url', 'observation', 'kind'} or item['kind'] not in ('official', 'independent', 'report'):
                raise ValueError('Evidência inválida.')
            clean_evidence.append({'url': _url(item['url']), 'observation': _text(item['observation'], 'a observação', 2000), 'kind': item['kind']})
        salaries = data.get('salary_observations', [])
        if not isinstance(salaries, list) or len(salaries) > 100:
            raise ValueError('Observações salariais inválidas.')
        result = {'id': str(uuid4()), 'kind': data['kind'], 'subject': _text(data['subject'], 'o assunto', 500),
                  'url': _url(data['url']), 'checked_at': _date(data['checked_at']),
                  'identity': data['identity'], 'official_origin': data['official_origin'], 'data_requests': data['data_requests'],
                  'red_flags': _texts(data['red_flags'], 'os sinais'), 'evidence': clean_evidence,
                  'uncertainties': _texts(data['uncertainties'], 'as incertezas'), 'salary_observations': [_salary(x) for x in salaries]}
        if result['red_flags'] or 'contradictory' in (result['identity'], result['official_origin']) or result['data_requests'] == 'dangerous':
            result['outcome'] = 'avoid'
        elif ('unknown' in (result['identity'], result['official_origin'], result['data_requests']) or result['uncertainties'] or not {'official', 'independent'} <= {e['kind'] for e in clean_evidence}):
            result['outcome'] = 'pending'
        else:
            result['outcome'] = 'consider'
        with self.profile._db(True) as db:
            records = self._read(db)
            records.append(result)
            db.execute('CREATE TABLE IF NOT EXISTS job_due_diligence (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_due_diligence VALUES (1, ?)', (json.dumps(records, ensure_ascii=False),))
        return result

    def suggestions(self):
        latest = {}
        for item in self.list():
            if item['kind'] == 'site':
                previous = latest.get(item['url'])
                if previous is None or datetime.fromisoformat(item['checked_at'].replace('Z', '+00:00')) >= datetime.fromisoformat(previous['checked_at'].replace('Z', '+00:00')):
                    latest[item['url']] = item
        return [{'id': x['id'], 'subject': x['subject'], 'url': x['url'], 'checked_at': x['checked_at'],
                 'limitation': 'Análise registrada, revalidar antes de uso.'} for x in latest.values() if x['outcome'] == 'consider']
