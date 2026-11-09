"""Private interview practice with versioned answers and external feedback."""
import json
import re
from uuid import uuid4
from datetime import datetime, timezone

from .profile import Profile
from .resumes import _text
from .practice_questions import CATALOG, EXERCISES, HINTS, LABELS


# Heuristic filter for interview answers only. Technical answers may explain
# concepts ("token: JWT de curta duração"); real-looking values are refused.
# It can miss credentials or refuse harmless text: it is not a detector.
_ANSWER_ASSIGNMENT = re.compile(r"(?i)\b(?:password|passwd|senha|token|cookie|secret|segredo|api[_ -]?key|chave(?: de api)?|access[_ -]?key|client[_ -]?secret)\s*([:=])((?:[^\n;!?.]|\.(?=\S))*)")
# Prose markers: a conceptual description reads as a phrase, not as a value.
_CONNECTORS = frozenset('a de do da dos das com sem para por e ou em no na nos nas que of with for and or the in to'.split())
_CONCEPTS = frozenset(('jwt', 'opaco', 'opaque', 'httponly', 'samesite', 'csrf', 'assinado', 'signed', 'criptografado', 'criptografada', 'encrypted', 'hash', 'bcrypt', 'argon2', 'guardada', 'armazenada', 'rotacionada', 'rotacionado'))
_TECHNICAL_IDENTIFIER = re.compile(r'(?i)(?:sha-?(?:1|224|256|384|512)|[hre]s(?:256|384|512)|argon2(?:id|i|d)?|oauth2)\Z')
_ANSWER_CREDENTIAL = re.compile(
    r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*"
    r"|\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"
    r"|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,})"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|\bhttps?://[^\s/:@]+:[^\s/@]+@")
_ANSWER_DOCUMENT = re.compile(r"(?i)\b(?:cpf|rg|cnh|passaporte|passport)\b\s*(?:n[º°o.]*\s*)?[:=]?\s*\d|\b\d{3}\.?\d{3}\.?\d{3}-\d{2}\b")
_ANSWER_BLOCKED = ('A resposta não foi salva porque parece conter senha, código de acesso ou número de documento. '
                   'Troque o valor real por uma descrição, como "token: JWT de curta duração". '
                   'Esta conferência é automática e pode errar; não cole credenciais nem documentos no treino.')


def _looks_secret(value):
    value = value.strip('.,;:!?)]}')
    if value[:1] in ('"', "'", '`'):
        return True
    letters, digits = re.search(r'[A-Za-z]', value), re.search(r'\d', value)
    return bool(letters and digits and len(value) >= 6 and not _TECHNICAL_IDENTIFIER.fullmatch(value)) or len(value) >= 20


def _conceptual(separator, clause):
    """Narrow exception: 'token: JWT de curta duração'. Any '=' or bare value is refused."""
    words = clause.split()
    return (separator == ':' and len(words) >= 3 and words[0].casefold().rstrip(',') in _CONCEPTS
            and not any(_looks_secret(word) for word in words)
            and any(word.casefold().strip(',()') in _CONNECTORS for word in words[1:]))


def _answer_text(value, name, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Informe {name} como texto, com até {limit} caracteres.")
    if (_ANSWER_CREDENTIAL.search(value) or _ANSWER_DOCUMENT.search(value)
            or any(not _conceptual(match.group(1), match.group(2)) for match in _ANSWER_ASSIGNMENT.finditer(value))):
        raise ValueError(_ANSWER_BLOCKED)
    return value.strip()


def _optional(value, name, limit):
    if value is None or value == '':
        return None
    return _text(value, name, limit)


class Practice:
    def __init__(self, root):
        self.profile = Profile(root)

    @staticmethod
    def catalog():
        return {track: [{'id': key, 'question': question, 'objective': objective}
                        for key, question, objective in questions]
                for track, questions in CATALOG.items()}

    @staticmethod
    def _read(db):
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE name='job_practice'").fetchone():
            return {'decision': None, 'sessions': []}
        row = db.execute('SELECT value FROM job_practice WHERE id=1').fetchone()
        return json.loads(row[0]) if row else {'decision': None, 'sessions': []}

    def get(self):
        with self.profile._db() as db:
            return self._read(db)

    def _save(self, change):
        with self.profile._db(True) as db:
            state = self._read(db)
            change(state)
            db.execute('CREATE TABLE IF NOT EXISTS job_practice (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_practice VALUES (1, ?)', (json.dumps(state, ensure_ascii=False, allow_nan=False),))
        return self.status()

    @staticmethod
    def _session(state, session_id, active=True):
        session = next((s for s in state['sessions'] if s['id'] == session_id), None)
        if session is None or (active and session['phase'] == 'finished'):
            raise ValueError('Treino não encontrado ou encerrado.')
        return session

    @staticmethod
    def _current(session, question_id):
        if session['phase'] != 'questions' or session['index'] >= len(session['questions']):
            raise ValueError('Não há pergunta atual.')
        question = session['questions'][session['index']]
        if question['id'] != question_id:
            raise ValueError('A pergunta informada não é a pergunta atual.')
        return question

    def status(self, session_id=None):
        state = self.get()
        if session_id is None:
            session = next((s for s in reversed(state['sessions']) if s['phase'] != 'finished'), None)
            if session is None and state['sessions']:
                session = state['sessions'][-1]
        else:
            session = self._session(state, session_id, active=False)
        if session is None:
            return {'decision': state['decision'], 'session_id': None, 'phase': 'idle', 'question': None,
                    'next_step': 'choose', 'message': 'Você escolheu treinar. Podemos começar por uma apresentação curta com ajuda ou escolher outro tema.' if state['decision'] == 'now' else 'Você pode treinar agora, depois ou pular.'}
        phase = session['phase']
        question = session['questions'][session['index']] if phase == 'questions' else None
        if phase == 'questions':
            current = question['attempts'][-1] if question['attempts'] else None
            step = 'answer' if current is None else ('feedback' if current['kind'] == 'answer' and session['mode'] == 'coach' and current['feedback'] is None else 'advance')
            message = {'answer': 'Vamos por partes. Você pode responder, pedir uma dica ou pular.',
                       'feedback': 'Sua resposta está salva. Vou preparar a devolutiva antes da próxima pergunta.',
                       'advance': 'A etapa está salva. Você pode tentar novamente ou seguir para a próxima pergunta.'}[step]
        elif phase == 'feedback':
            step = 'feedback' if any(q['attempts'] and q['attempts'][-1]['kind'] == 'answer' and q['attempts'][-1]['feedback'] is None for q in session['questions']) else 'finish'
            message = 'As perguntas terminaram. Vou conferir as respostas e preparar a devolutiva.' if step == 'feedback' else 'Respostas e devolutivas salvas. Vou preparar o fechamento do treino.'
        else:
            step = 'report'
            message = 'Treino encerrado antes do final.' if session['completion'] == 'ended_early' else 'Percurso de treino concluído.'
            message += '\n' + session['report']['text'] + '\nPróximo exercício: ' + session['report']['next_steps']
        visible = None
        if state['decision'] in ('later', 'skip') and phase != 'finished':
            message = 'Seu treino está guardado. Você pode seguir com a busca e pedir para retomar o treino quando quiser.'
        if question:
            visible = {k: question[k] for k in ('id', 'question', 'objective')}
            visible['attempt'] = question['attempts'][-1] if question['attempts'] else None
            if session['mode'] == 'mock' and visible['attempt']:
                visible['attempt'] = dict(visible['attempt'], feedback=None)
        return {'decision': state['decision'], 'session_id': session['id'], 'phase': phase,
                'next_step': step, 'message': message, 'question': visible,
                'track': session['track'], 'label': LABELS[session['track']], 'mode': session['mode'],
                'context': session['context'], 'position': min(session['index'] + 1, len(session['questions'])),
                'total': len(session['questions']), 'completion': session['completion']}

    def choose(self, decision):
        if decision not in ('now', 'later', 'skip'):
            raise ValueError('Escolha agora, depois ou pular.')
        return self._save(lambda state: state.update(decision=decision))

    def start(self, track, mode, context=None, area=None, level=None, short=False, question_ids=None):
        if not isinstance(track, str) or track not in CATALOG or mode not in ('coach', 'mock') or type(short) is not bool:
            raise ValueError('Informe uma trilha, modo e duração válidos.')
        context = _optional(context, 'o contexto', 20000) or EXERCISES.get(track)
        area = _optional(area, 'a área', 500)
        level = _optional(level, 'o nível', 500)
        bank = {item[0]: item for item in CATALOG[track]}
        if question_ids is not None and (not isinstance(question_ids, list) or not question_ids
                or any(not isinstance(key, str) or key not in bank for key in question_ids)
                or len(question_ids) != len(set(question_ids))):
            raise ValueError('Escolha perguntas existentes da trilha, sem repetição.')
        questions = [bank[key] for key in question_ids] if question_ids else CATALOG[track]
        questions = questions[:1] if short else questions
        session_id = uuid4().hex
        def change(state):
            if any(s['phase'] != 'finished' for s in state['sessions']):
                raise ValueError('Encerre ou retome o treino em andamento.')
            if len(state['sessions']) >= 500:
                raise ValueError('Limite de treinos atingido.')
            state['decision'] = 'now'
            state['sessions'].append({'id': session_id, 'track': track, 'mode': mode, 'context': context,
                'area': area, 'level': level, 'short': short, 'phase': 'questions', 'index': 0,
                'questions': [{'id': k, 'question': q, 'objective': o, 'attempts': []} for k, q, o in questions],
                'completion': None, 'report': None, 'ended_early': False})
        self._save(change)
        return self.status(session_id)

    def hint(self, session_id, question_id):
        session = self._session(self.get(), session_id)
        self._current(session, question_id)
        return {'session_id': session_id, 'question_id': question_id,
                'message': 'Tudo bem não saber. Comece pelo que você já conhece e peça ajuda para organizar a resposta.',
                'example': HINTS[session['track']]}

    def answer(self, session_id, question_id, text, *, attempt_id=None, origin=None, user_confirmation=None):
        """Save a response with optional human provenance and idempotent attempt ID."""
        if attempt_id is not None:
            attempt_id = _text(attempt_id, "o identificador da tentativa", 200)
        if origin not in (None, "person", "agent", "unknown"):
            raise ValueError("Origem inválida.")
        origin = origin or "unknown"
        if user_confirmation is not None:
            user_confirmation = _text(user_confirmation, "a confirmação", 2000)
        if origin == "person" and not user_confirmation:
            raise ValueError("A autoria da pessoa exige confirmação textual.")
        text = _answer_text(text, 'a resposta', 20000)
        if text.casefold().strip(' .!?') in ('não sei', 'nao sei'):
            return self.hint(session_id, question_id)
        def change(state):
            if attempt_id is not None:
                for session in state['sessions']:
                    for question in session['questions']:
                        for attempt in question['attempts']:
                            if attempt.get('attempt_id') == attempt_id:
                                if (session['id'] != session_id or question['id'] != question_id or attempt['text'] != text or attempt.get('origin') != origin or attempt.get('user_confirmation') != user_confirmation):
                                    raise ValueError('Identificador de tentativa já usado com outros dados.')
                                return
            q = self._current(self._session(state, session_id), question_id)
            if attempt_id is None and q['attempts'] and q['attempts'][-1]['kind'] == 'answer' and q['attempts'][-1]['text'] == text:
                return
            if len(q['attempts']) >= 50:
                raise ValueError('Limite de tentativas atingido.')
            q['attempts'].append({'version': len(q['attempts']) + 1, 'kind': 'answer', 'text': text, 'feedback': None, 'attempt_id': attempt_id, 'origin': origin, 'user_confirmation': user_confirmation, 'recorded_at': datetime.now(timezone.utc).isoformat()})
        self._save(change)
        return self.status(session_id)

    def skip(self, session_id, question_id):
        def change(state):
            q = self._current(self._session(state, session_id), question_id)
            if q['attempts']:
                raise ValueError('A pergunta já tem uma tentativa; avance ou responda novamente.')
            q['attempts'].append({'version': 1, 'kind': 'skip', 'text': None, 'feedback': None})
        self._save(change)
        return self.status(session_id)

    def feedback(self, session_id, question_id, version, strengths, improvements, suggestion, exercise):
        if type(version) is not int:
            raise ValueError('Informe a versão da resposta.')
        data = {k: _text(v, k, 10000) for k, v in {'strengths': strengths, 'improvements': improvements, 'suggestion': suggestion, 'exercise': exercise}.items()}
        def change(state):
            s = self._session(state, session_id)
            if s['mode'] == 'mock' and s['phase'] != 'feedback':
                raise ValueError('A devolutiva do simulado fica para o final.')
            if s['mode'] == 'coach' and s['phase'] == 'questions':
                q = self._current(s, question_id)
            else:
                q = next((q for q in s['questions'] if q['id'] == question_id), None)
            if not q or not q['attempts'] or q['attempts'][-1]['kind'] != 'answer' or q['attempts'][-1]['version'] != version:
                raise ValueError('Resposta ou versão atual não encontrada.')
            q['attempts'][-1]['feedback'] = data
        self._save(change)
        return self.status(session_id)

    def advance(self, session_id, question_id):
        def change(state):
            s = self._session(state, session_id)
            q = self._current(s, question_id)
            if not q['attempts']:
                raise ValueError('Responda ou pule antes de avançar.')
            a = q['attempts'][-1]
            if s['mode'] == 'coach' and a['kind'] == 'answer' and a['feedback'] is None:
                raise ValueError('Registre a devolutiva da resposta atual antes de avançar.')
            s['index'] += 1
            if s['index'] == len(s['questions']):
                s['phase'] = 'feedback'
        self._save(change)
        return self.status(session_id)

    def end_questions(self, session_id):
        """Stop asking questions and prepare feedback without claiming completion."""
        def change(state):
            s = self._session(state, session_id)
            if s['phase'] != 'questions':
                raise ValueError('A etapa de perguntas já terminou.')
            s['ended_early'] = True
            s['phase'] = 'feedback'
        self._save(change)
        return self.status(session_id)

    def finish(self, session_id, report, next_steps):
        report = _text(report, 'o relatório', 20000)
        next_steps = _text(next_steps, 'os próximos passos', 10000)
        def change(state):
            s = self._session(state, session_id)
            if any(q['attempts'] and q['attempts'][-1]['kind'] == 'answer' and q['attempts'][-1]['feedback'] is None for q in s['questions']):
                if s['mode'] == 'mock' and s['phase'] == 'questions':
                    raise ValueError('Encerre primeiro as perguntas com end-questions; depois registre a devolutiva e finalize o simulado.')
                raise ValueError('Registre a devolutiva das respostas antes de encerrar.')
            answered_all = all(q['attempts'] for q in s['questions'])
            s['completion'] = 'completed' if answered_all and not s['ended_early'] else 'ended_early'
            s['phase'] = 'finished'
            s['report'] = {'text': report, 'next_steps': next_steps}
        self._save(change)
        return self.status(session_id)
