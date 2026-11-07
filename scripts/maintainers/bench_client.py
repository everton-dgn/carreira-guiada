"""Prepare a provider-neutral client folder for the fictional laboratory."""
import argparse
import json
from pathlib import Path
import shlex
import shutil

PROJECT = Path(__file__).resolve().parents[2]


def create(laboratory, client):
    laboratory, client = laboratory.resolve(), client.resolve()
    if not (laboratory / 'state.json').is_file():
        raise ValueError('Inicialize primeiro um laboratório fictício novo.')
    if any((parent / '.git').exists() for parent in (client, *client.parents)):
        raise ValueError('Escolha uma pasta fora de um checkout Git para evitar mudança automática de diretório pelo cliente.')
    uv = shutil.which('uv')
    if not uv:
        raise ValueError('O executor precisa de uv no PATH.')
    client.mkdir(parents=True, exist_ok=False)
    shutil.copy2(PROJECT / 'docs/BENCHMARK-FERRAMENTAS.md', client / 'GUIA.md')
    command = [uv, 'run', '--offline', '--project', str(PROJECT), '--locked', '--group', 'browser',
               'python', '-m', 'scripts.maintainers.browser_benchmark', 'call', '--directory', str(laboratory), '--data']
    wrapper = client / 'tools'
    wrapper.write_text('#!/bin/sh\ncd ' + shlex.quote(str(PROJECT)) + '\nexec ' + shlex.join(command) + ' "$1"\n')
    wrapper.chmod(0o700)
    protocol = json.loads((PROJECT / 'templates/browser-benchmark.json').read_text())
    prompts = laboratory / 'executor-prompts'
    prompts.mkdir(exist_ok=False)
    for session in protocol['sessions']:
        (prompts / f'fase-{session["phase"]}.txt').write_text(session['prompt'])
    return {'client': str(client), 'laboratory': str(laboratory), 'executor_prompts': str(prompts), 'sessions': 2}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--laboratory', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(create(args.laboratory, args.client), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
