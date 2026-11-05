"""Conventional Commit rules and release notes, independent of Git and network."""

from datetime import date
import html
import re

VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SUBJECT = re.compile(r"([a-z]+)(?:\(([^)\r\n]+)\))?(!)?: (.+)")


def version_parts(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError("A versão precisa ter o formato X.Y.Z, sem zeros à esquerda.")
    return tuple(map(int, value.split('.')))


def breaking_footer(body):
    fence = None
    for line in body.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            run, rest = marker.groups()
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
                fence = None
        elif fence is None and re.match(r"^BREAKING[ -]CHANGE:\s+\S", line):
            return True
    return False


def classify(message):
    subject, _, body = message.partition('\n')
    match = SUBJECT.fullmatch(subject.rstrip('\r'))
    if not match:
        return None
    kind, scope, breaking, summary = match.groups()
    if breaking or breaking_footer(body):
        return 3, 'Mudanças incompatíveis', summary
    if kind == 'feat':
        return 2, 'Novidades', summary
    if kind in {'fix', 'perf', 'revert'} or (kind in {'chore', 'build'} and scope in {'deps', 'deps-dev'}):
        return 1, 'Correções', summary
    return None


def escaped_summary(value):
    value = html.escape(value, quote=False)
    return re.sub(r"([\\`*_[\]#])", r"\\\1", value).replace('@', '&#64;')


def plan_version(current, commits):
    parts = list(version_parts(current))
    changes = [(sha, classify(message)) for sha, message in commits]
    changes = [(sha, item) for sha, item in changes if item]
    if not changes:
        return None
    bump = max(item[0] for _, item in changes)
    index = 3 - bump
    parts[index] += 1
    parts[index + 1:] = [0] * (2 - index)
    notes = []
    for section in ('Novidades', 'Mudanças incompatíveis', 'Correções'):
        entries = [f"- {escaped_summary(item[2])} ({sha[:7]})" for sha, item in changes if item[1] == section]
        if entries:
            notes.append('### ' + section + '\n\n' + '\n'.join(entries))
    return {'version': '.'.join(map(str, parts)), 'notes': '\n\n'.join(notes)}


def prepare_changelog(changelog, version, notes, day):
    date.fromisoformat(day)
    headings = list(re.finditer(r'^## Unreleased[ \t]*$', changelog, re.M))
    if len(headings) != 1:
        raise ValueError('CHANGELOG.md precisa ter uma única seção ## Unreleased.')
    if re.search(r'^## ' + re.escape(version) + r'(?:\s|$)', changelog, re.M):
        raise ValueError('A versão já está registrada no changelog.')
    start = headings[0].end()
    following = re.search(r'^## ', changelog[start:], re.M)
    end = start + following.start() if following else len(changelog)
    curated = changelog[start:end].strip()
    notes = curated or notes
    if not notes:
        raise ValueError('A release precisa de notas.')
    result = changelog[:start].rstrip() + f'\n\n## {version} - {day}\n\n' + notes
    if changelog[end:].strip():
        result += '\n\n' + changelog[end:].strip()
    return result + '\n', notes


def release_notes(changelog, version):
    match = re.search(r'^## ' + re.escape(version) + r' - (\d{4}-\d{2}-\d{2})[ \t]*\n', changelog, re.M)
    if not match:
        raise ValueError('Falta a seção datada da versão no changelog.')
    date.fromisoformat(match.group(1))
    remaining = changelog[match.end():]
    next_heading = re.search(r'^## ', remaining, re.M)
    notes = remaining[:next_heading.start() if next_heading else len(remaining)].strip()
    if not notes:
        raise ValueError('As notas da release estão vazias.')
    return notes
