"""Release regression scenarios use temporary Git repositories and a fake GitHub API."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.maintainers.release_repository import Repository
from scripts.maintainers.release_publish import GitHub, publish
from scripts.maintainers.versioning import breaking_footer, plan_version, prepare_changelog, release_notes


class VersioningTests(unittest.TestCase):
    def test_optional_api_lookup_only_accepts_not_found(self):
        for status in ('404', 404, '403', '500'):
            response = subprocess.CompletedProcess([], 1, json.dumps({'status': status}), 'request failed')
            with self.subTest(status=status), patch('scripts.maintainers.release_publish.subprocess.run', return_value=response):
                if str(status) == '404':
                    self.assertIsNone(GitHub().call('GET', 'repos/owner/project/git/ref/tags/v1.0.0', optional=True))
                else:
                    with self.assertRaises(ValueError):
                        GitHub().call('GET', 'repos/owner/project/git/ref/tags/v1.0.0', optional=True)
                with self.assertRaises(ValueError):
                    GitHub().call('GET', 'repos/owner/project')

    def test_largest_conventional_change_sets_version(self):
        cases = [(['fix: correct output'], '1.2.4'), (['fix: repair', 'feat: add option'], '1.3.0'),
                 (['feat: add option', 'refactor(api)!: change contract'], '2.0.0'),
                 (['chore(deps): update parser'], '1.2.4'), (['build(deps-dev): update tools'], '1.2.4')]
        for messages, expected in cases:
            with self.subTest(messages=messages):
                self.assertEqual(plan_version('1.2.3', [('a' * 40, m) for m in messages])['version'], expected)
        self.assertIsNone(plan_version('1.2.3', [('a' * 40, 'docs: explain usage'), ('b' * 40, 'chore(release): v1.2.3')]))

    def test_breaking_examples_inside_fences_do_not_bump_major(self):
        for opening, inner, closing in [('````', '```', '````'), ('~~~', '```', '~~~'), ('```', '```python', '````')]:
            body = '\n'.join([opening, inner, 'BREAKING CHANGE: example', closing])
            self.assertFalse(breaking_footer(body))
            self.assertTrue(breaking_footer(body + '\nBREAKING-CHANGE: actual change'))
        self.assertTrue(breaking_footer('Details\nBREAKING CHANGE: actual change'))

    def test_curated_notes_survive_and_mentions_are_escaped(self):
        plan = plan_version('0.1.0', [('a' * 40, 'fix: <script> @someone #123')])
        self.assertIn('&lt;script&gt; &#64;someone', plan['notes'])
        result, notes = prepare_changelog('# Histórico\n\n## Unreleased\n\nNotas revisadas.\n\n## 0.1.0\nAnterior.\n', '0.1.1', plan['notes'], '2026-11-05')
        self.assertEqual(notes, 'Notas revisadas.')
        self.assertIn('## Unreleased\n\n## 0.1.1 - 2026-11-05', result)
        self.assertIn('Anterior.', result)
        self.assertEqual(release_notes(result, '0.1.1'), notes)

    def test_invalid_versions_and_ambiguous_changelog_fail(self):
        for version in ('01.2.3', '1.2', '1.2.3-alpha', '1.2.3\n'):
            with self.assertRaises(ValueError):
                plan_version(version, [('a' * 40, 'fix: change')])
        for changelog in ('# Missing', '## Unreleased\n## Unreleased\n', '## Unreleased\n## 1.2.4 - 2026-11-05\nExisting'):
            with self.assertRaises(ValueError):
                prepare_changelog(changelog, '1.2.4', 'Notes', '2026-11-05')
        with self.assertRaises(ValueError):
            prepare_changelog('## Unreleased\n', '1.2.4', 'Notes', '2026-02-30')


class FakeGitHub:
    def __init__(self, source):
        self.source = source
        self.run = {'status': 'completed', 'conclusion': 'success', 'event': 'push', 'head_branch': 'main',
                    'path': '.github/workflows/checks.yml', 'head_sha': source,
                    'head_repository': {'full_name': 'owner/project'}}
        self.ref = None
        self.release = None
        self.posts = []
        self.fail_release_once = False
        self.quality = 'success'
        self.unrelated = None

    def call(self, method, path, payload=None, optional=False):
        if method == 'POST':
            self.posts.append((path, payload))
            if path.endswith('/git/tags'):
                self.tag_object = {'object': {'type': 'commit', 'sha': payload['object']}}
                return {'sha': 'a' * 40}
            if path.endswith('/git/refs'):
                self.ref = {'object': {'type': 'tag', 'sha': payload['sha']}}
                return self.ref
            if path.endswith('/releases'):
                if self.fail_release_once:
                    self.fail_release_once = False
                    raise ValueError('Simulated publication failure')
                self.release = dict(payload, html_url='https://code.example/release')
                return self.release
        if path.endswith('/actions/runs/123'):
            return self.run
        if '/jobs?' in path:
            return {'jobs': [{'name': 'quality', 'conclusion': self.quality}]}
        if path.endswith('/git/ref/heads/main'):
            return {'object': {'sha': self.source, 'type': 'commit'}}
        if '/compare/' in path:
            return {'status': 'diverged' if self.unrelated and self.unrelated in path else 'identical'}
        if '/git/ref/tags/' in path:
            return self.ref
        if '/git/tags/' in path:
            return self.tag_object
        if '/releases/tags/' in path:
            return self.release
        raise AssertionError('Unexpected fake API call: ' + method + ' ' + path)


class ReleaseRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='carreira-release-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Example contributor')
        self.git('config', 'user.email', 'person@example.invalid')
        self.git('remote', 'add', 'origin', 'https://github.com/owner/project.git')
        (self.root / 'pyproject.toml').write_text('[project]\nname = "sample"\nversion = "0.1.0"\n\n[tool.carreira-release]\nprerelease = true\n')
        (self.root / 'uv.lock').write_text('version = 1\n\n[[package]]\nname = "sample"\nversion = "0.1.0"\nsource = { virtual = "." }\n\n[[package]]\nname = "dependency"\nversion = "2.0.0"\nsource = { registry = "https://pypi.org/simple" }\n')
        (self.root / 'CHANGELOG.md').write_text('# Histórico\n\n## Unreleased\n\n## 0.1.0 - 2026-11-01\n\nInitial.\n')
        self.commit('feat: start project')
        self.git('tag', 'v0.1.0')
        self.git('switch', '-c', 'feat/example')
        (self.root / 'feature.txt').write_text('Fictional feature')
        self.commit('feat: add example')
        self.repo = Repository(self.root)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], env=self.env,
                              check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-qm', message)

    def prepared(self):
        self.repo.prepare('2026-11-05')
        self.commit('chore(release): v0.2.0')
        return self.git('rev-parse', 'HEAD')

    def test_plan_is_read_only_and_prepare_changes_only_release_files(self):
        self.assertEqual(self.repo.plan()['version'], '0.2.0')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.repo.prepare('2026-11-05')
        self.assertEqual(set(self.git('diff', '--name-only').splitlines()), {'pyproject.toml', 'uv.lock', 'CHANGELOG.md'})
        self.assertIn('name = "dependency"\nversion = "2.0.0"', (self.root / 'uv.lock').read_text())
        self.assertEqual(self.repo.assert_versions()[0]['version'], '0.2.0')

    def test_dirty_tree_and_protected_branch_stop_before_changes(self):
        (self.root / 'feature.txt').write_text('Uncommitted')
        with self.assertRaises(ValueError):
            self.repo.prepare()
        self.commit('docs: note')
        self.git('branch', '-m', 'main-test')
        before = (self.root / 'pyproject.toml').read_bytes()
        with self.assertRaises(ValueError):
            self.repo.prepare()
        self.assertEqual((self.root / 'pyproject.toml').read_bytes(), before)

    def test_tag_drift_and_lock_mismatch_fail(self):
        self.git('tag', 'v0.1.1')
        with self.assertRaises(ValueError):
            self.repo.plan()
        (self.root / 'uv.lock').write_text((self.root / 'uv.lock').read_text().replace('version = "0.1.0"', 'version = "0.1.9"'))
        self.commit('chore: drift lock')
        with self.assertRaises(ValueError):
            self.repo.assert_versions()

    def test_publish_and_recovery_never_rewrite_tags(self):
        api = FakeGitHub(self.prepared())
        api.fail_release_once = True
        with self.assertRaises(ValueError):
            publish(self.repo, 'owner/project', '123', api)
        self.assertEqual(publish(self.repo, 'owner/project', '123', api)['status'], 'published')
        self.assertEqual(publish(self.repo, 'owner/project', '123', api)['status'], 'already_published')
        self.assertEqual(sum(path.endswith('/git/refs') for path, _ in api.posts), 1)
        self.assertTrue(api.release['prerelease'])
        self.assertTrue(all('/pulls' not in path and '/check-runs' not in path for path, _ in api.posts))

    def test_untrusted_ci_wrong_remote_and_failed_check_never_write(self):
        source = self.prepared()
        for patch in ({'event': 'pull_request'}, {'conclusion': 'failure'}, {'head_branch': 'feature'},
                      {'path': '.github/workflows/other.yml'}, {'head_repository': {'full_name': 'fork/project'}},
                      {'head_repository': None}, {'head_sha': 'invalid'}):
            api = FakeGitHub(source)
            api.run.update(patch)
            with self.assertRaises(ValueError):
                publish(self.repo, 'owner/project', '123', api)
            self.assertEqual(api.posts, [])
        api = FakeGitHub(source)
        api.quality = 'skipped'
        with self.assertRaises(ValueError):
            publish(self.repo, 'owner/project', '123', api)
        with self.assertRaises(ValueError):
            publish(self.repo, 'another/project', '123', api)
        self.assertEqual(api.posts, [])

    def test_unrelated_tag_is_preserved_and_conflicting_release_fails(self):
        source = self.prepared()
        api = FakeGitHub(source)
        api.ref = {'object': {'type': 'commit', 'sha': 'b' * 40}}
        api.unrelated = 'b' * 40
        with self.assertRaises(ValueError):
            publish(self.repo, 'owner/project', '123', api)
        self.assertEqual(api.posts, [])
        api = FakeGitHub(source)
        publish(self.repo, 'owner/project', '123', api)
        api.release['body'] = 'Different existing notes'
        with self.assertRaises(ValueError):
            publish(self.repo, 'owner/project', '123', api)


if __name__ == '__main__':
    unittest.main()
