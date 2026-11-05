"""Maintainer entry point: plan, prepare and publish releases."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from .release_repository import Repository
from .release_publish import publish


def main():
    parser = argparse.ArgumentParser(description='Planejar, preparar e publicar versões do projeto.')
    parser.add_argument('command', choices=('plan', 'prepare', 'publish'))
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--run-id', default=os.environ.get('RELEASE_SOURCE_RUN_ID'))
    args = parser.parse_args()
    repo = Repository(args.root)
    try:
        if args.command == 'publish':
            if not args.repository or not args.run_id:
                raise ValueError('Publicação exige --repository e --run-id, ou as variáveis equivalentes da CI.')
            result = publish(repo, args.repository, args.run_id)
        else:
            result = getattr(repo, args.command)()
        print(json.dumps(result or {'status': 'no_release'}, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, 'Não foi possível concluir o versionamento: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
