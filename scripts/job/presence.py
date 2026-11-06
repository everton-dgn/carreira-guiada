"""Optional professional-profile reviews, kept private across chat sessions."""

import hashlib
import json
from urllib.parse import urlsplit

from .profile import Profile
from .resumes import ResumeManager, _text

TOPICS = ('linkedin', 'github')
PUBLICATION_SECTIONS = {
    'linkedin': ('headline', 'about', 'experience', 'education', 'skills', 'featured'),
    'github': ('bio', 'profile_readme', 'pinned_repositories', 'repository_readme'),
}


def _source(topic, source):
    if topic not in TOPICS:
        raise ValueError('Perfil desconhecido.')
    source = _text(source, 'a origem do material revisado', 1000)
    if source != 'candidate_text':
        guidance = 'Use o link HTTPS do perfil, sem rastreadores ou credenciais, ou candidate_text para texto fornecido pela pessoa.'
        try:
            parsed = urlsplit(source)
            port = parsed.port
        except ValueError:
            raise ValueError(guidance) from None
        domain = 'linkedin.com' if topic == 'linkedin' else 'github.com'
        host = parsed.hostname or ''
        allowed_host = host in (domain, 'www.' + domain) or (topic == 'linkedin' and host.endswith('.linkedin.com'))
        if (parsed.scheme != 'https' or not allowed_host
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or port not in (None, 443) or not parsed.path.strip('/')):
            raise ValueError(guidance)
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

    def _save(self, change, validate=None):
        with self.profile._db(True) as db:
            state = self._read(db)
            if validate is not None:
                validate(db)
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
        confirmation = _text(confirmation, 'a escolha confirmada da pessoa', 500)
        return self._save(lambda state: state.update(decision=decision, topics=topics, confirmation=confirmation))

    def source(self, topic, source, material=None):
        source = _source(topic, source)
        if material is not None:
            material = _text(material, 'o material fornecido pela pessoa', 50_000)
        def change(state):
            if state['decision'] != 'now' or topic not in state['topics']:
                raise ValueError('A revisão deste perfil ainda não foi escolhida pela pessoa.')
            previous = state['reviews'].get(topic, {})
            link = _link(previous) if source == 'candidate_text' else source
            old_material = state.get('materials', {}).get(topic)
            new_material = {'content': material, 'source': source} if material is not None else None
            changed_link = bool(previous) and link != _link(previous)
            changed_material = new_material is not None and new_material != old_material
            if previous and not changed_link and not (changed_material and previous.get('content')):
                previous['link'] = link
                if not previous.get('content'):
                    previous['source'] = source
            else:
                _archive(state, topic, previous)
                state['reviews'][topic] = {'source': source, 'link': link, 'content': None,
                                          'version': previous.get('version', -1) + 1, 'reviewed': False}
            if changed_link or changed_material:
                if old_material:
                    state.setdefault('material_history', {}).setdefault(topic, []).append(old_material)
                    state['materials'].pop(topic)
                if new_material is not None:
                    state.setdefault('materials', {})[topic] = new_material
        return self._save(change)

    def draft(self, topic, content, source, fact_ids=None):
        source = _source(topic, source)
        content = _text(content, 'as sugestões para o perfil', 50_000)
        if fact_ids is not None:
            if (not isinstance(fact_ids, list) or any(type(item) is not str for item in fact_ids)
                    or len(set(fact_ids)) != len(fact_ids)):
                raise ValueError('Informe uma lista de identificadores únicos de fatos confirmados.')
            fact_ids = list(fact_ids)
        def validate(db):
            for fact_id in fact_ids or []:
                exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_facts'").fetchone()
                row = db.execute('SELECT confirmed FROM resume_facts WHERE id=?', (fact_id,)).fetchone() if exists else None
                if not row or row[0] != 1 or ResumeManager._revocation(db, fact_id):
                    raise ValueError('Use somente identificadores exatos de fatos atuais e confirmados.')
        def change(state):
            if state['decision'] != 'now' or topic not in state['topics']:
                raise ValueError('A revisão deste perfil ainda não foi escolhida pela pessoa.')
            previous = state['reviews'].get(topic, {})
            if (previous.get('content') == content and previous.get('source') == source
                    and previous.get('fact_ids') == fact_ids):
                return
            _archive(state, topic, previous)
            link = _link(previous) if source == 'candidate_text' else source
            state['reviews'][topic] = {'content': content, 'source': source, 'link': link,
                                      'version': previous.get('version', 0) + 1, 'reviewed': False, 'fact_ids': fact_ids}
        return self._save(change, validate)

    def finish(self, topic, version, confirmation):
        if topic not in TOPICS or type(version) is not int:
            raise ValueError('Informe o perfil e a versão revisada.')
        confirmation = _text(confirmation, 'a confirmação de revisão da pessoa', 500)
        def change(state):
            review = state['reviews'].get(topic)
            if state['decision'] != 'now' or topic not in state['topics'] or not review or not review.get('content') or review['version'] != version:
                raise ValueError('As sugestões mudaram ou ainda não existem. Confira a versão atual.')
            review['reviewed'] = True
            review['confirmation'] = confirmation
        return self._save(change)

    def status(self):
        state = self.get()
        pending = [topic for topic in state['topics'] if not state['reviews'].get(topic, {}).get('reviewed')] if state['decision'] == 'now' else []
        return {'decision': state['decision'], 'topics': state['topics'], 'pending': pending,
                'next_topic': pending[0] if pending else None,
                'reviews': {topic: {'version': review['version'], 'reviewed': review['reviewed']}
                            for topic, review in state['reviews'].items()},
                'publication_authorized': False}

    def publication(self, payload):
        """Validate the exact reviewed text; consent is recorded by Workflow."""
        fields = {'topic', 'version', 'section', 'destination', 'visibility', 'content_sha256'}
        if not isinstance(payload, dict) or set(payload) != fields:
            raise ValueError('publication: informe perfil, versão, seção, destino, visibilidade e hash do texto.')
        topic = payload['topic']
        if not isinstance(topic, str) or topic not in TOPICS or type(payload['version']) is not int:
            raise ValueError('publication: informe o perfil e a versão revisada.')
        if payload['section'] not in PUBLICATION_SECTIONS[topic] or payload['visibility'] not in ('public', 'connections', 'private'):
            raise ValueError('publication: confira a seção e a visibilidade escolhidas pela pessoa.')
        destination = _source(topic, payload['destination'])
        state = self.get()
        review = state['reviews'].get(topic, {})
        if (state['decision'] != 'now' or topic not in state['topics'] or not review.get('reviewed')
                or not review.get('content') or review.get('version') != payload['version']):
            raise ValueError('publication: as sugestões mudaram; confira e aprove a versão atual antes de publicar.')
        if destination == 'candidate_text' or destination != _link(review):
            raise ValueError('publication: o destino precisa ser o link conferido nesta revisão.')
        digest = hashlib.sha256(review['content'].encode()).hexdigest()
        if payload['content_sha256'] != digest:
            raise ValueError('publication: o texto difere da versão revisada; confira o conteúdo exato.')
        return {**payload, 'destination': destination}
