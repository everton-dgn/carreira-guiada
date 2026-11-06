"""Optional professional-profile reviews, kept private across chat sessions."""

import json
from urllib.parse import urlsplit

from .profile import Profile
from .resumes import _text

TOPICS = ('linkedin', 'github')


def _source(topic, source):
    if topic not in TOPICS:
        raise ValueError('Perfil desconhecido.')
    source = _text(source, 'a origem do material revisado', 1000)
    if source != 'candidate_text':
        parsed = urlsplit(source)
        domain = 'linkedin.com' if topic == 'linkedin' else 'github.com'
        host = parsed.hostname or ''
        allowed_host = host in (domain, 'www.' + domain) or (topic == 'linkedin' and host.endswith('.linkedin.com'))
        if (parsed.scheme != 'https' or not allowed_host
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.port not in (None, 443) or not parsed.path.strip('/')):
            raise ValueError('Use o link HTTPS do perfil, sem rastreadores ou credenciais, ou candidate_text para texto fornecido pela pessoa.')
    return source


def _link(review):
    return review.get('link') or (review.get('source') if review.get('source') != 'candidate_text' else None)


def _archive(state, topic, previous):
    if previous.get('content'):
        state.setdefault('history', {}).setdefault(topic, []).append(dict(previous))


class Presence:
    def __init__(self, root):
        self.profile = Profile(root)

    @staticmethod
    def _read(db):
        empty = {'decision': None, 'topics': [], 'reviews': {}}
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE name='job_presence'").fetchone():
            return empty
        row = db.execute('SELECT value FROM job_presence WHERE id=1').fetchone()
        return json.loads(row[0]) if row else empty

    def get(self):
        with self.profile._db() as db:
            return self._read(db)

    def _save(self, change):
        with self.profile._db(True) as db:
            state = self._read(db)
            change(state)
            db.execute('CREATE TABLE IF NOT EXISTS job_presence (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_presence VALUES (1, ?)', (json.dumps(state, ensure_ascii=False),))
        return self.status()

    def choose(self, decision, topics, confirmation):
        if decision not in ('now', 'later', 'skip'):
            raise ValueError('Escolha revisar agora, deixar para depois ou pular.')
        if not isinstance(topics, list) or any(topic not in TOPICS for topic in topics) or len(topics) != len(set(topics)):
            raise ValueError('Escolha LinkedIn, GitHub ou ambos.')
        if decision == 'now' and not topics:
            raise ValueError('Informe qual perfil a pessoa quer revisar.')
        _text(confirmation, 'a escolha confirmada da pessoa', 500)
        return self._save(lambda state: state.update(decision=decision, topics=topics))

    def source(self, topic, source):
        source = _source(topic, source)
        def change(state):
            if state['decision'] != 'now' or topic not in state['topics']:
                raise ValueError('A revisão deste perfil ainda não foi escolhida pela pessoa.')
            previous = state['reviews'].get(topic, {})
            link = None if source == 'candidate_text' else source
            if previous and (link is None or _link(previous) == link):
                previous['link'] = _link(previous)
                return
            _archive(state, topic, previous)
            state['reviews'][topic] = {'source': source, 'link': link, 'content': None,
                                      'version': previous.get('version', -1) + 1, 'reviewed': False}
        return self._save(change)

    def draft(self, topic, content, source):
        source = _source(topic, source)
        content = _text(content, 'as sugestões para o perfil', 50_000)
        def change(state):
            if state['decision'] != 'now' or topic not in state['topics']:
                raise ValueError('A revisão deste perfil ainda não foi escolhida pela pessoa.')
            previous = state['reviews'].get(topic, {})
            if previous.get('content') == content and previous.get('source') == source:
                return
            _archive(state, topic, previous)
            link = _link(previous) if source == 'candidate_text' else source
            state['reviews'][topic] = {'content': content, 'source': source, 'link': link,
                                      'version': previous.get('version', 0) + 1, 'reviewed': False}
        return self._save(change)

    def finish(self, topic, version, confirmation):
        if topic not in TOPICS or type(version) is not int:
            raise ValueError('Informe o perfil e a versão revisada.')
        _text(confirmation, 'a confirmação de revisão da pessoa', 500)
        def change(state):
            review = state['reviews'].get(topic)
            if state['decision'] != 'now' or topic not in state['topics'] or not review or not review.get('content') or review['version'] != version:
                raise ValueError('As sugestões mudaram ou ainda não existem. Confira a versão atual.')
            review['reviewed'] = True
        return self._save(change)

    def status(self):
        state = self.get()
        pending = [topic for topic in state['topics'] if not state['reviews'].get(topic, {}).get('reviewed')] if state['decision'] == 'now' else []
        return {'decision': state['decision'], 'topics': state['topics'], 'pending': pending,
                'next_topic': pending[0] if pending else None,
                'reviews': {topic: {'version': review['version'], 'reviewed': review['reviewed']}
                            for topic, review in state['reviews'].items()},
                'publication_authorized': False}
