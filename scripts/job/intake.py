"""Persist the CV conversation, including explicit skips, across chat restarts."""
import json
from datetime import datetime, timezone

from .profile import Profile
from .resumes import ResumeManager

QUESTIONS = [
    ('education', 'O que você estudou ou está estudando?', 'Pode dizer a escola ou curso e o ano, se lembrar. Se preferir, pode pular'),
    ('experience', 'Conte sobre o trabalho mais recente que você fez.', 'Pode ser emprego, trabalho informal, projeto ou voluntariado. Diga onde, quando e o que fazia. Se nunca trabalhou, diga isso'),
    ('skills', 'O que você sabe fazer que pode ajudar no trabalho?', 'Por exemplo, atender pessoas, organizar documentos, cozinhar ou usar uma ferramenta. Pode dizer que ainda não sabe'),
    ('languages', 'Você fala ou entende algum idioma além do português?', 'Pode dizer nenhum. Se souber outro, conte o que consegue fazer com ele, sem precisar dar um nome ao nível'),
    ('extra', 'Quer acrescentar algo ao currículo?', 'Pode ser um curso, outro trabalho, um projeto ou a cidade onde busca emprego. Pode dizer que terminou'),
]


class Intake:
    def __init__(self, root):
        self.profile = Profile(root)

    @staticmethod
    def _read(db):
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE name='job_intake'").fetchone():
            return {'mode': None, 'answers': {}}
        row = db.execute('SELECT value FROM job_intake WHERE id=1').fetchone()
        return json.loads(row[0]) if row else {'mode': None, 'answers': {}}

    def get(self):
        with self.profile._db() as db:
            return self._read(db)

    def _save(self, change, obsolete_fact=None, select_preparation=False):
        """Persist intake changes and retire affected resumes in one transaction."""
        with self.profile._db(True) as db:
            state = self._read(db)
            change(state)
            db.execute('CREATE TABLE IF NOT EXISTS job_intake (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_intake VALUES (1, ?)', (json.dumps(state, ensure_ascii=False),))
            if select_preparation:
                exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='job_checkpoint'").fetchone()
                row = db.execute('SELECT value FROM job_checkpoint WHERE id=1').fetchone() if exists else None
                point = json.loads(row[0]) if row else None
                if not point or point['phase'] == 'career':
                    from .checkpoint import _read_notes, save_note
                    saved = _read_notes(db, tolerate_invalid=True).get('curriculum')
                    point = saved[0] if saved else {
                        'phase': 'resume', 'summary': 'Você escolheu preparar seu currículo.',
                        'next_action': 'Continuar a preparação do currículo.', 'needs_user': True,
                        'saved_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
                    save_note(db, point, legacy=True)
            if obsolete_fact and db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_versions'").fetchone():
                for resume_id, fact_ids in db.execute('SELECT id, fact_ids FROM resume_versions'):
                    if obsolete_fact in json.loads(fact_ids):
                        db.execute("UPDATE resume_versions SET status='retired', approved_at=NULL WHERE id=?", (resume_id,))
        return self.status()

    def choose(self, mode, route=None):
        """Select CV preparation; an explicit route preserves operational checkpoints."""
        if mode not in ('create', 'import'):
            raise ValueError('Escolha criar o currículo ou anexar um arquivo.')
        if route not in (None, 'curriculum', 'prepare'):
            raise ValueError('Rota de preparação desconhecida.')
        def change(state):
            """Change the selected intake mode while preserving all saved answers."""
            state['mode'] = mode
            if route is not None:
                state['route'] = route
        return self._save(change, select_preparation=route != 'curriculum')

    def answer(self, field, text):
        if field not in {item[0] for item in QUESTIONS}:
            raise ValueError('Pergunta de currículo desconhecida.')
        if text is not None and (not isinstance(text, str) or not text.strip()):
            raise ValueError('Registre a resposta em texto ou null quando a pessoa preferir pular.')
        if self.get()['mode'] != 'create':
            raise ValueError('Primeiro registre que a pessoa quer criar o currículo.')
        previous = self.get()['answers'].get(field)
        if previous and previous['text'] == text:
            return self.status()
        fact = ResumeManager(self.profile.root).add_fact(text, 'candidate:intake-' + field, True) if text is not None else None
        return self._save(lambda state: state['answers'].update({field: {'text': text, 'fact_id': fact['id'] if fact else None}}),
                          obsolete_fact=previous['fact_id'] if previous else None)

    def select_existing_route(self, route):
        """Switch an explicit direct route without changing operational checkpoints."""
        if route not in ('career', 'practice', 'plan', 'progress'):
            raise ValueError('Rota desconhecida.')
        if self.get().get('route') in ('curriculum', 'career', 'practice', 'search', 'prepare', 'company', 'presence', 'offers', 'models', 'plan', 'progress'):
            self.remember_route(route)

    def remember_route(self, route):
        """Persist an explicit menu choice without granting or resuming actions."""
        if route not in ('curriculum', 'career', 'practice', 'search', 'prepare', 'company', 'presence', 'offers', 'models', 'plan', 'progress'):
            raise ValueError('Escolha uma das atividades disponíveis no menu.')
        return self._save(lambda state: state.update(route=route))

    def status(self):
        state = self.get()
        questions = [{'field': field, 'question': question, 'example': example}
                     for field, question, example in QUESTIONS if field not in state['answers']] if state['mode'] == 'create' else []
        return {'mode': state['mode'], 'complete': state['mode'] == 'create' and not questions,
                'question': questions[0] if questions else None, 'questions': questions,
                'fact_ids': [answer['fact_id'] for answer in state['answers'].values() if answer['fact_id']]}
