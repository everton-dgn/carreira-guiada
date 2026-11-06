"""Local release preparation. Only the project version, lock and changelog change."""

from datetime import date
from pathlib import Path
import re
import subprocess
import tomllib

from .versioning import VERSION, plan_version, prepare_changelog, version_parts


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              text=True, encoding='utf-8', capture_output=True, timeout=60).stdout.strip()

    def read(self, name, ref=None):
        if ref:
            return self.git('show', f'{ref}:{name}') + '\n'
        path = self.root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Arquivo ausente ou link simbólico: {name}')
        return path.read_text(encoding='utf-8')

    def manifest(self, ref=None):
        return tomllib.loads(self.read('pyproject.toml', ref))

    def baseline(self, head='HEAD', exclude=None):
        tags = self.git('tag', '--merged', head).splitlines()
        tags = [t for t in tags if t.startswith('v') and VERSION.fullmatch(t[1:]) and t != exclude]
        return max(tags, key=lambda t: version_parts(t[1:])) if tags else None

    def commits(self, baseline, head='HEAD'):
        span = f'{baseline}..{head}' if baseline else head
        fields = self.git('log', '--no-merges', '--format=%H%x00%B%x00', span).split('\0')
        return [(fields[i].strip(), fields[i + 1]) for i in range(0, len(fields) - 1, 2)]

    def assert_clean(self):
        if self.git('status', '--porcelain'):
            raise ValueError('Salve as mudanças em um commit antes de preparar ou publicar uma versão.')

    def assert_versions(self, ref=None):
        manifest = self.manifest(ref)
        project = manifest['project']
        version_parts(project['version'])
        packages = tomllib.loads(self.read('uv.lock', ref))['package']
        own = [p for p in packages if p.get('name') == project['name'] and p.get('source') == {'virtual': '.'}]
        if len(own) != 1 or own[0]['version'] != project['version']:
            raise ValueError('A versão do pyproject.toml difere do pacote local no uv.lock.')
        prerelease = manifest.get('tool', {}).get('carreira-release', {}).get('prerelease', True)
        if not isinstance(prerelease, bool):
            raise ValueError('tool.carreira-release.prerelease precisa ser booleano.')
        return project, prerelease

    def plan(self):
        self.assert_clean()
        project, prerelease = self.assert_versions()
        baseline = self.baseline()
        if baseline != 'v' + project['version'] and not (baseline is None and project['version'] == '0.0.0'):
            raise ValueError('A versão atual precisa coincidir com a última tag. Busque as tags antes de preparar a release.')
        plan = plan_version(project['version'], self.commits(baseline))
        if plan:
            plan.update(tag='v' + plan['version'], baseline=baseline, source=self.git('rev-parse', 'HEAD'), prerelease=prerelease)
        return plan

    def prepare(self, day=None):
        plan = self.plan()
        if not plan:
            return None
        branch = self.git('branch', '--show-current')
        if not re.fullmatch(r'(?:feat|fix|refactor|perf|docs|test|chore|release)/[A-Za-z0-9][A-Za-z0-9._/-]*', branch):
            raise ValueError('Prepare a versão em uma branch de trabalho, fora da main.')
        names = ('pyproject.toml', 'uv.lock', 'CHANGELOG.md')
        original = {name: self.read(name) for name in names}
        current = self.manifest()['project']
        changed = dict(original)
        section = re.search(r'(?ms)^\[project\]\n.*?(?=^\[|\Z)', original['pyproject.toml'])
        if not section:
            raise ValueError('Seção project não encontrada.')
        changed_section = replace_version(section.group(), current['version'], plan['version'])
        changed['pyproject.toml'] = original['pyproject.toml'][:section.start()] + changed_section + original['pyproject.toml'][section.end():]
        blocks = original['uv.lock'].split('[[package]]')
        changed_count = 0
        for index, block in enumerate(blocks[1:], 1):
            parsed = tomllib.loads('[[package]]' + block)['package'][0]
            if parsed.get('name') == current['name'] and parsed.get('source') == {'virtual': '.'}:
                blocks[index] = replace_version(block, current['version'], plan['version'])
                changed_count += 1
        if changed_count != 1:
            raise ValueError('Pacote local ambíguo no uv.lock.')
        changed['uv.lock'] = '[[package]]'.join(blocks)
        changed['CHANGELOG.md'], plan['notes'] = prepare_changelog(original['CHANGELOG.md'], plan['version'], plan['notes'], day or date.today().isoformat())
        written = []
        try:
            for name in names:
                written.append(name)
                (self.root / name).write_text(changed[name], encoding='utf-8')
        except OSError:
            for name in written:
                (self.root / name).write_text(original[name], encoding='utf-8')
            raise
        return plan


def replace_version(block, before, after):
    pattern = r'^version[ \t]*=[ \t]*"' + re.escape(before) + r'"[ \t]*$'
    result, count = re.subn(pattern, f'version = "{after}"', block, flags=re.M)
    if count != 1:
        raise ValueError('A versão não pôde ser alterada sem ambiguidade.')
    return result
