"""Prepare fresh restricted clients; model starts remain the orchestrator's job."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from .adversarial_codex import dump
from .adversarial_codex_probe import prepare as prepare_codex

ROOT = Path(__file__).resolve().parents[2]


def prepare(state, kind, provider, model, effort, seconds=300):
    """Keep each model cwd outside the project, corpus and scoring criteria."""
    state = Path(state).resolve()
    if kind not in ('adversarial', 'browser', 'preparation', 'guidance') or not state.is_file():
        raise ValueError('Initialize a supported fictional laboratory first')
    if provider == 'codex':
        catalog = json.loads((Path.home() / '.codex/models_cache.json').read_text(encoding='utf-8'))
        client = prepare_codex(ROOT, state, model, effort, catalog)
        manifest = json.loads((client / 'executor.json').read_text(encoding='utf-8'))
    elif provider in ('claude', 'glm', 'm3'):
        version = subprocess.run(['claude', '--version'], check=True, capture_output=True,
                                 text=True, encoding='utf-8', timeout=10).stdout.strip()
        parent = Path(tempfile.mkdtemp(prefix='carreira-claude-probe-')).resolve()
        client = parent / 'client'
        client.mkdir()
        manifest = {'root': str(ROOT), 'python': sys.executable, 'state': str(state),
                    'model': model, 'effort': effort, 'client_version': version}
    else:
        raise ValueError('Unsupported provider route')
    manifest.update(laboratory_kind=kind, session_seconds=seconds)
    dump(client / 'executor.json', manifest)
    return client


def main():
    """Print only the private client path, without inspecting authentication."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--kind', required=True)
    parser.add_argument('--provider', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', required=True)
    parser.add_argument('--seconds', type=int, default=300)
    args = parser.parse_args()
    print(prepare(args.state, args.kind, args.provider, args.model, args.effort, args.seconds))


if __name__ == '__main__':
    main()
