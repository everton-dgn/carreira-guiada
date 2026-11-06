"""A saved handoff note, never evidence that an executor is still running."""
import json
from datetime import datetime, timezone

from .profile import Profile
from .resumes import _text

PHASES = ('onboarding', 'resume', 'presence', 'research', 'fill', 'email', 'followup', 'waiting', 'stopped')


def checkpoint(root, data=None):
    profile = Profile(root)
    if data is not None:
        if set(data) != {'phase', 'summary', 'next_action', 'needs_user'} or data['phase'] not in PHASES or type(data['needs_user']) is not bool:
            raise ValueError('Informe phase, summary, next_action e needs_user desta etapa.')
        data = {**data, 'summary': _text(data['summary'], 'o progresso comprovado', 1000),
                'next_action': _text(data['next_action'], 'o próximo passo seguro', 1000),
                'saved_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    with profile._db(data is not None) as db:
        if data is not None:
            db.execute('CREATE TABLE IF NOT EXISTS job_checkpoint (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_checkpoint VALUES (1, ?)', (json.dumps(data, ensure_ascii=False),))
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE name='job_checkpoint'").fetchone():
            return None
        row = db.execute('SELECT value FROM job_checkpoint WHERE id=1').fetchone()
        return json.loads(row[0]) if row else None
