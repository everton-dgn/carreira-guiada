"""Publish immutable tags from successful main CI, using only Python, Git and gh."""

import json
import re
import subprocess

from .versioning import plan_version, release_notes

SHA = re.compile(r'[0-9a-f]{40}')


class GitHub:
    def call(self, method, path, payload=None, optional=False):
        args = ['gh', 'api', '--method', method, path]
        if payload is not None:
            args += ['--input', '-']
        result = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, text=True, encoding='utf-8', timeout=60)
        try:
            value = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            raise ValueError('O GitHub retornou uma resposta inesperada.') from None
        if result.returncode:
            if optional and str(value.get('status')) == '404':
                return None
            raise ValueError(f'O GitHub recusou a operação {method} {path}.')
        return value


def assert_run(run, repository):
    if (run.get('status') != 'completed' or run.get('conclusion') != 'success'
            or run.get('event') != 'push' or run.get('head_branch') != 'main'
            or run.get('path') != '.github/workflows/checks.yml'
            or (run.get('head_repository') or {}).get('full_name', '').lower() != repository.lower()
            or not SHA.fullmatch(run.get('head_sha', ''))):
        raise ValueError('A release exige CI de push aprovada na main deste repositório.')
    return run['head_sha']


def require_ancestor(api, base, sha, main):
    result = api.call('GET', f'{base}/compare/{sha}...{main}')
    if result.get('status') not in {'ahead', 'identical'}:
        raise ValueError('O commit não pertence ao histórico atual da main.')


def tag_commit(api, base, ref):
    obj = ref.get('object', {})
    if obj.get('type') == 'tag':
        if not SHA.fullmatch(obj.get('sha', '')):
            raise ValueError('Tag inválida.')
        obj = api.call('GET', f"{base}/git/tags/{obj['sha']}").get('object', {})
    if obj.get('type') != 'commit' or not SHA.fullmatch(obj.get('sha', '')):
        raise ValueError('A tag não aponta diretamente para um commit.')
    return obj['sha']


def publish(repo, repository, run_id, api=None):
    api = api or GitHub()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) or not re.fullmatch(r'[1-9][0-9]*', str(run_id)):
        raise ValueError('Informe o repositório e o ID numérico da CI de origem.')
    repo.assert_clean()
    remote = repo.git('config', '--get', 'remote.origin.url')
    # The publication workflow checks out its repository through HTTPS.
    expected = {f'https://github.com/{repository}.git', f'https://github.com/{repository}'}
    if remote.lower() not in {value.lower() for value in expected}:
        raise ValueError('O repositório solicitado difere do origin deste checkout.')
    base = 'repos/' + repository
    run = api.call('GET', f'{base}/actions/runs/{run_id}')
    source = assert_run(run, repository)
    jobs = api.call('GET', f'{base}/actions/runs/{run_id}/jobs?per_page=100').get('jobs', [])
    quality = [job for job in jobs if job.get('name') == 'quality']
    if len(quality) != 1 or quality[0].get('conclusion') != 'success':
        raise ValueError('O check quality da execução não foi aprovado.')
    main = api.call('GET', f'{base}/git/ref/heads/main').get('object', {}).get('sha', '')
    if not SHA.fullmatch(main):
        raise ValueError('Referência main inválida.')
    require_ancestor(api, base, source, main)
    require_ancestor(api, base, repo.git('rev-parse', 'HEAD'), main)
    project, prerelease = repo.assert_versions(source)
    version, tag = project['version'], 'v' + project['version']
    existing_ref = api.call('GET', f'{base}/git/ref/tags/{tag}', optional=True)
    if existing_ref:
        tagged = tag_commit(api, base, existing_ref)
        if tagged != source:
            require_ancestor(api, base, tagged, source)
            if repo.manifest(tagged)['project']['version'] != version:
                raise ValueError('A tag existente tem uma versão diferente.')
            previous = api.call('GET', f'{base}/releases/tags/{tag}', optional=True)
            if previous is None or previous.get('draft'):
                raise ValueError('A tag existe sem release. Reexecute a publicação da CI original.')
            return {'status': 'unchanged', 'version': version, 'tag': tag}
    baseline = repo.baseline(source, exclude=tag)
    before = baseline[1:] if baseline else '0.0.0'
    if baseline and repo.manifest(baseline)['project']['version'] != before:
        raise ValueError('A tag anterior difere da versão registrada no projeto.')
    plan = plan_version(before, repo.commits(baseline, source))
    if not plan or plan['version'] != version:
        raise ValueError('Prepare a versão calculada pelos commits antes de publicar.')
    notes = release_notes(repo.read('CHANGELOG.md', source), version)
    if not existing_ref:
        tag_object = api.call('POST', f'{base}/git/tags', {
            'tag': tag, 'message': f'Carreira Guiada {tag}', 'object': source, 'type': 'commit',
            'tagger': {'name': 'Carreira Guiada contributors', 'email': 'release@example.invalid',
                       'date': repo.git('show', '-s', '--format=%cI', source)},
        })
        object_sha = tag_object.get('sha', '')
        if not SHA.fullmatch(object_sha):
            raise ValueError('O GitHub não confirmou o objeto da tag.')
        api.call('POST', f'{base}/git/refs', {'ref': 'refs/tags/' + tag, 'sha': object_sha})
    published = api.call('GET', f'{base}/releases/tags/{tag}', optional=True)
    if published:
        if published.get('draft') or published.get('prerelease') != prerelease or published.get('body', '').strip() != notes:
            raise ValueError('A release existente difere do conteúdo validado; ela foi preservada.')
        return {'status': 'already_published', 'version': version, 'tag': tag}
    result = api.call('POST', f'{base}/releases', {
        'tag_name': tag, 'name': f'Carreira Guiada {tag}', 'body': notes,
        'draft': False, 'prerelease': prerelease, 'make_latest': 'false' if prerelease else 'legacy',
    })
    return {'status': 'published', 'version': version, 'tag': tag, 'url': result.get('html_url')}
