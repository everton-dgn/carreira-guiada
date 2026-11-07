"""Synthetic approved candidate and a bounded, offline adapter to the real CLI."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.job.profile import Profile
from scripts.job.resumes import ResumeManager
from scripts.job.workflow import Workflow

PROJECT = Path(__file__).resolve().parents[2]
OWNER = 'chat:benchmark'
ALLOWED = {'start', 'status', 'context', 'evaluate', 'opportunity', 'jobs', 'steps', 'step', 'transition', 'email', 'action', 'capability', 'stop', 'resume-work', 'checkpoint', 'tabs', 'mail-coverage'}


def seed(directory):
    root = directory / 'candidate'
    root.mkdir()
    sections = json.loads((PROJECT / 'templates/profile.json').read_text())['sections']
    sections['identity'] = {'name': 'Marina Exemplo', 'email': 'marina@example.invalid'}
    sections['preferences'].update(roles=['Atendente'], modalities=['remote'], currencies=['BRL'], contracts=['CLT'])
    sections['preferences']['salary'].update(range='minimum', floors=[{'contract': 'CLT', 'amount': 3500, 'currency': 'BRL', 'period': 'month'}], public_expectation={'amount': 4200, 'currency': 'BRL', 'period': 'month'})
    actions = ['research', 'fill', 'apply', 'email_read', 'email_reply']
    sections['permissions'].update({a: 'allow' for a in actions}, confirmed=actions)
    sections['sources'] = {'urls': ['https://portal.example.invalid/']}
    sections['connections'] = {'accounts': [{'provider': 'portal', 'alias': 'portal-a', 'address': 'marina@example.invalid'}, {'provider': 'gmail', 'alias': 'principal', 'address': 'marina@example.invalid'}]}
    profile = Profile(root)
    for key, value in sections.items():
        profile.save(key, value)
    profile.approve(profile.get()['version'])
    manager = ResumeManager(root)
    fact = manager.add_fact('Experiência fictícia em atendimento de 2022 a 2025.', 'candidate:chat', True)
    resume = manager.approve(manager.draft('atendimento', '# Marina Exemplo\n\nExperiência fictícia em atendimento de 2022 a 2025.', [fact['id']])['id'])
    wf = Workflow(root)
    try:
        wf.configure_goal({'summary': 'Candidatura fictícia e acompanhamento autorizado', 'actions': actions})
    finally:
        wf.close()
    clock = datetime.now(timezone.utc).isoformat()
    state = {'clock': clock, 'initial_clock': clock, 'phase': 1, 'resume': resume, 'profile': profile.get(), 'owner': OWNER}
    (directory / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
    guard = directory / 'guard'
    guard.mkdir()
    (guard / 'sitecustomize.py').write_text('''import socket, subprocess, os
from datetime import datetime
def deny(*args, **kwargs):
    raise RuntimeError('BENCHMARK_CLI_NETWORK_BLOCKED')
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.socket.sendto = deny
socket.create_connection = deny
socket.getaddrinfo = deny
subprocess.Popen = deny
os.system = deny
from scripts.job.workflow import Workflow
original = Workflow.__init__
def init(self, root, **kwargs):
    kwargs['clock'] = lambda: datetime.fromisoformat(os.environ['BENCHMARK_CLOCK'])
    original(self, root, **kwargs)
Workflow.__init__ = init
''')
    return state


def call(directory, args, data=None):
    if not isinstance(args, list) or not args or args[0] not in ALLOWED or any(not isinstance(a, str) or a.startswith('--') for a in args):
        raise ValueError('Comando fora do escopo fictício.')
    if args[0] == 'tabs' and args[1:] != ['status']:
        raise ValueError('As reservas são controladas por tab_open e tab_close.')
    state = json.loads((directory / 'state.json').read_text())
    env = {**os.environ, 'PYTHONPATH': str(directory / 'guard') + os.pathsep + str(PROJECT), 'PATH': str(directory / 'guard'), 'PYTHONDONTWRITEBYTECODE': '1', 'BENCHMARK_CLOCK': state['clock']}
    process = subprocess.run([sys.executable, '-m', 'scripts.job.cli', '--root', str(directory / 'candidate'), *args, '--json'], input=json.dumps(data) if data is not None else '', text=True, capture_output=True, cwd=PROJECT, env=env, timeout=20)
    try:
        result = json.loads(process.stdout)
    except ValueError:
        raise RuntimeError('CLI returned invalid output: ' + process.stderr[:500]) from None
    if process.returncode:
        raise ValueError(result.get('error', 'CLI failed'))
    return result
