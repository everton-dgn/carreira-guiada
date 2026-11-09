"""Conservative CI selection and required-check aggregation (standard library only)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tomllib


# Deliberately closed: new documents need review before joining the short route.
DOCUMENTS = {
    'README.md', 'CHANGELOG.md', 'CODE_OF_CONDUCT.md', 'CONTRIBUTING.md',
    'SECURITY.md', 'LICENSE', 'NOTICE',
    'docs/ACOMPANHAMENTO.md', 'docs/ATS.md', 'docs/CARREIRA.md',
    'docs/CONTRATOS.md', 'docs/CURRICULOS.md', 'docs/EMPRESAS.md',
    'docs/ENTREVISTAS.md', 'docs/FAQ.md', 'docs/FONTES.md',
    'docs/GUIA-VISUAL.md', 'docs/GUIA.md', 'docs/INTERNACIONAL.md',
    'docs/INVESTIGACAO-AGENTE.md', 'docs/MODELOS.md', 'docs/ONBOARDING.md',
    'docs/OPERACAO.md', 'docs/PLANEJAMENTO-AGENTE.md', 'docs/PRIVACIDADE.md',
    'docs/PROPOSTAS.md', 'docs/SEGURANCA-NA-PRATICA.md',
}


def documentation_path(name):
    path = PurePosixPath(name)
    return name in DOCUMENTS or (
        len(path.parts) == 3 and path.parts[:2] == ('docs', 'assets')
        and path.suffix in {'.png', '.gif'} and '\\' not in name
    )


def diff_entries(raw):
    """Parse name-status -z, preserving both rename/copy names and whitespace."""
    if not raw or not raw.endswith(b'\0'):
        raise ValueError('Missing or incomplete diff')
    fields = raw[:-1].decode('utf-8').split('\0')
    entries = []
    while fields:
        status = fields.pop(0)
        if not re.fullmatch(r'[AMD]|[RC][0-9]{1,3}', status):
            raise ValueError('Unrecognized diff status')
        count = 2 if status[0] in 'RC' else 1
        if len(fields) < count:
            raise ValueError('Incomplete diff entry')
        names = []
        for _ in range(count):
            name = fields.pop(0)
            path = PurePosixPath(name)
            if not name or path.is_absolute() or '..' in path.parts:
                raise ValueError('Invalid diff path')
            names.append(name)
        entries.append((status, names))
    return entries


def diff_paths(raw):
    return [name for _, names in diff_entries(raw) for name in names]


def toml_value(value):
    """Compare every field, including scalar types (False must not equal 0)."""
    if isinstance(value, dict):
        return {key: toml_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [toml_value(item) for item in value]
    return (type(value).__name__, repr(value))


def project_version(manifest, lock):
    project = manifest['project']
    if project['name'] != 'carreira-guiada':
        raise ValueError('Unexpected project identity')
    version = project['version']
    if not isinstance(version, str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('Missing or invalid release version')
    packages = lock['package']
    if not isinstance(packages, list) or any(not isinstance(p, dict) for p in packages):
        raise ValueError('Invalid package inventory')
    own = [p for p in packages if p.get('name') == 'carreira-guiada']
    if len(own) != 1 or own[0].get('source') != {'virtual': '.'} or own[0].get('version') != version:
        raise ValueError('Ambiguous or inconsistent local package')
    return version, own[0]


def version_only(base, head):
    snapshots = []
    versions = []
    for ref in (base, head):
        names = ('pyproject.toml', 'uv.lock')
        tree = git('ls-tree', '-z', ref, '--', *names).decode().rstrip('\0').split('\0')
        if len(tree) != 2 or {entry.split('\t')[-1] for entry in tree} != set(names):
            return False
        if any(not entry.startswith('100644 blob ') for entry in tree):
            return False
        manifest, lock = [tomllib.loads(git('show', f'{ref}:{name}').decode('utf-8')) for name in names]
        version, own = project_version(manifest, lock)
        versions.append(version)
        del manifest['project']['version']
        del own['version']
        snapshots.append(toml_value([manifest, lock]))
    return versions[0] != versions[1] and snapshots[0] == snapshots[1]


def git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True, timeout=60).stdout


def commit(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value) or value == '0' * 40:
        raise ValueError('Missing commit')
    return value


def selection(event_name, event):
    """Any unavailable/ambiguous comparison selects the complete suite."""
    try:
        if event_name == 'pull_request':
            base = commit(event['pull_request']['base']['sha'])
            head = commit(event['pull_request']['head']['sha'])
            base = commit(git('merge-base', base, head).decode().strip())
        elif event_name == 'push':
            base, head = commit(event['before']), commit(event['after'])
        else:
            return 'full'
        entries = diff_entries(git('diff', '--name-status', '-z', '--find-renames', base, head, '--'))
        metadata = {'pyproject.toml', 'uv.lock'}
        release = [(status, names) for status, names in entries if metadata.intersection(names)]
        if release:
            if sorted(release) != [('M', ['pyproject.toml']), ('M', ['uv.lock'])] or not version_only(base, head):
                return 'full'
        paths = [name for _, names in entries for name in names if name not in metadata]
        return 'docs' if all(map(documentation_path, paths)) else 'full'
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        return 'full'


def quality(needs):
    """Only the planner's documented short route may skip expensive jobs."""
    if not isinstance(needs, dict) or set(needs) != {'plan', 'documentation', 'tests', 'browser'}:
        return False
    if any(not isinstance(value, dict) for value in needs.values()):
        return False
    if needs['plan'].get('result') != 'success' or needs['documentation'].get('result') != 'success':
        return False
    outputs = needs['plan'].get('outputs')
    mode = outputs.get('mode') if isinstance(outputs, dict) else None
    if mode not in {'docs', 'full'}:
        return False
    expected = 'success' if mode == 'full' else 'skipped'
    return all(needs[job].get('result') == expected for job in ('tests', 'browser'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['select', 'quality', 'versions'])
    args = parser.parse_args()
    if args.command == 'versions':
        try:
            manifest, lock = [tomllib.loads(Path(name).read_text(encoding='utf-8'))
                              for name in ('pyproject.toml', 'uv.lock')]
            version, _ = project_version(manifest, lock)
        except (KeyError, TypeError, ValueError, OSError) as error:
            print(f'Release metadata failed: {error}')
            return 1
        print(f'Consistent project release: {version}')
        return 0
    if args.command == 'quality':
        try:
            passed = quality(json.loads(os.environ['CI_NEEDS']))
        except (KeyError, ValueError):
            passed = False
        print('Required checks passed.' if passed else 'Required checks failed or were unexpectedly omitted.')
        return 0 if passed else 1
    try:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
        mode = selection(os.environ.get('GITHUB_EVENT_NAME'), event)
    except (KeyError, ValueError, OSError):
        mode = 'full'
    print(f'CI selection: {mode}')
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        output.write(f'mode={mode}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
