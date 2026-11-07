"""Procedural public-research permission, not network containment.

ResearchScopes.grant(data), get(scope_id, version=None), list(), revoke(data).
check(data, *, db=None) accepts scope_id, expected_version, purpose, target,
url and returns allowed/reason/scope_id/version. Pass the caller's write
transaction as db to check revocation and workflow generation atomically.
Targets: company_dossier/company, career_exploration/career,
source_discovery/source, job_search/search. URLs are exact normalized public URLs without queries.
Historical reads do not require a currently active permission.
"""
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4
from .profile import Profile
from .policy import obj
from .due_diligence import _url, _date
from .resumes import _text


def fields(data, required, optional=()):
    obj(data, tuple(required) + tuple(optional), tuple(required))


def positive(value):
    if type(value) is not int or value < 1:
        raise ValueError('Versão ou identificador inválido.')
    return value


def text(value):
    return _text(value, 'texto', 4000)


def table_exists(db, name):
    return db is not None and bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def job_search_target(preferences, urls):
    """Bind a public job search to the saved filters and exact normalized URLs."""
    urls = list(dict.fromkeys(_url(url) for url in urls))
    if 'roles' not in preferences or 'modalities' not in preferences or not urls:
        raise ValueError('Combine o tipo de trabalho, a modalidade e os sites antes de pesquisar.')
    digest = hashlib.sha256(json.dumps({'preferences': preferences, 'urls': urls},
        sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    return {'kind': 'search', 'id': digest}


class Revisions:
    table = ''

    def __init__(self, root):
        self.profile = Profile(root)

    def _rows(self, db):
        if not table_exists(db, self.table):
            return []
        records = []
        for identifier, version, raw in db.execute(f'SELECT id,version,value FROM {self.table} ORDER BY version'):
            try:
                record = json.loads(raw)
                self._validate(record)
                if record['id'] != identifier or record['version'] != version:
                    raise ValueError('Identidade divergente.')
            except (TypeError, KeyError, json.JSONDecodeError) as exc:
                raise ValueError('Registro persistido inválido.') from exc
            records.append(record)
        return records

    def _get(self, db, identifier, version=None):
        text(identifier)
        if version is not None:
            positive(version)
        return next((r for r in reversed(self._rows(db)) if r['id'] == identifier and (version is None or r['version'] == version)), None)

    def get(self, identifier, version=None):
        with self.profile._db() as db:
            return self._get(db, identifier, version)

    def list(self):
        with self.profile._db() as db:
            latest = {r['id']: r for r in self._rows(db)}
            return list(latest.values())

    def _save(self, db, record):
        self._validate(record)
        db.execute(f'CREATE TABLE IF NOT EXISTS {self.table} (id TEXT NOT NULL, version INTEGER NOT NULL, value TEXT NOT NULL, PRIMARY KEY(id,version))')
        db.execute(f'INSERT INTO {self.table} VALUES(?,?,?)', (record['id'], record['version'], json.dumps(record, allow_nan=False)))
        return record

    def _current(self, db, data, key='id'):
        positive(data['expected_version'])
        current = self._get(db, data[key])
        if current is None or current['version'] != data['expected_version']:
            raise ValueError('A versão mudou ou o registro não existe.')
        return current


class ResearchScopes(Revisions):
    table = 'job_research_scopes'
    purposes = {'company_dossier': 'company', 'career_exploration': 'career', 'source_discovery': 'source', 'job_search': 'search'}

    @classmethod
    def _target(cls, purpose, target):
        fields(target, ('kind', 'id'))
        text(target['id'])
        if not isinstance(purpose, str) or purpose not in cls.purposes or target['kind'] != cls.purposes[purpose]:
            raise ValueError('Finalidade e alvo incompatíveis.')

    @staticmethod
    def _control(db):
        if not table_exists(db, 'wf_control'):
            return 1, False
        row = db.execute('SELECT generation,stopped FROM wf_control WHERE id=1').fetchone()
        if row is None or type(row[0]) is not int or row[0] < 1 or row[1] not in (0, 1):
            raise ValueError('Controle operacional inválido.')
        return row[0], bool(row[1])

    def _validate(self, r):
        fields(r, ('id','version','purpose','target','question','urls','user_confirmation','generation','revoked','created_at'))
        text(r['id']); positive(r['version']); positive(r['generation'])
        self._target(r['purpose'], r['target'])
        text(r['question']); text(r['user_confirmation']); _date(r['created_at'])
        if type(r['revoked']) is not bool or not isinstance(r['urls'], list) or not r['urls']:
            raise ValueError('Escopo inválido.')
        for url in r['urls']:
            if _url(url) != url: raise ValueError('URL não normalizada.')

    def grant(self, data):
        fields(data, ('purpose','target','question','urls','user_confirmation'))
        self._target(data['purpose'], data['target'])
        if not isinstance(data['urls'], list): raise ValueError('URLs inválidas.')
        with self.profile._db(True) as db:
            generation, stopped = self._control(db)
            if stopped: raise ValueError('Pesquisa parada; retome antes de autorizar.')
            if data['purpose'] == 'job_search' and not self._current_search(db, data):
                raise ValueError('Os filtros ou sites mudaram. Confira o alcance atual antes de autorizar.')
            return self._save(db, dict(data, id=str(uuid4()), version=1, generation=generation, revoked=False, urls=list(dict.fromkeys(_url(u) for u in data['urls'])), created_at=datetime.now(timezone.utc).isoformat()))

    def _current_search(self, db, scope):
        """Reject stale targets even when the caller reuses an old check payload."""
        sections = self.profile._read(db)['sections']
        try:
            urls = list(dict.fromkeys(_url(url) for url in sections.get('sources', {}).get('urls', [])))
            target = job_search_target(sections.get('preferences', {}), urls)
            return scope['target'] == target and scope['urls'] == urls
        except ValueError:
            return False

    def check(self, data, *, db=None):
        fields(data, ('scope_id','expected_version','purpose','target','url'))
        positive(data['expected_version']); self._target(data['purpose'], data['target'])
        url = _url(data['url'])
        def check_conn(conn):
            r = self._get(conn, data['scope_id'])
            generation, stopped = self._control(conn)
            reason = ('not_found' if r is None else 'stale_version' if r['version'] != data['expected_version'] else 'revoked' if r['revoked'] else 'stopped' if stopped else 'stale_generation' if generation != r['generation'] else 'purpose_mismatch' if r['purpose'] != data['purpose'] else 'target_mismatch' if r['target'] != data['target'] else 'url_mismatch' if url not in r['urls'] else 'allowed')
            if reason == 'allowed' and r['purpose'] == 'job_search' and not self._current_search(conn, r):
                reason = 'stale_search'
            return dict(allowed=reason == 'allowed', reason=reason, scope_id=data['scope_id'], version=r['version'] if r else None)
        if db is not None: return check_conn(db)
        with self.profile._db() as conn: return check_conn(conn)

    def revoke(self, data):
        fields(data, ('scope_id','expected_version'))
        with self.profile._db(True) as db:
            r = self._current(db, data, 'scope_id')
            if r['revoked']: raise ValueError('Escopo já revogado.')
            return self._save(db, dict(r, version=r['version'] + 1, revoked=True))
