"""Versioned private personal plans."""
import json
import hashlib
from datetime import date
from uuid import uuid4

from .profile import Profile
from .policy import obj
from .resumes import _text
from .practice import Practice


def text(value):
    """Validate a bounded text supplied for a personal plan."""
    _text(value, 'o texto', 4000)


def integer(value, low=0, high=10080):
    """Reject booleans and values outside the documented integer range."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Informe um número inteiro dentro dos limites.')


def day(value):
    """Require a canonical ISO calendar date without inventing a timezone."""
    if not isinstance(value, str): raise ValueError('Informe uma data ISO válida.')
    try:
        if date.fromisoformat(value).isoformat() != value: raise ValueError()
    except ValueError as exc: raise ValueError('Informe uma data ISO válida.') from exc


class PersonalPlan:
    """Save personal plans independently from operational permissions and goals."""
    def __init__(self, root):
        """Bind plan storage to the private profile without initializing it."""
        self.profile = Profile(root)

    @staticmethod
    def _rows(db):
        """Read immutable plan revisions in insertion order when storage exists."""
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_plan_revisions'").fetchone(): return []
        return [json.loads(row[0]) for row in db.execute('SELECT value FROM personal_plan_revisions ORDER BY rowid')]

    @staticmethod
    def _save(db, plan):
        """Append one immutable revision after every validated change."""
        db.execute('CREATE TABLE IF NOT EXISTS personal_plan_revisions (id TEXT, version INTEGER, value TEXT NOT NULL, PRIMARY KEY(id,version))')
        db.execute('INSERT INTO personal_plan_revisions VALUES (?,?,?)', (plan['id'], plan['version'], json.dumps(plan, ensure_ascii=False, allow_nan=False)))
        return plan

    @staticmethod
    def _fingerprint(db, ref):
        """Bind advice to the exact practice answer and its editable feedback."""
        if ref['kind'] != 'practice':
            return None
        state = Practice._read(db)
        for session in state['sessions']:
            for question in session['questions']:
                if session['id'] == ref['session_id'] and question['id'] == ref['question_id']:
                    for attempt in question['attempts']:
                        if attempt['version'] == ref['version']:
                            return hashlib.sha256(json.dumps(attempt, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return None

    def _capture(self, db, refs):
        """Capture source versions without updating existing evidence implicitly."""
        return [{'reference': ref, 'digest': self._fingerprint(db, ref)} for ref in refs]

    @staticmethod
    def _reference(db, ref):
        """Validate a reference and check that its exact source revision exists."""
        if not isinstance(ref, dict): raise ValueError('Referência inválida.')
        if ref.get('kind') == 'career':
            obj(ref, ('kind','id','version'), ('kind','id','version'))
            text(ref['id']); integer(ref['version'], 1, 1000000000)
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='career_revisions'").fetchone(): return False
            return bool(db.execute('SELECT 1 FROM career_revisions WHERE id=? AND version=?', (ref['id'], ref['version'])).fetchone())
        if ref.get('kind') == 'practice':
            obj(ref, ('kind','session_id','question_id','version'), ('kind','session_id','question_id','version'))
            text(ref['session_id']); text(ref['question_id']); integer(ref['version'], 1, 1000000000)
            state = Practice._read(db)
            return any(a['version'] == ref['version'] for s in state['sessions'] if s['id'] == ref['session_id'] for q in s['questions'] if q['id'] == ref['question_id'] for a in q['attempts'])
        raise ValueError('Tipo de referência desconhecido.')

    def _fields(self, data, db):
        """Validate supplied plan fields and their stored source references."""
        if 'direction' in data and data['direction'] is not None: text(data['direction'])
        if 'weekly_minutes' in data and data['weekly_minutes'] is not None: integer(data['weekly_minutes'])
        if 'cycle' in data:
            c = data['cycle']; obj(c, ('title','review_on'), ('title',)); text(c['title'])
            if c.get('review_on') is not None: day(c['review_on'])
        if 'basis' in data:
            if not isinstance(data['basis'], list) or len(data['basis']) > 50: raise ValueError('Informe até 50 referências.')
            for ref in data['basis']:
                if not self._reference(db, ref): raise ValueError('Referência inexistente.')

    def start(self, data):
        """Reuse the current plan, or create an empty plan with confirmed choices."""
        fields = ('direction','weekly_minutes','cycle','basis')
        obj(data, fields)
        with self.profile._db(True) as db:
            self._fields(data, db)
            latest = {s['id']: s for s in self._rows(db)}
            active = [s for s in latest.values() if s['state'] != 'archived']
            if active: return active[-1]
            s = dict(id=uuid4().hex, version=1, state='active', direction=None, weekly_minutes=None, cycle=None, basis=[], actions=[], reflections=[])
            s.update(data)
            s['source_snapshots'] = self._capture(db, s['basis'])
            return self._save(db, s)

    def get(self, plan_id=None, version=None):
        """Read a chosen revision or the latest plan without creating a database."""
        if plan_id is not None: text(plan_id)
        if version is not None: integer(version, 1, 1000000000)
        with self.profile._db() as db: rows = self._rows(db)
        if plan_id is None and rows:
            latest = {s['id']: s for s in rows}
            active = [s for s in latest.values() if s['state'] != 'archived']
            plan_id = (active[-1] if active else rows[-1])['id']
        matches = [s for s in rows if s['id'] == plan_id and (version is None or s['version'] == version)]
        return matches[-1] if matches else None

    def history(self, plan_id):
        """Return the immutable revisions for one plan."""
        text(plan_id)
        with self.profile._db() as db: return [s for s in self._rows(db) if s['id'] == plan_id]

    def status(self, plan_id=None):
        """Project weekly capacity and stale sources without claiming execution."""
        s = self.get(plan_id)
        if not s: return dict(exists=False, id=None, version=None, state=None, message='Ainda não há plano.', next_action=None, next_step='Comece um plano.', budget=None, actions=[])
        periods = {}
        for a in s['actions']:
            if a['state'] not in ('planned','active') or a['period'] is None: continue
            periods.setdefault(a['period'], []).append(a['estimated_minutes'])
        budget = []
        for period, minutes in sorted(periods.items()):
            total = sum(minutes) if all(x is not None for x in minutes) else None
            remaining = None if total is None or s['weekly_minutes'] is None else max(0, s['weekly_minutes'] - total)
            over = None if total is None or s['weekly_minutes'] is None else max(0, total - s['weekly_minutes'])
            budget.append(dict(period=period, planned_minutes=total, remaining_minutes=remaining, over_by_minutes=over))
        with self.profile._db() as db:
            changed = []
            references = [(ref, None) for ref in s['basis']] + [(a['source'], a['id']) for a in s['actions'] if a.get('source') is not None]
            for ref, action_id in references:
                if ref['kind'] == 'career':
                    row = db.execute('SELECT MAX(version) FROM career_revisions WHERE id=?', (ref['id'],)).fetchone() if db and self._reference(db, ref) else (None,)
                    changed.append(dict(reference=ref, action_id=action_id, changed=row[0] != ref['version']))
                else:
                    state = Practice._read(db)
                    versions = [a['version'] for session in state['sessions'] if session['id']==ref['session_id'] for q in session['questions'] if q['id']==ref['question_id'] for a in q['attempts']]
                    snapshots = s.get('source_snapshots', []) if action_id is None else next(a for a in s['actions'] if a['id'] == action_id).get('source_snapshots', [])
                    captured = next((item['digest'] for item in snapshots if item['reference'] == ref), None)
                    stale = not versions or max(versions) != ref['version'] or captured is None or captured != self._fingerprint(db, ref)
                    changed.append(dict(reference=ref, action_id=action_id, changed=stale))
        pending = [a for a in s['actions'] if a['state'] in ('active', 'planned')]
        nxt = next((a for a in pending if a['state'] == 'active'), pending[0] if pending else None) if s['state'] == 'active' else None
        labels = {'active': 'em andamento', 'paused': 'pausado', 'archived': 'arquivado'}
        return dict(exists=True, id=s['id'], version=s['version'], state=s['state'], message='Plano ' + labels[s['state']] + '.', next_action=nxt, next_step=nxt['title'] if nxt else 'Revise o plano quando quiser.', budget=dict(weekly_minutes=s['weekly_minutes'], periods=budget, without_period=[a for a in s['actions'] if a['period'] is None and a['state'] in ('planned','active')]), actions=s['actions'], basis=changed, direction=s['direction'], cycle=s['cycle'])

    def _mutate(self, operation, data):
        """Apply one validated operation under optimistic version control."""
        fields = {'update':('direction','weekly_minutes','cycle','basis'), 'action':('action',), 'transition':('action_id','state','evidence'), 'review':('observation','next_step','decision'), 'pause':(), 'resume':(), 'archive':()}[operation]
        required = {'action':('action',), 'transition':('action_id','state'), 'review':('observation','next_step','decision')}.get(operation, ())
        obj(data, ('id','expected_version',*fields), ('id','expected_version',*required))
        text(data['id']); integer(data['expected_version'], 1, 1000000000)
        with self.profile._db(True) as db:
            matches = [s for s in self._rows(db) if s['id']==data['id']]
            if not matches: raise ValueError('Plano não encontrado. Confira os planos salvos antes de continuar.')
            s = matches[-1]
            if s['version'] != data['expected_version']: raise ValueError('Seu plano foi atualizado. Confira a versão atual antes de salvar; nada foi sobrescrito.')
            if s['state']=='archived': raise ValueError('Plano arquivado.')
            if operation == 'update':
                changes = {k:data[k] for k in fields if k in data}; self._fields(changes, db); s.update(changes)
                if 'basis' in changes:
                    s['source_snapshots'] = self._capture(db, changes['basis'])
            elif operation == 'action':
                a = data['action']; keys = ('id','activity','title','reason','criterion','estimated_minutes','period','smaller_step','if_then','source')
                obj(a, keys, ('id','activity','title','reason','criterion','estimated_minutes','period'))
                for k in ('id','activity','title','reason','criterion'): text(a[k])
                if a['activity'] not in ('prepare', 'curriculum', 'practice', 'career', 'presence', 'company', 'search', 'offers', 'models', 'study'):
                    raise ValueError('Escolha uma atividade do projeto ou estudo para esta ação.')
                for k in ('smaller_step','if_then'):
                    if k in a and a[k] is not None: text(a[k])
                if a['estimated_minutes'] is not None: integer(a['estimated_minutes'])
                if a['period'] is not None:
                    day(a['period'])
                    if date.fromisoformat(a['period']).weekday() != 0:
                        raise ValueError('Informe a segunda-feira que inicia a semana planejada.')
                if 'source' in a and a['source'] is not None and not self._reference(db, a['source']): raise ValueError('Referência inexistente.')
                a = dict(a)
                if 'source' in a:
                    a['source_snapshots'] = self._capture(db, [a['source']]) if a['source'] else []
                old = next((x for x in s['actions'] if x['id']==a['id']), None)
                if old and old['state'] != 'planned': raise ValueError('Só ações planejadas podem ser alteradas.')
                if old: old.update(a)
                else:
                    if len(s['actions']) >= 50: raise ValueError('Limite de ações atingido.')
                    s['actions'].append(dict(a, state='planned', evidence=None))
            elif operation == 'transition':
                text(data['action_id'])
                a = next((x for x in s['actions'] if x['id']==data['action_id']), None)
                if not a or data['state'] not in ('planned','active','completed','deferred','cancelled'): raise ValueError('Ação ou estado inválido.')
                evidence = data.get('evidence')
                if evidence is not None:
                    obj(evidence, ('kind','description','criterion','source'), ('kind','description','criterion'))
                    if evidence['kind'] not in ('user_report','source'): raise ValueError('Tipo de evidência inválido.')
                    text(evidence['description']); text(evidence['criterion'])
                    if evidence['kind']=='source' and ('source' not in evidence or not self._reference(db, evidence['source'])): raise ValueError('Fonte inexistente.')
                if data['state']=='completed' and evidence is None: raise ValueError('Conclusão exige evidência.')
                if data['state'] == 'completed' and evidence['criterion'] != a['criterion']:
                    raise ValueError('Confira a conclusão pelo mesmo critério combinado para esta ação.')
                a.update(state=data['state'], evidence=evidence)
            elif operation == 'review':
                text(data['observation']); text(data['next_step'])
                if data['decision'] not in ('continue','adjust','finish'): raise ValueError('Decisão inválida.')
                s['reflections'].append({k:data[k] for k in fields})
            else:
                if operation == 'resume' and s['state'] != 'paused': raise ValueError('Plano não está pausado.')
                if operation == 'pause' and s['state'] != 'active': raise ValueError('Plano não está ativo.')
                s['state'] = {'pause':'paused','resume':'active','archive':'archived'}[operation]
            s['version'] += 1
            return self._save(db, s)

    def update(self, data):
        """Revise only the explicitly supplied direction, budget, cycle or sources."""
        return self._mutate('update', data)

    def action(self, data):
        """Add or revise a planned action without opening its target activity."""
        return self._mutate('action', data)

    def transition(self, data):
        """Change an action state, requiring evidence for its agreed criterion."""
        return self._mutate('transition', data)

    def review(self, data):
        """Record a reflection independently from pausing or archiving the plan."""
        return self._mutate('review', data)

    def pause(self, data):
        """Pause the personal plan without changing campaign state."""
        return self._mutate('pause', data)

    def resume(self, data):
        """Resume an explicitly paused plan without resuming external actions."""
        return self._mutate('resume', data)

    def archive(self, data):
        """Keep the final revision and allow a separate new plan."""
        return self._mutate('archive', data)
