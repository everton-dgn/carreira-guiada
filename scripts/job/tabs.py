"""Shared reservations for browser work, independent of any browser provider."""
import json
from uuid import uuid4

from .profile import Profile
from .resumes import _text


class Tabs:
    def __init__(self, root):
        self.profile = Profile(root)

    @staticmethod
    def _read(db):
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE name='job_tabs'").fetchone():
            return {}
        row = db.execute('SELECT value FROM job_tabs WHERE id=1').fetchone()
        return json.loads(row[0]) if row else {}

    def status(self):
        with self.profile._db() as db:
            tabs = self._read(db)
            limit = Profile._read(db)['sections'].get('limits', {}).get('browser_tabs', 2)
        active = {key: value for key, value in tabs.items() if value['active']}
        return {'limit': limit, 'in_use': len(active), 'available': max(0, limit - len(active)), 'tabs': active}

    def _change(self, change):
        with self.profile._db(True) as db:
            tabs = self._read(db)
            limit = Profile._read(db)['sections'].get('limits', {}).get('browser_tabs', 2)
            result = change(tabs, limit)
            db.execute('CREATE TABLE IF NOT EXISTS job_tabs (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_tabs VALUES (1, ?)', (json.dumps(tabs, ensure_ascii=False),))
        return result

    def reserve(self, owner, purpose, owned):
        owner, purpose = _text(owner, 'o responsável', 100), _text(purpose, 'a finalidade da aba', 200)
        if type(owned) is not bool:
            raise ValueError('Informe se a aba será criada pelo agente ou se já pertence à pessoa.')
        def change(tabs, limit):
            if sum(tab['active'] for tab in tabs.values()) >= limit:
                raise ValueError('Limite de abas atingido. Reutilize uma aba segura ou preserve as pendências e siga outra atividade.')
            key = uuid4().hex
            tabs[key] = {'owner': owner, 'purpose': purpose, 'owned': owned, 'external_id': None,
                         'protected': True, 'active': True}
            return {'reservation': key, **tabs[key]}
        return self._change(change)

    def update(self, reservation, external_id, protected, evidence):
        reservation = _text(reservation, 'a reserva da aba', 64)
        external_id = _text(external_id, 'o identificador observado da aba', 200)
        _text(evidence, 'a conferência do estado da aba', 500)
        if type(protected) is not bool:
            raise ValueError('Informe se há formulário ou ação pendente nesta aba.')
        def change(tabs, limit):
            tab = tabs.get(reservation)
            if not tab or not tab['active']:
                raise ValueError('Reserva de aba ausente ou encerrada.')
            if any(key != reservation and value['active'] and value['external_id'] == external_id for key, value in tabs.items()):
                raise ValueError('Esta aba já tem uma reserva ativa.')
            if tab['external_id'] not in (None, external_id):
                raise ValueError('A reserva pertence a outra aba. Confira a identidade antes de continuar.')
            tab.update(external_id=external_id, protected=protected)
            return {'reservation': reservation, **tab}
        return self._change(change)

    def release(self, reservation, outcome, evidence):
        reservation = _text(reservation, 'a reserva da aba', 64)
        if outcome not in ('closed', 'not_created', 'returned_to_user', 'already_absent'):
            raise ValueError('Informe aba fechada, criação não realizada ou aba devolvida à pessoa.')
        evidence = _text(evidence, 'a evidência conferida na ferramenta', 500)
        def change(tabs, limit):
            tab = tabs.get(reservation)
            if not tab or not tab['active']:
                raise ValueError('Reserva de aba ausente ou encerrada.')
            if outcome == 'not_created' and tab['external_id'] is not None:
                raise ValueError('A aba foi identificada. Confira o destino antes de liberar a reserva.')
            if outcome == 'already_absent' and not tab['external_id']:
                raise ValueError('Confira a identidade da aba antes de registrar que ela não existe mais.')
            if outcome == 'closed' and (not tab['owned'] or tab['protected'] or not tab['external_id']):
                raise ValueError('Não feche aba da pessoa, aba com estado desconhecido ou com pendência.')
            if outcome == 'returned_to_user' and tab['owned']:
                raise ValueError('Abas abertas pelo agente continuam no limite enquanto estiverem abertas.')
            tab.update(active=False, outcome=outcome, evidence=evidence)
            return {'reservation': reservation, 'active': False}
        return self._change(change)
