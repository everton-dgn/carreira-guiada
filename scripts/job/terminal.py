"""Terminal presentation of projections already computed by the CLI.

Rendering is pure: it returns text, never prints, reads the database, opens
processes or decides authorization. The linear `plain_text` supplied by the
caller is the source of truth; the visual mode only promotes a few fields to
the top and keeps every remaining linear line once at the end.
"""
import io
import os
import re
import sys
import unicodedata

_SEQUENCES = re.compile(
    r'(?:\x1b\][^\x07\x1b\x9c\n]*(?:\x07|\x1b\\|\x9c)?'    # OSC até BEL/ST
    r'|\x9d[^\x07\x1b\x9c\n]*(?:\x07|\x1b\\|\x9c)?'
    r'|\x1b[PX^_][^\x1b\x9c\n]*(?:\x1b\\|\x9c)?'               # DCS, SOS, PM, APC
    r'|[\x90\x98\x9e\x9f][^\x1b\x9c\n]*(?:\x1b\\|\x9c)?'
    r'|(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]?'                    # CSI
    r'|\x1b[ -/]*[0-~]?)'                                    # demais escapes
)
_TRAILING = re.compile(r'(?:[ ]|\x1b\[[0-9;]*m)+$')
_SGR = re.compile(r'\x1b\[[0-9;]*m')
_BIDI = frozenset('\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff')
_PLAN_STATES = {'active': 'em andamento', 'paused': 'pausado', 'archived': 'arquivado'}
_ACTION_STATES = ('completed', 'active', 'planned', 'deferred', 'cancelled')
_ACTION_LABELS = {'completed': 'concluída', 'active': 'em andamento', 'planned': 'planejada',
                  'deferred': 'adiada', 'cancelled': 'cancelada'}
_MODES = {'off': 'acompanhamento desativado', 'tracking': 'práticas registradas',
          'achievements': 'práticas e conquistas', 'points': 'práticas, conquistas e pontos'}
_KINDS = {'participation': 'participação', 'learning': 'aprendizagem'}
_GLYPHS = {
    'unicode': {'completed': '●', 'active': '◐', 'planned': '○', 'deferred': '◌', 'cancelled': '×',
                'link': ' ─ ', 'full': '█', 'empty': '░', 'over': '▸', 'next': '→', 'item': '•',
                'milestone': '◆', 'warning': '!', 'tally': '●', 'rule': '─'},
    'ascii': {'completed': '*', 'active': '>', 'planned': 'o', 'deferred': '~', 'cancelled': 'x',
              'link': ' - ', 'full': '#', 'empty': '.', 'over': '+', 'next': '->', 'item': '-',
              'milestone': '*', 'warning': '!', 'tally': '*', 'rule': '-'},
}
_MAX_WIDTH = 100
_MIN_WIDTH = 20
_BAR = 24
_TALLY = 20


def sanitize(text):
    """Neutralize terminal sequences and invisible direction controls.

    Keeps line breaks, tabs, accents, combining marks, ZWJ and variation
    selectors, so legitimate emoji sequences survive unchanged.
    """
    text = _SEQUENCES.sub('', str(text).replace('\r\n', '\n'))
    out = []
    for ch in text:
        if ch in '\n\t':
            out.append(ch)
        elif ch in '\u2028\u2029':
            out.append('\n')
        elif ch in _BIDI or unicodedata.category(ch) == 'Cc':
            continue
        else:
            out.append(ch)
    return ''.join(out)


def render(value, plain_text, *, appearance='auto', motion=False, width=None, stream=None):
    """Return the presentation for `stream` without writing to it.

    `motion` is accepted for compatibility and never produces animation.
    """
    del motion
    stream = sys.stdout if stream is None else stream
    plain = sanitize('' if plain_text is None else plain_text)
    if appearance == 'plain' or os.environ.get('TERM', '').strip().lower() == 'dumb' or not _isatty(stream):
        return plain
    try:
        return _Visual(value, plain, _width(width, stream), _unicode(stream),
                       os.environ.get('NO_COLOR', '') != '').output()
    except ImportError:
        return plain


def _isatty(stream):
    """Detect a terminal conservatively when stream capabilities are unavailable."""
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError, ValueError):
        return False


def _width(width, stream):
    """Resolve terminal columns and clamp them to supported layout bounds."""
    if type(width) is not int:
        try:
            width = os.get_terminal_size(stream.fileno()).columns
        except (AttributeError, OSError, ValueError):
            width = 80
    return max(_MIN_WIDTH, min(width, _MAX_WIDTH))


def _unicode(stream):
    """Check whether the stream encoding supports every decorative glyph."""
    encoding = getattr(stream, 'encoding', None)
    if not encoding:
        return False
    try:
        ''.join(_GLYPHS['unicode'].values()).encode(encoding)
        '╭─╮│╰╯'.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def _key(line):
    """Normalize a displayed line for exact-fact deduplication."""
    return line.strip().rstrip('.').strip()


def _int(item):
    """Accept integers without treating booleans as numeric measurements."""
    return item if type(item) is int else None


def _text(item):
    """Return sanitized nonempty text or an absent-field marker."""
    return sanitize(item).strip() if isinstance(item, str) and item.strip() else None


class _Visual:
    """Build one capture console and the ordered sections of a projection."""

    def __init__(self, value, plain, width, unicode_ok, no_color):
        """Create a private capture console with fixed capabilities and literal text."""
        from rich import box
        from rich.console import Console
        self.value = value if isinstance(value, dict) else {}
        self.plain = plain
        self.width = width
        self.glyph = _GLYPHS['unicode' if unicode_ok else 'ascii']
        self.box = box.ROUNDED if unicode_ok else box.ASCII
        self.console = Console(file=io.StringIO(), width=width, height=25, force_terminal=True,
                               force_jupyter=False, force_interactive=False, color_system='standard',
                               no_color=no_color, markup=False, emoji=False, highlight=False,
                               legacy_windows=False, safe_box=True, soft_wrap=False)
        self.shown = set()

    def line(self, *parts, same=()):
        """Literal text from (content, style) pairs; content never becomes markup.

        `same` names linear lines that state exactly this fact, so the summary
        does not repeat them.
        """
        from rich.text import Text
        text = Text(overflow='fold', no_wrap=False)
        for content, style in parts:
            text.append(content, style=style)
        self.shown.update(_key(item) for item in (text.plain, *same))
        return text

    def print(self, renderable=None):
        """Append a padded renderable or blank line to the capture console."""
        from rich.padding import Padding
        if renderable is None:
            self.console.print()
        else:
            self.console.print(Padding(renderable, (0, 1), expand=False))

    def output(self):
        """Render the selected view and retain remaining plain-text facts."""
        view = self.value.get('view')
        if view == 'plan':
            self.plan()
        elif view == 'progress':
            self.progress()
        self.linear()
        return '\n'.join(_TRAILING.sub(lambda m: ''.join(_SGR.findall(m.group())), line)
                         for line in self.console.file.getvalue().rstrip('\n').split('\n'))

    def step(self):
        """Human next step; machine route codes such as `record` are never shown."""
        step = _text(self.value.get('next_step'))
        return step if step and any(ch.isspace() for ch in step) else None

    def question(self):
        """Read the contextual question without accepting malformed payloads."""
        question = self.value.get('question')
        return _text(question.get('question')) if isinstance(question, dict) else None

    def next_box(self, headline=None, extra=(), same=()):
        """Place the next action and contextual question in one highlighted panel."""
        from rich.console import Group
        from rich.panel import Panel
        headline = headline or self.step()
        lines = [self.line((self.glyph['next'] + ' ', 'bold cyan'), (headline, 'bold'), same=same)] if headline else []
        lines += list(extra)
        question = self.question()
        if question and _key(question) not in {_key(line.plain) for line in lines}:
            lines.append(self.line((question, 'cyan')))
        if lines:
            self.console.print(Panel(Group(*lines), title=self.line(('Próximo passo', 'bold blue')),
                                     title_align='left', box=self.box, border_style='blue', padding=(0, 1)))

    def heading(self, title, detail=None, same=()):
        """Render a section title and record equivalent plain-text lines."""
        parts = [(title, 'bold blue')]
        if detail:
            parts += [('  ' + self.glyph['item'] + '  ', 'cyan'), (detail, 'bold')]
        self.print(self.line(*parts, same=(title, *same)))

    def field(self, label, content):
        """Render a labeled field only when a value is present."""
        if content is not None:
            self.print(self.line((label + ': ', 'cyan'), (content, None)))

    def plan(self):
        """Present the next action before saved direction, state and weekly capacity."""
        action = self.value.get('next_action')
        if not isinstance(action, dict):
            action = {}
        title = _text(action.get('title'))
        extra = []
        for key, label in (('reason', 'Para quê'), ('criterion', 'Termina quando'), ('smaller_step', 'Se hoje couber menos')):
            if _text(action.get(key)):
                extra.append(self.line((label + ': ', 'cyan'), (_text(action[key]), None)))
        if_then = self.if_then(action.get('if_then'))
        if if_then:
            extra.append(self.line(('Se, então: ', 'cyan'), (if_then, None)))
        if _int(action.get('estimated_minutes')) is not None:
            extra.append(self.line(('Estimativa: ', 'cyan'), (f"{action['estimated_minutes']} min", None)))
        self.next_box(title, extra, same=(f'Próximo passo: {title}',) if title else ())
        exists = self.value.get('exists') is not False
        state = _PLAN_STATES.get(self.value.get('state')) if exists else None
        self.heading('Meu plano', state, same=(f'Situação: {state}',) if state else ())
        if not exists:
            return
        self.field('Direção', _text(self.value.get('direction')) or 'a combinar')
        cycle = self.value.get('cycle') if isinstance(self.value.get('cycle'), dict) else {}
        if _text(cycle.get('title')):
            self.field('Ciclo atual', _text(cycle['title']))
            self.field('Revisão combinada', _text(cycle.get('review_on')))
        self.path()
        self.budget(self.value.get('state') in ('paused', 'archived'))

    @staticmethod
    def if_then(item):
        """Normalize a textual or structured implementation intention for display."""
        if isinstance(item, str):
            return _text(item)
        if isinstance(item, dict) and _text(item.get('if')) and _text(item.get('then')):
            return f"se {_text(item['if'])}, então {_text(item['then'])}"
        return None

    def actions(self):
        """Select dictionary actions whose states have known visual labels."""
        items = self.value.get('actions')
        return [a for a in items if isinstance(a, dict) and a.get('state') in _ACTION_STATES] if isinstance(items, list) else []

    def path(self):
        """Show action-state glyphs with a legend limited to states actually present."""
        actions = self.actions()
        if not actions:
            return
        self.print(self.line(('Caminho: ', 'cyan'),
                             (self.glyph['link'].join(self.glyph[a['state']] for a in actions), 'blue')))
        present = [s for s in _ACTION_STATES if any(a['state'] == s for a in actions)]
        legend = '  '.join(f'{self.glyph[s]} {_ACTION_LABELS[s]}' for s in present)
        self.print(self.line(('         ' if self.width >= 60 else '', None), (legend, 'dim')))

    @staticmethod
    def periods(budget):
        """Normalize list or keyed weekly budgets without inferring missing values."""
        periods = budget.get('periods')
        if isinstance(periods, dict):
            periods = [{'period': k, **v} for k, v in sorted(periods.items()) if isinstance(v, dict)]
        return [p for p in periods if isinstance(p, dict)] if isinstance(periods, list) else []

    def budget(self, stopped):
        """Show weekly estimates and suppress capacity bars for paused plans."""
        budget = self.value.get('budget') if isinstance(self.value.get('budget'), dict) else {}
        weekly = _int(budget.get('weekly_minutes'))
        self.field('Tempo disponível por semana', 'a combinar' if weekly is None else f'{weekly} min')
        for period in self.periods(budget):
            label = _text(period.get('period'))
            if label is None:
                continue
            planned = _int(period.get('planned_minutes'))
            remaining, over = _int(period.get('remaining_minutes')), _int(period.get('over_by_minutes'))
            estimate = 'estimativa incompleta' if planned is None else f'{planned} min planejados'
            free = '; tempo livre a calcular' if remaining is None else f'; {remaining} min livres'
            self.print(self.line((f'Semana de {label}: ', 'cyan'), (estimate + free, 'bold' if over else None)))
            if weekly is not None and planned is not None and not stopped:
                self.print(self.bar(planned, weekly, over))
        loose = budget.get('without_period')
        if not isinstance(loose, list):
            loose = [a for a in self.actions() if a.get('period') is None and a['state'] in ('planned', 'active')]
        loose = [a for a in loose if isinstance(a, dict) and a.get('state') in _ACTION_STATES]
        if loose:
            self.print(self.line(('Sem semana definida: ', 'cyan'),
                                 (' '.join(self.glyph[a['state']] for a in loose), 'blue')))

    def bar(self, planned, weekly, over):
        """Planned minutes against weekly availability, never a completion rate."""
        size = max(8, min(_BAR, self.width - 20))
        if weekly <= 0:
            filled = size if planned > 0 else 0
        else:
            filled = min(size, -(-planned * size // weekly))
        parts = [(self.glyph['full'] * filled, 'cyan'), (self.glyph['empty'] * (size - filled), 'blue')]
        if self.glyph is _GLYPHS['ascii']:
            parts = [('[', None)] + parts + [(']', None)]
        if over:
            parts.append((f" {self.glyph['over']} {over} min acima", 'bold'))
        return self.line(*parts)

    def progress(self):
        """Show only the indicators enabled by the chosen tracking mode."""
        self.next_box()
        mode = self.value.get('mode')
        label = _MODES.get(mode)
        self.heading('Minha evolução', label, same=(f'Você escolheu: {label}',) if label else ())
        if mode not in _MODES or mode == 'off':
            return
        count = _int(self.value.get('practice_count'))
        if count is not None:
            self.field('Treinos com autoria confirmada', str(count))
            if count:
                more = ('…' if self.glyph is _GLYPHS['unicode'] else '+') if count > _TALLY else ''
                self.print(self.line((self.glyph['tally'] * min(count, _TALLY) + more, 'blue')))
        minutes = _int(self.value.get('reported_minutes'))
        incomplete = ', total incompleto' if _int(self.value.get('unreported_time_count')) else ''
        self.field('Tempo informado por você', f'{minutes} min{incomplete}' if minutes is not None else 'não informado')
        self.points(self.value.get('points'))
        self.milestones()
        warnings = self.value.get('evidence_warnings')
        warnings = [_text(w) for w in warnings if _text(w)] if isinstance(warnings, list) else []
        if warnings:
            self.print(self.line(('Ressalvas', 'bold blue')))
            for warning in warnings:
                self.print(self.line((self.glyph['warning'] + ' ', 'bold cyan'), (warning, None), same=(warning,)))

    def points(self, points):
        """Display supplied points and an optional explanation without inventing totals."""
        if _int(points) is not None:
            self.field('Pontos', str(points))
        elif isinstance(points, dict):
            total = _int(points.get('total'))
            if total is None:
                total = _int(points.get('value'))
            if total is not None:
                self.field('Pontos', str(total))
            rule = _text(points.get('rule')) or _text(points.get('explanation'))
            if rule:
                self.print(self.line((rule, 'dim')))

    def milestones(self):
        """Present named milestones with contestation and stale-evidence warnings."""
        items = self.value.get('milestones')
        items = [m for m in items if isinstance(m, dict) and _text(m.get('title'))] if isinstance(items, list) else []
        if not items:
            return
        self.print(self.line(('Marcos', 'bold blue')))
        for item in items:
            parts = [(self.glyph['milestone'] + ' ', 'cyan'), (_text(item['title']), None)]
            if item.get('kind') in _KINDS:
                parts.append((f" {self.glyph['item']} {_KINDS[item['kind']]}", 'dim'))
            status = {item.get('state'), item.get('status')}
            if item.get('contested') is True or 'contested' in status:
                parts.append((f" {self.glyph['item']} contestado, precisa de revisão", 'bold'))
            elif item.get('needs_review') is True or 'needs_review' in status:
                parts.append((f" {self.glyph['item']} precisa de revisão", 'bold'))
            self.print(self.line(*parts))

    def choice_lines(self):
        """Map linear lines to the given choices, keeping their own numbering."""
        choices = self.value.get('choices')
        choices = [c for c in choices if isinstance(c, dict) and _text(c.get('label'))] if isinstance(choices, list) else []
        numbered, labelled, missing = {}, {}, []
        lines = {line.strip() for line in self.plain.split('\n')}
        for choice in choices:
            label, number = _text(choice['label']), _text(choice.get('number'))
            if number and f'{number}. {label}' in lines:
                numbered[f'{number}. {label}'] = number
            elif label in lines:
                labelled[label] = True
            else:
                missing.append((number, label))
        return numbered, labelled, missing

    def linear(self):
        """Preserve unpromoted prose and every menu option without renumbering."""
        from rich.rule import Rule
        numbered, labelled, missing = self.choice_lines()
        promoted = self.shown.copy()
        body, blank = [], False
        for raw in self.plain.split('\n'):
            line = raw.strip()
            if line and _key(line) in promoted:
                continue
            if not line:
                blank = bool(body)
                continue
            if blank:
                body.append(None)
                blank = False
            if line in numbered:
                number = numbered[line]
                body.append(self.line((number + '.', 'bold cyan'), (line[len(number) + 1:], None)))
            elif line in labelled:
                body.append(self.line((self.glyph['item'] + ' ', 'bold cyan'), (raw.rstrip(), None)))
            else:
                body.append(self.line((raw.rstrip(), None)))
        if missing:
            body.append(None)
            body.append(self.line(('Opções', 'bold blue')))
            for number, label in missing:
                if number and number.isdigit():
                    body.append(self.line((number + '.', 'bold cyan'), (' ' + label, None)))
                else:
                    body.append(self.line((self.glyph['item'] + ' ', 'bold cyan'), (label, None)))
        if not body:
            return
        if self.value.get('view') in ('plan', 'progress'):
            self.console.print(Rule(self.line(('Resumo', 'dim')), characters=self.glyph['rule'],
                                    style='blue', align='left'))
        for item in body:
            self.print(item)
