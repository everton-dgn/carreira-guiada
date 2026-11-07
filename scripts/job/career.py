"""Private career cycles. Answers are null or nonempty strings up to 4000 chars.

All updates take id and expected_version. Proposal basis references current answer
versions; prose remains the caller's responsibility, not a semantic fact checker.
"""
import json
from uuid import uuid4
from .profile import Profile
from .policy import obj
from .due_diligence import _date, _url
from .resumes import _text

QUESTIONS = dict(zip(('goal', 'priorities', 'experiences', 'constraints', 'available_time'), (
    'O que você gostaria de descobrir sobre seu trabalho? Pode dizer não sei.',
    'O que importa para você no trabalho? Por exemplo, aprender ou ter estabilidade.',
    'O que você já experimentou fazer? Pode dizer que ainda não sabe.',
    'Existe alguma limitação que precisamos considerar? Pode dizer não sei.',
    'Quanto tempo você pode reservar? Por exemplo, uma hora por semana, ou não sei.')))


def text(value):
    _text(value, 'a resposta', 4000)


def integer(value, maximum=1000000000):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError('Número inteiro fora dos limites.')


def texts(value):
    if not isinstance(value, list) or len(value) > 30:
        raise ValueError('Informe uma lista de até 30 textos.')
    for item in value: text(item)


class CareerGuide:
    def __init__(self, root):
        self.profile = Profile(root)
        self.root = root

    def _rows(self, db):
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE name='career_revisions' AND type='table'").fetchone():
            return []
        result = []
        for sid, version, raw in db.execute('SELECT id,version,value FROM career_revisions ORDER BY rowid'):
            try:
                s = json.loads(raw)
                self._validate(s)
                if s['id'] != sid or s['version'] != version: raise ValueError('Identidade inválida.')
            except (TypeError, KeyError, json.JSONDecodeError) as exc:
                raise ValueError('Registro de carreira inválido.') from exc
            result.append(s)
        return result

    def _validate(self, s):
        keys = ('id','version','phase','paused','answers','alternatives','selection','experiment','reflection')
        obj(s, keys, keys)
        text(s['id']); integer(s['version'])
        if type(s['paused']) is not bool or s['phase'] not in ('questions','alternatives','experiment','reflection','finished'):
            raise ValueError('Estado de carreira inválido.')
        obj(s['answers'], QUESTIONS)
        for a in s['answers'].values():
            obj(a, ('value','version'), ('value','version')); integer(a['version'])
            if a['version'] > s['version']: raise ValueError('Resposta futura.')
            if a['value'] is not None: text(a['value'])
        self._alternatives(s, s['alternatives'], None, allow_empty=True)
        if s['selection'] is not None:
            obj(s['selection'], ('alternative_id','user_confirmation'), ('alternative_id','user_confirmation'))
            text(s['selection']['user_confirmation'])
            if s['selection']['alternative_id'] not in [a['id'] for a in s['alternatives']]: raise ValueError('Escolha inválida.')
        if s['experiment'] is not None: self._experiment(s['experiment'])
        if s['reflection'] is not None: self._reflection(s['reflection'])
        expected = ('finished' if s['reflection'] is not None else 'reflection' if s['experiment'] is not None else 'experiment' if s['selection'] is not None else 'alternatives' if s['alternatives'] else 'questions')
        if s['phase'] != expected or (s['alternatives'] and len(s['answers']) != 5) or (s['experiment'] and not s['selection']) or (s['reflection'] and not s['experiment']):
            raise ValueError('Fase inconsistente.')

    def _alternatives(self, s, alternatives, db, allow_empty=False):
        if not isinstance(alternatives, list) or not (0 if allow_empty else 1) <= len(alternatives) <= 3: raise ValueError('Informe de uma a três alternativas.')
        ids = set()
        for a in alternatives:
            required = ('id','title','gains','costs','basis','gaps')
            obj(a, (*required,'market_evidence'), required)
            text(a['id']); text(a['title'])
            if a['id'] in ids: raise ValueError('Alternativa repetida.')
            ids.add(a['id'])
            for key in ('gains','costs','gaps'): texts(a[key])
            if not isinstance(a['basis'], list) or not 1 <= len(a['basis']) <= 5: raise ValueError('Base da alternativa obrigatória.')
            for b in a['basis']:
                obj(b, ('answer_field','answer_version'), ('answer_field','answer_version'))
                integer(b['answer_version'])
                if not isinstance(b['answer_field'], str) or b['answer_field'] not in s['answers'] or s['answers'][b['answer_field']]['version'] != b['answer_version']: raise ValueError('Base desatualizada.')
            evidence = a.get('market_evidence', [])
            if not isinstance(evidence, list) or len(evidence) > 30: raise ValueError('Evidências inválidas.')
            for e in evidence:
                keys = ('statement','url','checked_at','scope_id','scope_version','limitations')
                obj(e, keys, keys)
                for key in ('statement','url','checked_at','scope_id'): text(e[key])
                integer(e['scope_version']); texts(e['limitations'])
                _date(e['checked_at'])
                _url(e['url'])
                if db is not None:
                    from .research_scope import ResearchScopes
                    check = ResearchScopes(self.root).check({'scope_id':e['scope_id'],'expected_version':e['scope_version'],'purpose':'career_exploration','target':{'kind':'career','id':s['id']},'url':e['url']}, db=db)
                    if check.get('allowed') is not True: raise ValueError('Escopo não autoriza a evidência.')

    def _experiment(self, d):
        keys = ('activity','duration_days','time_budget_minutes','learning_criterion','user_confirmation')
        obj(d, keys, keys)
        for key in ('activity','learning_criterion','user_confirmation'): text(d[key])
        integer(d['duration_days'], 90); integer(d['time_budget_minutes'], 43200)
        if d['time_budget_minutes'] > d['duration_days'] * 1440: raise ValueError('Orçamento excede a duração.')

    def _reflection(self, d):
        obj(d, ('observations','learned','next_decision'), ('observations','learned','next_decision'))
        for key in ('observations','learned'):
            if d[key] is not None: text(d[key])
        if d['next_decision'] not in ('continue','change','defer'): raise ValueError('Decisão inválida.')

    def _save(self, db, s):
        self._validate(s)
        db.execute('CREATE TABLE IF NOT EXISTS career_revisions (id TEXT, version INTEGER, value TEXT NOT NULL, PRIMARY KEY(id,version))')
        db.execute('INSERT INTO career_revisions VALUES (?,?,?)', (s['id'],s['version'],json.dumps(s, allow_nan=False)))
        return s

    def start(self, data):
        obj(data, ())
        with self.profile._db(True) as db:
            latest = {s['id']:s for s in self._rows(db)}
            active = [s for s in latest.values() if s['phase'] != 'finished']
            if active: return active[-1]
            return self._save(db, dict(id=uuid4().hex, version=1, phase='questions', paused=False, answers={}, alternatives=[], selection=None, experiment=None, reflection=None))

    def get(self, id, version=None):
        text(id)
        if version is not None: integer(version)
        with self.profile._db() as db:
            matches = [s for s in self._rows(db) if s['id']==id and (version is None or s['version']==version)]
            return matches[-1] if matches else None

    def status(self, id=None):
        if id is not None: text(id)
        with self.profile._db() as db: rows = self._rows(db)
        latest = {s['id']:s for s in rows}
        active = [s for s in latest.values() if s['phase'] != 'finished']
        s = latest.get(id) if id else active[-1] if active else rows[-1] if rows else None
        question = next(({'field':f,'question':q} for f,q in QUESTIONS.items() if f not in s['answers']), None) if s and s['phase']=='questions' else None
        phase = s['phase'] if s else 'idle'
        message = {'idle':'Vamos descobrir um próximo passo que faça sentido para você. Não precisa ter currículo ou cargo definido.',
                   'questions': 'Vamos seguir uma pergunta por vez. Você pode responder "não sei".',
                   'alternatives': 'As opções estão salvas. Qual delas você quer experimentar? Podemos também deixar para depois.',
                   'experiment': 'Vamos combinar uma atividade pequena e quanto tempo você quer reservar.',
                   'reflection': 'Quando terminar a atividade, conte o que fez e o que aprendeu. Podemos continuar outro dia.',
                   'finished': 'Registramos o que você aprendeu. Podemos usar isso no próximo passo ou explorar outro caminho.'}[phase]
        if s and s['paused']:
            message = 'Seu guia de carreira está pausado. Diga "continuar meu guia de carreira" quando quiser retomar.'
            question = None
        elif phase == 'questions' and question is None: message = 'Já temos suas respostas. Vou comparar até três caminhos com você.'
        return dict(count=len(latest), session=s, phase=phase, paused=s['paused'] if s else False, question=question, message=message)

    def _mutate(self, action, data):
        fields = {'answer':('field','value'), 'propose':('alternatives',), 'choose':('alternative_id','user_confirmation'), 'experiment':('activity','duration_days','time_budget_minutes','learning_criterion','user_confirmation'), 'reflect':('observations','learned','next_decision'), 'pause':(), 'resume':()}[action]
        obj(data, ('id','expected_version',*fields), ('id','expected_version',*fields))
        text(data['id']); integer(data['expected_version'])
        with self.profile._db(True) as db:
            rows = self._rows(db)
            matches = [s for s in rows if s['id']==data['id']]
            if not matches: raise ValueError('Sessão inexistente.')
            s = matches[-1]
            if s['version'] != data['expected_version']: raise ValueError('Versão desatualizada; releia a sessão.')
            if s['paused'] and action != 'resume': raise ValueError('Retome a sessão antes de alterar.')
            d = {k:data[k] for k in fields}
            if action in ('pause','resume'):
                if s['paused'] == (action=='pause'): return s
                s['paused'] = action=='pause'
            elif action == 'answer':
                if not isinstance(d['field'], str) or d['field'] not in QUESTIONS: raise ValueError('Pergunta desconhecida.')
                if d['value'] is not None: text(d['value'])
                if d['field'] in s['answers'] and s['answers'][d['field']]['value']==d['value']: return s
                latest = {row['id']: row for row in rows}
                if s['phase'] == 'finished' and any(row['id'] != s['id'] and row['phase'] != 'finished' for row in latest.values()):
                    raise ValueError('Há outro guia de carreira em andamento. Conclua esse ciclo antes de reabrir o anterior; o histórico foi preservado.')
                s['answers'][d['field']] = {'value':d['value'], 'version':s['version']+1}
                s.update(phase='questions', alternatives=[], selection=None, experiment=None, reflection=None)
            elif action == 'propose':
                if s['phase'] not in ('questions','alternatives') or len(s['answers']) != 5: raise ValueError('Responda às cinco perguntas antes de propor.')
                self._alternatives(s,d['alternatives'],db)
                s.update(alternatives=d['alternatives'], phase='alternatives')
            elif action == 'choose':
                if s['phase'] != 'alternatives': raise ValueError('Prepare alternativas antes de escolher.')
                text(d['user_confirmation'])
                if d['alternative_id'] not in [a['id'] for a in s['alternatives']]: raise ValueError('Alternativa inexistente.')
                s.update(selection=d, phase='experiment')
            elif action == 'experiment':
                if s['phase'] != 'experiment': raise ValueError('Confirme uma escolha primeiro.')
                self._experiment(d); s.update(experiment=d, phase='reflection')
            else:
                if s['phase'] != 'reflection': raise ValueError('Combine um experimento primeiro.')
                self._reflection(d); s.update(reflection=d, phase='finished')
            s['version'] += 1
            return self._save(db,s)

    def answer(self, data): return self._mutate('answer', data)
    def propose(self, data): return self._mutate('propose', data)
    def choose(self, data): return self._mutate('choose', data)
    def experiment(self, data): return self._mutate('experiment', data)
    def reflect(self, data): return self._mutate('reflect', data)
    def pause(self, data): return self._mutate('pause', data)
    def resume(self, data): return self._mutate('resume', data)
