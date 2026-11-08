"""A saved handoff note, never evidence that an executor is still running."""
import json
from datetime import datetime, timezone

from .profile import Profile
from .resumes import _text

PHASES = ('onboarding', 'resume', 'presence', 'practice', 'career', 'company', 'offers', 'research', 'fill', 'email', 'followup', 'waiting', 'stopped')
ACTIVITIES = ('prepare', 'curriculum', 'presence', 'practice', 'career', 'company', 'offers', 'search', 'models')
CONDITIONS = ('recorded', 'ready', 'waiting_user', 'waiting_tool', 'paused', 'completed', 'needs_verification')
DEPENDENCIES = {'login': 'Entre na conta pela aba preservada, sem enviar sua senha no chat.',
                'answer': 'Responda à pergunta atual desta atividade.',
                'upload': 'Anexe o arquivo solicitado no chat.',
                'review': 'Confira o material antes de aprová-lo.',
                'verify': 'Confira o resultado no destino antes de repetir a ação.',
                'tool': 'Falta conferir o retorno da ferramenta.'}
PHASE_ACTIVITY = {'onboarding': 'prepare', 'resume': 'curriculum', 'presence': 'presence',
                  'practice': 'practice', 'career': 'career', 'company': 'company', 'offers': 'offers'}


def activity_of(note):
    """Scope legacy notes by phase without treating them as current instructions."""
    return note.get('activity') or PHASE_ACTIVITY.get(note['phase'], 'search')


def _exists(db, table):
    """Inspect optional tables without initializing a candidate workspace."""
    return db is not None and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()


def _read_notes(db, tolerate_invalid=False):
    """Read additive scoped notes and retain a newer legacy writer's note."""
    notes = {}
    if _exists(db, 'job_checkpoints'):
        for activity, value, sequence in db.execute('SELECT activity,value,sequence FROM job_checkpoints'):
            try:
                note = _decode(value)
                if activity != activity_of(note):
                    raise ValueError('O contexto da nota de retomada precisa de reparo.')
            except ValueError:
                if tolerate_invalid:
                    continue
                raise
            notes[activity] = (note, sequence)
    if _exists(db, 'job_checkpoint'):
        row = db.execute('SELECT value FROM job_checkpoint WHERE id=1').fetchone()
        if row:
            try:
                note = _decode(row[0])
            except ValueError:
                if tolerate_invalid:
                    return notes
                raise
            activity = activity_of(note)
            if activity not in notes or note['saved_at'] > notes[activity][0]['saved_at']:
                sequence = max((pair[1] for pair in notes.values()), default=0) + 1
                notes[activity] = (note, sequence)
    return notes


def _decode(value):
    """Reject malformed optional state without altering its saved content."""
    try:
        note = json.loads(value)
        if not isinstance(note, dict) or not isinstance(note.get('saved_at'), str):
            raise ValueError('registro incompleto')
        fields = {key: value for key, value in note.items() if key not in {'saved_at', 'campaign_generation'}}
        _validate(fields)
        return note
    except (TypeError, KeyError, ValueError) as exc:
        raise ValueError('A nota de retomada precisa de reparo; o conteúdo foi preservado.') from exc


def checkpoints(root, tolerate_invalid=False):
    """Return the last note per activity, preserving legacy content verbatim."""
    with Profile(root)._db() as db:
        return {key: value[0] for key, value in _read_notes(db, tolerate_invalid).items()}


def _validate(data):
    """Validate optional context without accepting permissions or external instructions."""
    required = {'phase', 'summary', 'next_action', 'needs_user'}
    optional = {'activity', 'condition', 'dependency'}
    if not isinstance(data, dict) or not required <= set(data) or set(data) - required - optional:
        raise ValueError('Informe phase, summary, next_action e needs_user; contexto opcional: activity, condition e dependency.')
    if data['phase'] not in PHASES or type(data['needs_user']) is not bool:
        raise ValueError('Confira a etapa e se existe uma ação que depende da pessoa.')
    if 'activity' in data and data['activity'] not in ACTIVITIES:
        raise ValueError('Atividade de retomada desconhecida.')
    if 'condition' in data and data['condition'] not in CONDITIONS:
        raise ValueError('Condição de retomada desconhecida.')
    condition = data.get('condition')
    if condition and condition != 'recorded' and (condition == 'waiting_user') != data['needs_user']:
        raise ValueError('A condição deve indicar quando a espera depende da pessoa.')
    expected = PHASE_ACTIVITY.get(data['phase'])
    if expected and 'activity' in data and data['activity'] != expected:
        raise ValueError('A etapa deve pertencer à atividade informada.')
    result = {**data, 'summary': _text(data['summary'], 'o progresso comprovado', 1000),
              'next_action': _text(data['next_action'], 'o próximo passo seguro', 1000)}
    if 'dependency' in data:
        dependency = data['dependency']
        if not isinstance(dependency, dict) or not {'reason'} <= set(dependency) or set(dependency) - {'reason', 'reference', 'due_at'} or not isinstance(dependency['reason'], str) or dependency['reason'] not in DEPENDENCIES:
            raise ValueError('A dependência precisa de reason conhecido; reference e due_at são opcionais.')
        if dependency['reason'] in {'login', 'answer', 'upload', 'review'} and not data['needs_user']:
            raise ValueError('Esta dependência exige ação da pessoa.')
        if dependency['reason'] == 'tool' and data['needs_user']:
            raise ValueError('Espera por ferramenta não é uma ação da pessoa.')
        result['dependency'] = dict(dependency)
        if 'reference' in dependency:
            result['dependency']['reference'] = _text(dependency['reference'], 'a referência da pendência', 150)
        if 'due_at' in dependency:
            try:
                date = datetime.fromisoformat(dependency['due_at'])
                if date.tzinfo is None:
                    raise ValueError('fuso ausente')
            except (ValueError, TypeError) as exc:
                raise ValueError('Informe um prazo com data, hora e fuso.') from exc
    return result


def save_note(db, data, legacy=False):
    """Store one note inside the caller's transaction, retaining other activities."""
    previous = _read_notes(db, tolerate_invalid=True)
    if _exists(db, 'job_checkpoints'):
        current = db.execute('SELECT value FROM job_checkpoints WHERE activity=?', (activity_of(data),)).fetchone()
        if current:
            _decode(current[0])
    if legacy and _exists(db, 'job_checkpoint'):
        current = db.execute('SELECT value FROM job_checkpoint WHERE id=1').fetchone()
        if current:
            _decode(current[0])
    db.execute('CREATE TABLE IF NOT EXISTS job_checkpoints (activity TEXT PRIMARY KEY, value TEXT NOT NULL, sequence INTEGER NOT NULL)')
    for key, (note, sequence) in previous.items():
        db.execute('INSERT OR REPLACE INTO job_checkpoints VALUES (?,?,?)', (key, json.dumps(note, ensure_ascii=False), sequence))
    sequence = db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM job_checkpoints').fetchone()[0]
    if activity_of(data) == 'search':
        row = db.execute('SELECT generation FROM wf_control WHERE id=1').fetchone() if _exists(db, 'wf_control') else None
        data['campaign_generation'] = row[0] if row else 1
    db.execute('INSERT OR REPLACE INTO job_checkpoints VALUES (?,?,?)',
               (activity_of(data), json.dumps(data, ensure_ascii=False), sequence))
    if legacy:
        db.execute('CREATE TABLE IF NOT EXISTS job_checkpoint (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO job_checkpoint VALUES (1, ?)', (json.dumps(data, ensure_ascii=False),))


def checkpoint(root, data=None, activity=None):
    """Read or save an additive scoped note; reading never migrates old state.

    The four-field legacy payload remains supported. New context fields are
    optional and never grant permission, prove execution or confirm a result.
    """
    profile = Profile(root)
    if activity is not None and activity not in ACTIVITIES:
        raise ValueError('Atividade de retomada desconhecida.')
    if data is not None:
        data = _validate(data)
        if activity is not None and activity_of(data) != activity:
            raise ValueError('A atividade selecionada deve corresponder à nota.')
        data['saved_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with profile._db(data is not None) as db:
        if data is not None:
            save_note(db, data, legacy='activity' not in data)
            return data
        notes = _read_notes(db)
        if activity:
            return notes.get(activity, (None, 0))[0]
        return max(notes.values(), key=lambda pair: pair[1])[0] if notes else None
