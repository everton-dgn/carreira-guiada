"""Exercise CI diff selection against real Git histories and fail-closed results."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.maintainers import ci_checks as ci

ROOT = Path(__file__).resolve().parents[1]


class SelectionTests(unittest.TestCase):
    def test_documentation_and_assets_are_short(self):
        for name in ('README.md', 'docs/GUIA.md', 'docs/assets/image with spaces.png',
                     'docs/assets/demo.gif', 'CHANGELOG.md'):
            with self.subTest(name=name), patch.object(ci, 'git', return_value=f'M\0{name}\0'.encode()):
                self.assertEqual(ci.selection('push', {'before': 'a' * 40, 'after': 'b' * 40}), 'docs')

    def test_unknown_code_fixtures_reports_skills_config_and_gates_are_full(self):
        names = ('scripts/job/cli.py', 'tests/fixtures/model-benchmark.json', 'pyproject.toml',
                 'uv.lock', '.github/workflows/checks.yml', '.githooks/pre-push',
                 'docs/benchmarks/answer.md', 'docs/benchmarks/raw.txt', 'docs/benchmarks/report.json',
                 'docs/BENCHMARK-FERRAMENTAS.md', 'docs/new-guide.md', 'unknown.md',
                 'docs/assets/payload.py', '.agents/skills/inicio/SKILL.md',
                 '.claude/skills/inicio/SKILL.md', 'AGENTS.md', 'CLAUDE.md')
        for name in names:
            with self.subTest(name=name), patch.object(ci, 'git', return_value=f'M\0{name}\0'.encode()):
                self.assertEqual(ci.selection('push', {'before': 'a' * 40, 'after': 'b' * 40}), 'full')

    def test_renames_and_copies_consider_both_names(self):
        for status in ('R100', 'C075'):
            for old, new, expected in (
                ('README.md', 'docs/GUIA.md', 'docs'),
                ('scripts/job/cli.py', 'docs/GUIA.md', 'full'),
                ('docs/GUIA.md', 'scripts/job/cli.py', 'full'),
                ('docs/assets/old image.png', 'docs/assets/new image.png', 'docs'),
            ):
                raw = f'{status}\0{old}\0{new}\0'.encode()
                with self.subTest(status=status, old=old, new=new), patch.object(ci, 'git', return_value=raw):
                    self.assertEqual(ci.diff_paths(raw), [old, new])
                    self.assertEqual(ci.selection('push', {'before': 'a' * 40, 'after': 'b' * 40}), expected)

    def test_deletions_and_mixed_changes(self):
        for raw, expected in ((b'D\0docs/GUIA.md\0', 'docs'),
                              (b'D\0scripts/job/cli.py\0', 'full'),
                              (b'M\0README.md\0A\0new-file\0', 'full')):
            with self.subTest(raw=raw), patch.object(ci, 'git', return_value=raw):
                self.assertEqual(ci.selection('push', {'before': 'a' * 40, 'after': 'b' * 40}), expected)

    def test_missing_malformed_empty_or_unavailable_diff_is_full(self):
        event = {'before': 'a' * 40, 'after': 'b' * 40}
        for raw in (b'', b'M\0README.md', b'R100\0README.md\0', b'T\0README.md\0',
                    b'U\0README.md\0', b'M\0\xff\0', b'M\0../README.md\0'):
            with self.subTest(raw=raw), patch.object(ci, 'git', return_value=raw):
                self.assertEqual(ci.selection('push', event), 'full')
        for error in (OSError(), subprocess.CalledProcessError(128, 'git'), subprocess.TimeoutExpired('git', 60)):
            with self.subTest(error=error), patch.object(ci, 'git', side_effect=error):
                self.assertEqual(ci.selection('push', event), 'full')
        for event in ({}, None, {'before': '0' * 40, 'after': 'b' * 40}):
            self.assertEqual(ci.selection('push', event), 'full')
        for name in ('workflow_dispatch', 'unexpected'):
            with patch.object(ci, 'git') as git:
                self.assertEqual(ci.selection(name, {}), 'full')
                git.assert_not_called()

    def test_real_git_merge_base_push_and_renames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.run(['git', '-C', directory, *args], check=True, capture_output=True).stdout

            def save(name, text):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding='utf-8')

            def commit():
                git('add', '.')
                git('-c', 'user.name=CI Test', '-c', 'user.email=ci@example.invalid',
                    '-c', 'commit.gpgsign=false', 'commit', '-m', 'test: fixture')
                return git('rev-parse', 'HEAD').decode().strip()

            git('init', '-b', 'main')
            save('README.md', 'base\n')
            save('docs/assets/old image.png', 'fictional\n' * 10)
            base = commit()
            git('checkout', '-b', 'feat/docs')
            save('README.md', 'changed\n')
            head = commit()
            git('checkout', 'main')
            save('scripts/new.py', 'print(1)\n')
            advanced = commit()
            with patch.object(ci, 'git', side_effect=git):
                self.assertEqual(ci.selection('pull_request', {'pull_request': {
                    'base': {'sha': advanced}, 'head': {'sha': head}}}), 'docs')
                self.assertEqual(ci.selection('push', {'before': advanced, 'after': head}), 'full')
                self.assertEqual(ci.selection('push', {'before': 'c' * 40, 'after': head}), 'full')
            git('checkout', 'feat/docs')
            git('mv', 'docs/assets/old image.png', 'docs/assets/new image.png')
            renamed = commit()
            raw = git('diff', '--name-status', '-z', '--find-renames', head, renamed, '--')
            self.assertEqual(ci.diff_paths(raw), ['docs/assets/old image.png', 'docs/assets/new image.png'])
            git('rm', 'README.md')
            deleted = commit()
            with patch.object(ci, 'git', side_effect=git):
                self.assertEqual(ci.selection('push', {'before': renamed, 'after': deleted}), 'docs')
                self.assertEqual(ci.selection('push', {'before': base, 'after': deleted}), 'docs')


class ReleaseSelectionTests(unittest.TestCase):
    manifest = '[project]\nname = "carreira-guiada"\nversion = "1.0.0"\ndependencies = ["other>=2"]\n[tool.uv]\npackage = false\n'
    lock = 'version = 1\n[[package]]\nname = "carreira-guiada"\nversion = "1.0.0"\nsource = {virtual = "."}\ndependencies = [{name = "other"}]\n[[package]]\nname = "other"\nversion = "2.0.0"\nsource = {registry = "https://example.invalid"}\n'

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git('init', '-b', 'main')
        self.save('pyproject.toml', self.manifest)
        self.save('uv.lock', self.lock)
        self.save('README.md', 'before')
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, timeout=15).stdout

    def save(self, name, content):
        (self.root / name).write_text(content, encoding='utf-8')

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'user.name=CI Test', '-c', 'user.email=ci@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'test: release')
        return self.git('rev-parse', 'HEAD').decode().strip()

    def select(self):
        head = self.commit()
        with patch.object(ci, 'git', side_effect=self.git):
            return ci.selection('push', {'before': self.base, 'after': head})

    def bump(self):
        self.save('pyproject.toml', self.manifest.replace('1.0.0', '1.1.0'))
        self.save('uv.lock', self.lock.replace('1.0.0', '1.1.0'))
        self.save('README.md', 'after')

    def test_real_release_version_only_uses_short_route(self):
        self.bump()
        self.assertEqual(self.select(), 'docs')

    def test_pull_request_uses_blobs_at_merge_base(self):
        self.git('checkout', '-b', 'feat/docs')
        self.bump()
        head = self.commit()
        self.git('checkout', 'main')
        self.save('pyproject.toml', self.manifest.replace('other>=2', 'other>=3'))
        advanced = self.commit()
        with patch.object(ci, 'git', side_effect=self.git):
            self.assertEqual(ci.selection('pull_request', {'pull_request': {
                'base': {'sha': advanced}, 'head': {'sha': head}}}), 'docs')
            self.assertEqual(ci.selection('push', {'before': advanced, 'after': head}), 'full')

    def test_missing_baseline_file_and_unchanged_versions_are_full(self):
        self.save('pyproject.toml', self.manifest + '# comment\n')
        self.save('uv.lock', self.lock + '# comment\n')
        self.assertEqual(self.select(), 'full')
        self.git('rm', 'uv.lock')
        self.base = self.commit()
        self.bump()
        self.assertEqual(self.select(), 'full')

    def test_other_toml_changes_remain_full(self):
        changes = [
            ('pyproject.toml', 'package = false', 'package = true'),
            ('pyproject.toml', 'package = false', 'package = 0'),
            ('pyproject.toml', 'other>=2', 'other>=3'),
            ('uv.lock', '2.0.0', '2.0.1'),
            ('uv.lock', 'example.invalid', 'changed.invalid'),
            ('uv.lock', 'virtual = "."', 'virtual = "elsewhere"'),
            ('uv.lock', 'dependencies = [{name = "other"}]', 'dependencies = []'),
            ('uv.lock', 'name = "other"', 'name = "hidden"'),
            ('uv.lock', 'version = 1\n', 'version = 2\n'),
        ]
        for name, old, new in changes:
            with self.subTest(name=name, change=new):
                self.bump()
                self.save(name, (self.root / name).read_text().replace(old, new))
                self.assertEqual(self.select(), 'full')

    def test_absent_inconsistent_malformed_or_duplicate_versions_are_full(self):
        for name, old, new in [
            ('uv.lock', '1.1.0', '1.2.0'),
            ('pyproject.toml', 'version = "1.1.0"', ''),
            ('uv.lock', 'version = "1.1.0"', ''),
            ('pyproject.toml', '1.1.0', 'invalid'),
            ('pyproject.toml', '[project]', '[project'),
            ('uv.lock', 'version = 1', 'version = invalid'),
            ('uv.lock', '[[package]]\nname = "other"', '[[package]]\nname = "carreira-guiada"'),
        ]:
            with self.subTest(name=name, change=new):
                self.bump()
                self.save(name, (self.root / name).read_text().replace(old, new))
                self.assertEqual(self.select(), 'full')

    def test_one_sided_bump_delete_and_rename_are_full(self):
        self.save('pyproject.toml', self.manifest.replace('1.0.0', '1.1.0'))
        self.assertEqual(self.select(), 'full')
        self.bump()
        self.git('mv', 'uv.lock', 'renamed.lock')
        self.assertEqual(self.select(), 'full')
        self.git('mv', 'renamed.lock', 'uv.lock')
        self.commit()
        self.git('rm', 'uv.lock')
        self.assertEqual(self.select(), 'full')

    def test_invalid_baseline_is_not_repaired_into_short_route(self):
        self.save('uv.lock', self.lock.replace('1.0.0', '0.9.0'))
        self.base = self.commit()
        self.bump()
        self.assertEqual(self.select(), 'full')

    def test_mode_change_and_symlink_are_full(self):
        self.bump()
        (self.root / 'uv.lock').chmod(0o755)
        self.assertEqual(self.select(), 'full')
        (self.root / 'uv.lock').unlink()
        (self.root / 'uv.lock').symlink_to('pyproject.toml')
        self.assertEqual(self.select(), 'full')

    def test_version_only_does_not_hide_code_changes(self):
        self.bump()
        self.save('code.py', 'print(1)')
        self.assertEqual(self.select(), 'full')

    def test_comments_and_formatting_cannot_hide_semantic_changes(self):
        self.bump()
        self.save('pyproject.toml', (self.root / 'pyproject.toml').read_text() + '\n# comment\n')
        self.assertEqual(self.select(), 'docs')
        self.save('pyproject.toml', (self.root / 'pyproject.toml').read_text() + 'hidden = "payload"\n')
        self.assertEqual(self.select(), 'full')

    def test_versions_command_reads_actual_files_without_project_dependencies(self):
        for expected in (0, 1):
            if expected:
                self.save('uv.lock', self.lock.replace('1.0.0', '1.2.0'))
            result = subprocess.run([sys.executable, '-S', str(ROOT / 'scripts/maintainers/ci_checks.py'),
                                     'versions'], cwd=self.root, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        (self.root / 'uv.lock').unlink()
        result = subprocess.run([sys.executable, '-S', str(ROOT / 'scripts/maintainers/ci_checks.py'),
                                 'versions'], cwd=self.root, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 1)


class QualityTests(unittest.TestCase):
    def needs(self, mode):
        result = 'success' if mode == 'full' else 'skipped'
        return {'plan': {'result': 'success', 'outputs': {'mode': mode}},
                'documentation': {'result': 'success'},
                'tests': {'result': result}, 'browser': {'result': result}}

    def test_only_exact_success_and_intentional_skips_pass(self):
        for mode in ('full', 'docs'):
            needs = self.needs(mode)
            self.assertTrue(ci.quality(needs))
            for job in needs:
                for result in ('failure', 'cancelled', 'skipped', '', 'success'):
                    if result == needs[job]['result']:
                        continue
                    changed = copy.deepcopy(needs)
                    changed[job]['result'] = result
                    with self.subTest(mode=mode, job=job, result=result):
                        self.assertFalse(ci.quality(changed))
                changed = copy.deepcopy(needs)
                del changed[job]
                self.assertFalse(ci.quality(changed))

    def test_missing_or_unrecognized_plan_cannot_allow_skips(self):
        for outputs in ({}, None, {'mode': ''}, {'mode': 'false'}, {'mode': 'other'}):
            needs = self.needs('docs')
            needs['plan']['outputs'] = outputs
            self.assertFalse(ci.quality(needs))
        for needs in (None, {}, {'plan': None}):
            self.assertFalse(ci.quality(needs))

    def test_quality_command_exit_status(self):
        for needs, expected in ((self.needs('docs'), 0), (self.needs('full'), 0), ({}, 1)):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/maintainers/ci_checks.py'), 'quality'],
                                    env={**os.environ, 'CI_NEEDS': json.dumps(needs)}, capture_output=True)
            self.assertEqual(result.returncode, expected, result.stderr)

    def test_select_command_missing_event_falls_back_to_full(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/maintainers/ci_checks.py'), 'select'],
                env={**os.environ, 'GITHUB_EVENT_NAME': 'push', 'GITHUB_EVENT_PATH': str(Path(directory) / 'missing'),
                     'GITHUB_OUTPUT': str(output)}, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(), 'mode=full\n')


if __name__ == '__main__':
    unittest.main()
