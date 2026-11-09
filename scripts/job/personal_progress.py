"""Private, versioned records of explicitly confirmed personal progress."""
import copy
import hashlib
import json
from datetime import datetime

from .practice import Practice
from .profile import Profile

POINTS_RULE_VERSION = 1
POINTS_PER_PRACTICE = 10


def _object(value, allowed, required=()):
    """Reject unknown fields and missing required fields in a payload."""
    if not isinstance(value, dict) or set(value) - set(allowed) or not set(required) <= set(value):
        raise ValueError('Campos inválidos ou ausentes.')


def _text(value):
    """Return bounded nonempty text without coercing booleans or other types."""
    if not isinstance(value, str) or not value.strip() or len(value) > 10000:
        raise ValueError('Informe um texto não vazio de até 10000 caracteres.')
    return value.strip()


def _minutes(value):
    """Accept an unknown duration or a bounded integer number of minutes."""
    if value is not None and (type(value) is not int or not 0 <= value <= 1440):
        raise ValueError('Informe minutos entre 0 e 1440 ou deixe em aberto.')
    return value


def _fingerprint(value):
    """Hash canonical JSON to detect changes to quoted practice evidence."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _attempt(db, source):
    """Resolve an exact session, question and attempt version from private storage."""
    _object(source, ('kind', 'session_id', 'question_id', 'version'), ('kind', 'session_id', 'question_id', 'version'))
    if source['kind'] != 'practice' or type(source['version']) is not int or source['version'] < 1:
        raise ValueError('Referência de treino inválida.')
    _text(source['session_id']); _text(source['question_id'])
    state = Practice._read(db)
    for session in state['sessions']:
        if session['id'] == source['session_id']:
            for question in session['questions']:
                if question['id'] == source['question_id']:
                    for attempt in question['attempts']:
                        if attempt['version'] == source['version']:
                            return attempt
    raise ValueError('Tentativa de treino não encontrada.')


class PersonalProgress:
    """Track voluntary participation without turning it into application permission."""
    def __init__(self, root):
        """Bind progress records to the private profile without creating storage."""
        self.profile = Profile(root)

    @staticmethod
    def _read(db):
        """Read the latest revision or return the disabled first-use state."""
        if db is not None and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_progress_revisions'").fetchone():
            row = db.execute('SELECT value FROM personal_progress_revisions ORDER BY version DESC LIMIT 1').fetchone()
            if row:
                return json.loads(row[0])
        return {'version': 0, 'points_rule_version': POINTS_RULE_VERSION, 'preferences': {'mode': 'off', 'appearance': 'auto', 'motion': False}, 'events': [], 'milestones': [], 'corrections': []}

    def get(self):
        """Read preferences and history without initializing private storage."""
        with self.profile._db() as db:
            return self._read(db)

    def history(self):
        """Return immutable revisions, including corrected and disabled states."""
        with self.profile._db() as db:
            if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_progress_revisions'").fetchone():
                return []
            return [json.loads(row[0]) for row in db.execute('SELECT value FROM personal_progress_revisions ORDER BY version')]

    def _mutate(self, data, allowed, required, change):
        """Append a validated revision while rejecting stale competing changes."""
        _object(data, allowed, required)
        if type(data['expected_version']) is not int or data['expected_version'] < 0:
            raise ValueError('Informe a versão esperada.')
        with self.profile._db(True) as db:
            state = self._read(db)
            # Identical event retries remain safe even with a stale version.
            if data['expected_version'] != state['version']:
                if change == self._record and any(e['event_id'] == data.get('event_id') and e['original'] == {k: v for k, v in data.items() if k != 'expected_version'} for e in state['events']):
                    return state
                raise ValueError('Seu acompanhamento foi atualizado. Confira a versão atual antes de salvar; nada foi sobrescrito.')
            if change(state, data, db) is False:
                return state
            state['version'] += 1
            db.execute('CREATE TABLE IF NOT EXISTS personal_progress_revisions (version INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('INSERT INTO personal_progress_revisions VALUES (?, ?)', (state['version'], json.dumps(state, ensure_ascii=False, allow_nan=False)))
            return state

    def configure(self, data):
        """Save the person's explicit tracking and presentation preferences."""
        def change(s, d, db):
            """Validate preferences before updating the in-transaction state."""
            if d['mode'] not in ('off', 'tracking', 'achievements', 'points'):
                raise ValueError('Modo inválido.')
            if 'appearance' in d and d['appearance'] not in ('auto', 'plain'):
                raise ValueError('Aparência inválida.')
            if 'motion' in d and type(d['motion']) is not bool:
                raise ValueError('Movimento deve ser verdadeiro ou falso.')
            s['preferences'].update({k: v for k, v in d.items() if k != 'expected_version'})
        return self._mutate(data, ('expected_version', 'mode', 'appearance', 'motion'), ('expected_version', 'mode'), change)

    def _record(self, s, d, db):
        """Append a confirmed event, rejecting duplicate attempts and conflicting IDs."""
        original = {k: copy.deepcopy(v) for k, v in d.items() if k != 'expected_version'}
        for e in s['events']:
            if e['event_id'] == d['event_id']:
                if e['original'] == original:
                    return False
                raise ValueError('Identificador de evento já usado com outros dados.')
        if s['preferences']['mode'] == 'off':
            raise ValueError('O acompanhamento está desativado. Você pode manter assim ou escolher como acompanhar suas práticas.')
        for key in ('event_id', 'activity', 'user_confirmation'):
            _text(d[key])
        _minutes(d['reported_minutes'])
        if 'note' in d and d['note'] is not None:
            _text(d['note'])
        try:
            date = datetime.fromisoformat(d['occurred_at'])
            if date.utcoffset() is None:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError('Informe data ISO com fuso horário.') from None
        source = d['source']
        if not isinstance(source, dict):
            raise ValueError('Fonte inválida.')
        if source.get('kind') == 'practice':
            attempt = _attempt(db, source)
            if attempt['kind'] != 'answer' or attempt.get('origin', 'unknown') != 'person' or not attempt.get('user_confirmation'):
                raise ValueError('A tentativa não tem autoria pessoal confirmada.')
            if any(e['source'] == source for e in s['events']):
                raise ValueError('Esta tentativa já foi registrada.')
        else:
            _object(source, ('kind', 'description'), ('kind', 'description'))
            if source['kind'] != 'user_report':
                raise ValueError('Fonte inválida.')
            _text(source['description'])
        s['events'].append(dict(original, original=original, revoked=False))

    def record(self, data):
        """Record one confirmed activity with idempotent event and attempt identity."""
        return self._mutate(data, ('expected_version', 'event_id', 'activity', 'source', 'user_confirmation', 'reported_minutes', 'occurred_at', 'note'), ('expected_version', 'event_id', 'activity', 'source', 'user_confirmation', 'reported_minutes', 'occurred_at'), self._record)

    def correct(self, data):
        """Correct duration or revoke an event while retaining its original record."""
        def change(s, d, db):
            """Apply a correction and mark affected milestone evidence for review."""
            _text(d['reason']); _text(d['event_id'])
            if 'reported_minutes' not in d and 'revoked' not in d:
                raise ValueError('Informe uma correção.')
            if 'reported_minutes' in d: _minutes(d['reported_minutes'])
            if 'revoked' in d and type(d['revoked']) is not bool: raise ValueError('Revogação inválida.')
            event = next((e for e in s['events'] if e['event_id'] == d['event_id']), None)
            if event is None: raise ValueError('Evento não encontrado.')
            changed = any(k in d and event[k] != d[k] for k in ('reported_minutes', 'revoked'))
            for k in ('reported_minutes', 'revoked'):
                if k in d: event[k] = d[k]
            if changed:
                for milestone in s['milestones']:
                    if d['event_id'] in milestone['event_ids']:
                        milestone['needs_review'] = True
            s['corrections'].append({k: copy.deepcopy(v) for k, v in d.items() if k != 'expected_version'})
        return self._mutate(data, ('expected_version', 'event_id', 'reason', 'reported_minutes', 'revoked'), ('expected_version', 'event_id', 'reason'), change)

    def milestone(self, data):
        """Save a contestable observation or comparison backed by quoted evidence."""
        def change(s, d, db):
            """Validate events and quoted evidence before saving a contestable milestone."""
            if s['preferences']['mode'] not in ('achievements', 'points'):
                raise ValueError('A pessoa precisa escolher conquistas antes de registrar um marco.')
            for k in ('milestone_id', 'title', 'criterion', 'assessment'): _text(d[k])
            if d['kind'] not in ('participation', 'learning'): raise ValueError('Tipo de marco inválido.')
            if any(m['milestone_id'] == d['milestone_id'] for m in s['milestones']): raise ValueError('Marco já existe.')
            ids = d['event_ids']
            if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)): raise ValueError('Informe eventos distintos.')
            events = [next((e for e in s['events'] if e['event_id'] == i and not e['revoked']), None) for i in ids]
            if any(e is None for e in events): raise ValueError('Evento ativo não encontrado.')
            m = {k: copy.deepcopy(v) for k, v in d.items() if k != 'expected_version'}
            m.update(needs_review=False, fingerprints=[])
            if d['kind'] == 'learning':
                evidence = d.get('evidence')
                _object(evidence, ('basis', 'event_id', 'answer_excerpt', 'feedback_excerpt', 'previous_event_id', 'previous_answer_excerpt', 'previous_feedback_excerpt'), ('basis', 'event_id', 'answer_excerpt', 'feedback_excerpt'))
                if evidence['basis'] not in ('observation', 'comparison'):
                    raise ValueError('Indique se a avaliação observa uma tentativa ou compara duas.')
                event = next((e for e in events if e['event_id'] == evidence['event_id']), None)
                if not event or event['source']['kind'] != 'practice': raise ValueError('A aprendizagem exige tentativa vinculada.')
                attempt = _attempt(db, event['source'])
                answer = _text(evidence['answer_excerpt']); feedback = _text(evidence['feedback_excerpt'])
                if answer not in attempt['text'] or not attempt['feedback'] or not any(feedback in v for v in attempt['feedback'].values()): raise ValueError('Trecho não encontrado na resposta ou devolutiva.')
                if evidence['basis'] == 'comparison' and not evidence.get('previous_event_id'):
                    raise ValueError('Informe a tentativa anterior para comparar melhora.')
                if evidence['basis'] == 'observation' and evidence.get('previous_event_id'):
                    raise ValueError('Use comparação para avaliar duas tentativas.')
                if evidence.get('previous_event_id'):
                    previous = next((e for e in events if e['event_id'] == evidence['previous_event_id'] and e['source']['kind'] == 'practice' and e['event_id'] != evidence['event_id']), None)
                    if not previous: raise ValueError('Tentativa anterior não encontrada nos eventos.')
                    old_source = previous['source']
                    if (old_source['session_id'] != event['source']['session_id'] or old_source['question_id'] != event['source']['question_id'] or old_source['version'] >= event['source']['version']):
                        raise ValueError('A comparação exige tentativa anterior da mesma pergunta.')
                    old = _attempt(db, old_source)
                    old_answer = _text(evidence.get('previous_answer_excerpt'))
                    old_feedback = _text(evidence.get('previous_feedback_excerpt'))
                    if old_answer not in old['text'] or not old['feedback'] or not any(old_feedback in v for v in old['feedback'].values()):
                        raise ValueError('Trechos anteriores não encontrados.')
                    m['fingerprints'].append({'source': old_source, 'answer': _fingerprint(old['text']), 'feedback': _fingerprint(old['feedback'])})
                m['fingerprints'].append({'source': event['source'], 'answer': _fingerprint(attempt['text']), 'feedback': _fingerprint(attempt['feedback'])})
            s['milestones'].append(m)
        return self._mutate(data, ('expected_version', 'milestone_id', 'kind', 'title', 'criterion', 'event_ids', 'assessment', 'evidence'), ('expected_version', 'milestone_id', 'kind', 'title', 'criterion', 'event_ids', 'assessment'), change)

    def contest(self, data):
        """Keep disagreement visible without deleting the original evaluation."""
        def change(s, d, db):
            """Record the stated objection without deleting the milestone history."""
            _text(d['reason']); _text(d['milestone_id'])
            m = next((m for m in s['milestones'] if m['milestone_id'] == d['milestone_id']), None)
            if m is None: raise ValueError('Marco não encontrado.')
            m['needs_review'] = True
            m.setdefault('contests', []).append(d['reason'])
        return self._mutate(data, ('expected_version', 'milestone_id', 'reason'), ('expected_version', 'milestone_id', 'reason'), change)

    def status(self):
        """Derive indicators from active evidence, never from time connected."""
        with self.profile._db() as db:
            s = self._read(db)
            mode = s['preferences']['mode']
            if mode == 'off':
                return {'mode': mode, 'version': s['version'], 'message': 'Acompanhamento desativado; histórico preservado.', 'next_step': 'configure', 'practice_count': None, 'reported_minutes': None, 'points': None, 'milestones': [], 'evidence_warnings': []}
            events = [e for e in s['events'] if not e['revoked']]
            count = sum(e['source']['kind'] == 'practice' for e in events)
            milestones = copy.deepcopy(s['milestones']) if mode in ('achievements', 'points') else []
            warnings = []
            for m in milestones:
                if any(not any(e['event_id'] == i for e in events) for i in m['event_ids']): m['needs_review'] = True
                for fp in m['fingerprints']:
                    try:
                        a = _attempt(db, fp['source'])
                        if _fingerprint(a['text']) != fp['answer'] or _fingerprint(a['feedback']) != fp['feedback']: m['needs_review'] = True
                    except ValueError:
                        m['needs_review'] = True
                if m['needs_review']: warnings.append('Marco ' + m['milestone_id'] + ' precisa de revisão.')
            return {'mode': mode, 'version': s['version'], 'message': 'Práticas confirmadas estão salvas. Você pode conferir, corrigir ou desativar o acompanhamento.', 'next_step': 'record', 'practice_count': count, 'reported_minutes': sum(e['reported_minutes'] for e in events if e['reported_minutes'] is not None), 'unreported_time_count': sum(e['reported_minutes'] is None for e in events), 'points': count * POINTS_PER_PRACTICE if mode == 'points' else None, 'points_rule_version': s.get('points_rule_version', POINTS_RULE_VERSION), 'milestones': milestones, 'evidence_warnings': warnings}
