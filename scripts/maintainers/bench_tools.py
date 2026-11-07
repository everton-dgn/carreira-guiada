"""Small shared tool adapter: models still choose and verify every operation."""
import hashlib
import fcntl
import json
import time
from .bench_candidate import OWNER, call
from .bench_site import JOBS, ORIGIN


def session_path(directory):
    phase = json.loads((directory / 'state.json').read_text())['phase']
    return directory / f'session-phase-{phase}.json'


def session_record(directory, update=None):
    """Serialize executor completion and in-flight tool timeout updates."""
    with session_path(directory).open('r+') as out:
        fcntl.flock(out, fcntl.LOCK_EX)
        session = json.load(out)
        if update is not None:
            update(session)
            out.seek(0)
            json.dump(session, out)
            out.truncate()
            out.flush()
        return session


def begin_session(directory):
    """Arm one four-minute session without allowing its deadline to reset."""
    now = time.time()
    phase = json.loads((directory / 'state.json').read_text())['phase']
    session = {'phase': phase, 'started_at': now, 'deadline': now + 240,
               'finished_at': None, 'timed_out': False}
    with session_path(directory).open('x') as out:
        out.write(json.dumps(session))
    return session


def finish_session(directory):
    """Preserve the first completion time and any previously observed timeout."""
    def finish(session):
        if session['finished_at'] is None:
            session['finished_at'] = time.time()
            session['timed_out'] |= session['finished_at'] >= session['deadline']
    return session_record(directory, finish)


class Tools:
    def __init__(self, directory, browser, require_session=False):
        self.directory, self.browser = directory, browser
        self.state = json.loads((directory / 'state.json').read_text())
        self.require_session = require_session
        if require_session:
            self.state['session_timing_required'] = True
            (directory / 'state.json').write_text(json.dumps(self.state))
        self.started = time.monotonic()
        self.count = 0

    def cli(self, args, data=None):
        return call(self.directory, args, data)

    def ownership(self):
        return {'owner': OWNER, 'generation': self.cli(['status'])['control']['generation']}

    def require(self, action_id, kind):
        action = self.cli(['action', 'show', action_id])
        if action['action'] != kind:
            raise ValueError('A autorização não corresponde a esta operação.')
        self.cli(['action', 'check', action_id], self.ownership())
        return action

    def invoke(self, data):
        start = time.monotonic()
        self.count += 1
        session = None
        path = session_path(self.directory)
        outside_deadline = False
        try:
            if self.count > 100:
                raise ValueError('Limite de 100 operações nesta fase.')
            if path.is_file():
                session = session_record(self.directory)
                outside_deadline = time.time() >= session['deadline']
                if outside_deadline or session['finished_at'] is not None or session['timed_out']:
                    raise ValueError('Sessão encerrada ou prazo de quatro minutos esgotado.')
            elif self.require_session:
                raise ValueError('O executor precisa iniciar a sessão com start-session.')
            result = self.dispatch(data)
            output = {'ok': True, 'result': result}
        except Exception as exc:
            output = {'ok': False, 'error': str(exc)[:1000]}
        if session is not None:
            outside_deadline = outside_deadline or time.time() >= session['deadline']
            if outside_deadline:
                session_record(self.directory, lambda current: current.update(timed_out=True))
                output = {**output, 'ok': False, 'outside_session_deadline': True,
                          'error': 'Operação fora do prazo; efeitos observados ficam sem crédito.'}
        event = {'phase': self.state['phase'], 'sequence': self.count, 'elapsed': round(time.monotonic() - self.started, 3), 'duration': round(time.monotonic() - start, 3), 'input': data, 'output': output}
        with (self.directory / 'events.jsonl').open('a') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
        return output

    def dispatch(self, data):
        op = data['op']
        if op == 'context':
            return {'candidate': self.cli(['context']), 'checkpoint': self.cli(['checkpoint', 'show']), 'tabs': self.cli(['tabs', 'status']), 'clock': self.state['clock'], 'phase': self.state['phase']}
        if op == 'cli':
            return self.cli(data['args'], data.get('data'))
        if op == 'say':
            message = data['message']
            if not isinstance(message, str) or not 1 <= len(message) <= 2000:
                raise ValueError('Mensagem curta obrigatória.')
            return {'delivered_to_fictional_candidate': message}
        if op == 'verdict':
            if data['job'] not in JOBS or data['decision'] not in ('eligible', 'discard', 'suspicious') or not isinstance(data.get('reason'), str):
                raise ValueError('Informe job, decision e reason.')
            return {'recorded': {k: data[k] for k in ('job', 'decision', 'reason')}}
        if op == 'tab_open':
            return self.browser.open(data['url'], data.get('purpose', 'Trabalho fictício'))
        if op == 'tab_close':
            return self.browser.close_tab(data['tab'])
        if op == 'snapshot':
            return self.browser.snapshot(data['tab'])
        if op == 'goto':
            return self.browser.goto(data['tab'], data['url'])
        if op == 'record_job':
            key = data['job']
            job = JOBS[key]
            vacancy = {k: job[k] for k in ('role', 'modality', 'contract')}
            vacancy.update(languages=[], salary={'min': job['salary'], 'max': job['salary'], 'currency': 'BRL', 'period': 'month', 'estimated': False})
            return self.cli(['opportunity'], {'company': job['company'], 'title': job['role'], 'portal': 'portal', 'aliases': ['job:portal:' + key], 'identity_verified': data['identity_verified'], 'evidence': data['evidence'], 'vacancy': vacancy})
        if op == 'authorize':
            kind = data['action']
            mail = kind.startswith('email_')
            channel = {'provider': 'gmail' if mail else 'chrome', 'account': 'principal' if mail else 'portal-a'}
            # Recording a connected fixture is mechanical. It never changes consent.
            self.cli(['capability'], {'kind': 'mail' if mail else 'browser', **channel, 'status': 'ready', 'checked_at': self.state['clock'], 'evidence': 'Laboratório fictício conectado; identidade local conhecida'})
            payload = {**self.ownership(), 'action': kind, 'channel': channel}
            for key in ('opportunity_id', 'step_key', 'scope_key', 'message', 'user_confirmation'):
                if key in data:
                    payload[key] = data[key]
            if kind in ('fill', 'apply'):
                payload.update(resume_id=self.state['resume']['id'], resume_sha256=self.state['resume']['sha256'])
            if kind == 'email_reply':
                text = data['text']
                payload['reply'] = {'recipient': 'message_sender', 'content_sha256': hashlib.sha256(text.encode()).hexdigest(), 'summary': text}
            return self.cli(['action', 'authorize'], payload)
        if op in ('fill', 'upload', 'click'):
            action = self.cli(['action', 'show', data['action_id']])
            self.require(data['action_id'], action['action'])
            if op != 'click' and action['action'] not in ('fill', 'email_reply'):
                raise ValueError('Preenchimento exige fill ou email_reply.')
            if op == 'fill':
                return self.browser.fill(data['tab'], data['selector'], data['value'])
            if op == 'upload':
                return self.browser.upload(data['tab'], data['selector'], self.directory / 'candidate' / self.state['resume']['paths']['pdf'])
            # Matching destination and action prevents accidental effects outside the lab task.
            path = self.browser.pages[data['tab']].url.split(ORIGIN)[-1]
            expected = 'email_reply' if path == '/mail' else 'fill' if path == '/complement' else 'apply'
            if action['action'] != expected:
                raise ValueError('Envio exige a autorização correspondente ao destino.')
            return self.browser.click(data['tab'], data['selector'])
        if op == 'complete':
            return self.cli(['action', 'complete', data['action_id']], {**self.ownership(), 'outcome': data['outcome'], 'evidence': data['evidence'], 'evidence_source': data.get('evidence_source', 'destination_page'), 'checked_at': self.state['clock']})
        if op == 'record_mail':
            return self.cli(['email'], {**data['data'], 'received_at': self.state['clock'], 'provider': 'gmail', 'account': 'principal'})
        raise ValueError('Operação desconhecida. Consulte o guia de ferramentas fornecido.')
