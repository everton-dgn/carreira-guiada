"""Terminal presentation: pure rendering of projections, with fictional data."""
import copy
import io
import os
import re
import sys
import tempfile
import unicodedata
import unittest
from unittest.mock import patch

from rich.cells import cell_len

from scripts.job.terminal import render, sanitize

SGR = re.compile(r'\x1b\[([0-9;]*)m')


class Stream:
    """Writable stream with configurable tty and encoding; fileno is unsupported."""

    def __init__(self, tty=True, encoding='utf-8'):
        self.tty, self.encoding, self.buffer = tty, encoding, io.StringIO()

    def write(self, data):
        return self.buffer.write(data)

    def isatty(self):
        return self.tty

    def fileno(self):
        raise io.UnsupportedOperation('fileno')

    def getvalue(self):
        return self.buffer.getvalue()


def visible(output):
    return SGR.sub('', output)


def flat(output):
    """Join wrapped lines without borders or spaces, to compare facts."""
    lines = [visible(line).strip().strip('│|').strip() for line in output.split('\n')]
    return re.sub(r'\s+', '', ''.join(lines))


def colors(output):
    """Extract actual ANSI color codes for assertions about color-free output."""
    codes = set()
    for params in SGR.findall(output):
        codes.update(int(p) for p in params.split(';') if p)
    return {c for c in codes if 30 <= c <= 49 or 90 <= c <= 107}


PLAN = {
    'view': 'plan', 'exists': True, 'id': 'plan-1', 'version': 4, 'state': 'active',
    'direction': 'Análise de dados em saúde', 'next_step': 'personal_plan',
    'question': {'question': 'Quer fazer esse passo agora, diminuí-lo ou escolher outra atividade?'},
    'next_action': {'id': 'a2', 'title': 'Revisar consultas SQL', 'criterion': 'Três consultas resolvidas',
                    'smaller_step': 'Resolver uma consulta', 'estimated_minutes': 30, 'period': '2026-11-09'},
    'cycle': {'title': 'Ciclo de novembro', 'review_on': '2026-11-30'},
    'budget': {'weekly_minutes': 90, 'periods': [
        {'period': '2026-11-09', 'planned_minutes': 60, 'remaining_minutes': 30, 'over_by_minutes': 0},
        {'period': '2026-11-16', 'planned_minutes': 120, 'remaining_minutes': 0, 'over_by_minutes': 30}],
        'without_period': [{'id': 'a4', 'state': 'planned', 'period': None, 'estimated_minutes': None}]},
    'actions': [{'id': 'a1', 'state': 'completed', 'period': '2026-11-09', 'estimated_minutes': 45},
                {'id': 'a2', 'state': 'active', 'period': '2026-11-09', 'estimated_minutes': 30},
                {'id': 'a3', 'state': 'planned', 'period': '2026-11-16', 'estimated_minutes': 120},
                {'id': 'a4', 'state': 'planned', 'period': None, 'estimated_minutes': None}],
}
PLAN_TEXT = ('Meu plano\nSituação: em andamento.\nDireção: Análise de dados em saúde.\n'
             'Ciclo atual: Ciclo de novembro\nRevisão combinada: 2026-11-30\n'
             'Próximo passo: Revisar consultas SQL\nTermina quando: Três consultas resolvidas\n'
             'Se hoje couber menos: Resolver uma consulta\nTempo disponível por semana: 90 min.\n'
             'Semana de 2026-11-09: 60 min planejados; 30 min livres.\n'
             'Semana de 2026-11-16: 120 min planejados; 0 min livres.\n'
             'O plano ultrapassa sua disponibilidade em 30 min. Podemos reduzir ou adiar uma ação.\n'
             '1 ação(ões) ainda sem semana definida.\n'
             'Quer fazer esse passo agora, diminuí-lo ou escolher outra atividade?')
PROGRESS = {
    'view': 'progress', 'mode': 'points', 'version': 3, 'next_step': 'personal_progress',
    'question': {'question': 'Quer registrar uma prática que você fez, conferir um marco ou ajustar este acompanhamento?'},
    'practice_count': 3, 'reported_minutes': 45, 'unreported_time_count': 0, 'points': 30, 'milestones': [
        {'milestone_id': 'm1', 'kind': 'participation', 'title': 'Primeiro ensaio completo', 'needs_review': False},
        {'milestone_id': 'm2', 'kind': 'learning', 'title': 'Resposta mais objetiva', 'needs_review': True}],
    'evidence_warnings': ['Marco m2 precisa de revisão.'],
}
PROGRESS_TEXT = ('Minha evolução\nVocê escolheu: práticas, conquistas e pontos.\n'
                 'Treinos com autoria confirmada: 3.\nTempo informado por você: 45 min.\n'
                 'Pontos: 30. Convenção v1: 10 por treino confirmado, sem relação com a duração.\n'
                 'Marco: Primeiro ensaio completo (registrado).\nMarco: Resposta mais objetiva (precisa de revisão).\n'
                 'Marco m2 precisa de revisão.\n'
                 'Esses registros não medem seu valor nem garantem contratação. Você pode corrigir ou contestar uma avaliação.\n'
                 'Quer registrar uma prática que você fez, conferir um marco ou ajustar este acompanhamento?')
MENU = {'message': 'O que você quer fazer?', 'selected': None, 'choices': [
    {'number': '1', 'focus': 'curriculum', 'label': 'Currículo'},
    {'number': '2', 'focus': 'practice', 'label': 'Entrevistas'},
    {'number': '3', 'focus': 'career', 'label': 'Guia de carreira'},
    {'number': '4', 'focus': 'search', 'label': 'Busca de vagas'}]}
MENU_TEXT = ('O que você quer fazer?\n1. Currículo\n2. Entrevistas\n3. Guia de carreira\n'
             '4. Busca de vagas\n5. Mais opções\nDiga o número ou o nome.')


PROMOTED = {'Meu plano', 'Minha evolução', 'Situação: em andamento', 'Próximo passo: Revisar consultas SQL',
            'Você escolheu: práticas, conquistas e pontos'}


def facts(text):
    """Linear facts minus the lines the visual mode states once at the top."""
    lines = [line.strip().rstrip('.') for line in text.split('\n') if line.strip()]
    return [line for line in lines if line not in PROMOTED]


def squeeze(text):
    return re.sub(r'\s+', '', text)


class TerminalTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for name in ('NO_COLOR', 'TERM', 'COLUMNS', 'LINES', 'FORCE_COLOR', 'TTY_COMPATIBLE',
                     'TTY_INTERACTIVE', 'COLORTERM'):
            os.environ.pop(name, None)
        os.environ['TERM'] = 'xterm-256color'

    def tty(self, value, text, **options):
        stream = options.pop('stream', None) or Stream()
        output = render(value, text, stream=stream, **options)
        self.assertEqual(stream.getvalue(), '', 'render nunca escreve no stream')
        self.assertNotIn('\x1b', SGR.sub('', output), 'somente SGR é permitido')
        return output

    def test_plain_routes_return_sanitized_linear_text(self):
        """Explicit plain output preserves readable route text without styling."""
        text = 'Linha um\x1b[31m vermelha\x1b[0m\nLinha dois'
        expected = 'Linha um vermelha\nLinha dois'
        self.assertEqual(render(PLAN, text, stream=Stream(tty=False)), expected)
        self.assertEqual(render(PLAN, text, appearance='plain', stream=Stream()), expected)
        os.environ['TERM'] = 'dumb'
        self.assertEqual(render(PLAN, text, stream=Stream()), expected)

    def test_default_stream_is_stdout_and_pipe_stays_plain(self):
        """Piped output remains plain when no custom stream is provided."""
        with patch.object(sys, 'stdout', Stream(tty=False)):
            self.assertEqual(render(MENU, MENU_TEXT), MENU_TEXT)

    def test_choices_keep_numbers_and_appear_once(self):
        """Rendering preserves menu numbering without duplicating choices."""
        output = visible(self.tty(MENU, MENU_TEXT, width=60))
        for line in MENU_TEXT.split('\n'):
            self.assertEqual(output.count(line), 1, line)
        self.assertNotIn('6.', output)

    def test_choices_without_linear_line_are_shown_without_renumbering(self):
        """Choices missing from the prose remain available under their original numbers."""
        more = {'choices': [{'number': 'empresa', 'focus': 'company', 'label': 'Empresa'},
                            {'number': 'presença', 'focus': 'presence', 'label': 'LinkedIn/GitHub'}]}
        output = visible(self.tty(more, 'Mais opções:\nEmpresa\nDiga o nome da atividade.', width=60))
        self.assertEqual(output.count('Empresa'), 1)
        self.assertIn('LinkedIn/GitHub', output)
        self.assertNotRegex(output, r'\b1\.')

    def test_next_step_comes_first_and_plan_facts_are_equivalent(self):
        """Visual hierarchy promotes the next step without losing the plan facts."""
        before = copy.deepcopy(PLAN)
        output = self.tty(PLAN, PLAN_TEXT, width=120)
        self.assertEqual(PLAN, before, 'render não altera a projeção')
        lines = [visible(line) for line in output.split('\n') if visible(line).strip()]
        self.assertIn('Próximo passo', lines[0])
        self.assertIn('Revisar consultas SQL', lines[1])
        text = visible(output)
        self.assertLess(text.index('Revisar consultas SQL'), text.index('Direção'))
        self.assertLess(text.index('Direção'), text.index('Tempo disponível por semana'))
        self.assertNotIn('personal_plan', text, 'código de rota não aparece como passo')
        for fact in facts(PLAN_TEXT) + ['Três consultas resolvidas', 'Estimativa: 30 min']:
            self.assertEqual(text.count(fact), 1, fact)
        self.assertIn('Meu plano  •  em andamento', text)
        self.assertIn('● ─ ◐ ─ ○ ─ ○', text)
        self.assertIn('Sem semana definida: ○', text)
        self.assertNotIn('%', text)

    def test_over_budget_is_marked_and_weeks_stay_separate(self):
        """An overloaded week is identified without merging independent budgets."""
        text = visible(self.tty(PLAN, PLAN_TEXT, width=80))
        bars = [line for line in text.split('\n') if '█' in line]
        self.assertEqual(len(bars), 2)
        self.assertIn('░', bars[0])
        self.assertNotIn('acima', bars[0])
        self.assertIn('▸ 30 min acima', bars[1])
        self.assertLess(text.index('Semana de 2026-11-09'), text.index(bars[0]))
        self.assertLess(text.index(bars[0]), text.index('Semana de 2026-11-16'))

    def test_unknown_budget_and_estimate_have_no_bar_and_no_zero(self):
        """Unknown capacity must not appear as a measured zero or progress bar."""
        plan = {**PLAN, 'budget': {'weekly_minutes': None, 'without_period': [], 'periods': [
            {'period': '2026-11-09', 'planned_minutes': None, 'remaining_minutes': None, 'over_by_minutes': None},
            {'period': '2026-11-16', 'planned_minutes': 60, 'remaining_minutes': None, 'over_by_minutes': None}]}}
        text = visible(self.tty(plan, 'Tempo disponível por semana: a combinar.', width=80))
        self.assertIn('Tempo disponível por semana: a combinar', text)
        self.assertIn('Semana de 2026-11-09: estimativa incompleta; tempo livre a calcular', text)
        self.assertIn('Semana de 2026-11-16: 60 min planejados; tempo livre a calcular', text)
        self.assertNotIn('█', text)
        self.assertNotIn('0 min livres', text)
        self.assertNotIn('Sem semana definida', text)

    def test_paused_plan_is_labelled_without_progress_bars(self):
        """Paused plans retain their status and omit active capacity bars."""
        plan = {**PLAN, 'state': 'paused', 'next_action': None,
                'question': {'question': 'Seu plano está pausado. Quer retomá-lo, ajustar o próximo passo ou apenas consultar?'}}
        text = visible(self.tty(plan, 'Meu plano\nSituação: pausado.\n' + plan['question']['question'], width=120))
        self.assertIn('Meu plano  •  pausado', text)
        self.assertEqual(text.count(plan['question']['question']), 1)
        self.assertLess(text.index(plan['question']['question']), text.index('Meu plano'))
        self.assertNotIn('█', text)
        self.assertIn('Semana de 2026-11-09: 60 min planejados; 30 min livres', text)

    def test_missing_plan_shows_only_next_step_and_linear_text(self):
        """An absent plan does not produce fabricated visual indicators."""
        value = {'view': 'plan', 'exists': False, 'next_step': 'personal_plan', 'budget': None, 'actions': [],
                 'question': {'question': 'O que você quer conseguir primeiro? Pode dizer "não sei".'}}
        plain = 'Meu plano\nVamos escolher um objetivo e um primeiro passo que caiba na sua rotina.\n' + value['question']['question']
        output = self.tty(value, plain, width=60)
        text = visible(output)
        self.assertEqual(flat(output).count(squeeze(value['question']['question'])), 1)
        self.assertIn('Vamos escolher um objetivo', text)
        self.assertNotIn('Tempo disponível', text)
        self.assertNotIn('personal_plan', text)

    def test_prose_next_step_is_shown_when_there_is_no_action(self):
        """A readable next step remains visible without a structured action."""
        value = {'view': 'plan', 'exists': True, 'state': 'active', 'next_action': None,
                 'next_step': 'Revise o plano quando quiser.', 'budget': {'weekly_minutes': 30, 'periods': []}}
        lines = [visible(line) for line in self.tty(value, 'Plano em andamento.', width=60).split('\n')]
        self.assertIn('Revise o plano quando quiser.', lines[1])

    def test_progress_shows_indicators_and_evidence_caveats(self):
        """Enabled progress indicators retain warnings about their supporting evidence."""
        output = self.tty(PROGRESS, PROGRESS_TEXT, width=120)
        text = visible(output)
        self.assertIn(PROGRESS['question']['question'], text.split('\n')[1])
        for fact in ('Treinos com autoria confirmada: 3', '●●●', 'Tempo informado por você: 45 min', 'Pontos: 30',
                     'Primeiro ensaio completo • participação', 'Resposta mais objetiva • aprendizagem • precisa de revisão',
                     '! Marco m2 precisa de revisão.'):
            self.assertIn(fact, text)
        for fact in facts(PROGRESS_TEXT):
            self.assertIn(squeeze(fact), flat(output))
        self.assertEqual(text.count('Marco m2 precisa de revisão'), 1)
        self.assertNotIn('Você escolheu', text)
        self.assertNotIn('personal_progress', text)

    def test_progress_without_points_or_minutes_does_not_invent_values(self):
        """Missing scores and durations remain absent from the displayed summary."""
        value = {**PROGRESS, 'mode': 'tracking', 'points': None, 'reported_minutes': None, 'milestones': [],
                 'evidence_warnings': []}
        text = visible(self.tty(value, 'Minha evolução', width=80))
        self.assertNotIn('Pontos', text)
        self.assertIn('Tempo informado por você: não informado', text)
        partial = {**PROGRESS, 'unreported_time_count': 2}
        self.assertIn('45 min, total incompleto', visible(self.tty(partial, 'x', width=80)))

    def test_progress_off_has_no_scoreboard(self):
        """Disabled tracking does not display practice scores or points."""
        value = {**PROGRESS, 'mode': 'off', 'practice_count': None, 'reported_minutes': None,
                 'question': {'question': 'Quer guardar suas práticas, ver conquistas com evidências ou também usar pontos?'}}
        plain = ('Minha evolução\nAcompanhamento desativado. Você pode usar todas as atividades sem pontos ou conquistas.\n'
                 + value['question']['question'])
        text = visible(self.tty({**value, 'points': 30, 'practice_count': 3}, plain, width=120))
        self.assertIn('Minha evolução  •  acompanhamento desativado', text)
        self.assertIn('Você pode usar todas as atividades sem pontos ou conquistas.', text)
        self.assertIn(value['question']['question'], text)
        for hidden in ('Pontos:', 'Treinos com autoria', 'Marcos', '30', '●', 'Resposta mais objetiva'):
            self.assertNotIn(hidden, text)

    def test_other_commands_keep_whole_linear_text(self):
        """Unrecognized views retain their full plain-text response."""
        text = 'Falta conferir a sessão do portal.\nFaça o login na aba aberta e me avise quando terminar.\nPosso continuar?'
        output = visible(self.tty({'message': 'x', 'next_step': 'login', 'question': {'question': 'Posso continuar?'}},
                                  text, width=80))
        for line in text.split('\n'):
            self.assertEqual(output.count(line), 1, line)
        self.assertNotIn('Próximo passo', output)
        self.assertEqual(render([1, 2], 'lista', stream=Stream(), width=40).strip(), 'lista')

    def test_widths_keep_cells_and_long_text_without_cutting(self):
        """Supported terminal widths wrap long text without losing its content."""
        long_word = 'https://exemplo.invalid/' + 'caminho' * 30
        plan = {**PLAN, 'direction': 'Direção longa ' * 12 + long_word}
        text = PLAN_TEXT + '\n' + 'Texto longo do resumo ' * 15 + long_word
        for width in (40, 60, 80, 120):
            output = self.tty(plan, text, width=width)
            for line in visible(output).split('\n'):
                self.assertLessEqual(cell_len(line), width, (width, line))
                self.assertEqual(line, line.rstrip(), 'sem espaços à direita')
            joined = flat(output)
            self.assertIn(squeeze(plan['direction']), joined)
            for fact in facts(text):
                self.assertIn(squeeze(fact), joined, (width, fact))
            self.assertNotIn('…', visible(output))

    def test_width_falls_back_without_terminal_size(self):
        """A stream without terminal dimensions uses the documented fallback width."""
        output = self.tty(PLAN, PLAN_TEXT)
        self.assertTrue(all(cell_len(line) <= 80 for line in visible(output).split('\n')))

    def test_no_color_removes_colors_but_keeps_glyphs(self):
        """NO_COLOR disables styling colors while retaining supported glyphs."""
        self.assertTrue(colors(self.tty(PLAN, PLAN_TEXT, width=80)) & {34, 36})
        os.environ['NO_COLOR'] = '1'
        output = self.tty(PLAN, PLAN_TEXT, width=80)
        self.assertEqual(colors(output), set())
        self.assertIn('╭', output)
        self.assertIn('●', output)

    def test_motion_is_accepted_without_animation(self):
        """The motion preference cannot start an animation or change a static render."""
        still = self.tty(PROGRESS, PROGRESS_TEXT, width=80)
        self.assertEqual(self.tty(PROGRESS, PROGRESS_TEXT, width=80, motion=True), still)
        self.assertNotRegex(still, r'\x1b\[\?|\x1b\[[0-9;]*[ABCDEFGHJKST]|\r')

    def test_ascii_encoding_uses_ascii_boxes(self):
        """Unsupported glyph encodings select ASCII decorative borders."""
        output = visible(self.tty(PLAN, 'Resumo simples', width=80, stream=Stream(encoding='ascii')))
        drawing = ''.join(ch for ch in output if not unicodedata.category(ch).startswith(('L', 'M')))
        self.assertTrue(all(ord(ch) < 128 for ch in drawing), drawing)
        self.assertIn('+-', output)

    def test_markup_is_literal(self):
        """User-supplied bracket syntax remains literal rather than Rich markup."""
        hostile = '[bold red]x[/bold red] :smile: [link=https://exemplo.invalid]y[/link]'
        plan = {**PLAN, 'direction': hostile}
        output = self.tty(plan, hostile, width=120)
        self.assertIn(hostile, visible(output))
        self.assertNotIn('\x1b]8', output)
        self.assertNotIn('😄', output)

    def test_terminal_sequences_and_bidi_controls_are_neutralized(self):
        """Untrusted terminal and bidirectional controls cannot affect display state."""
        hostile = ('Vaga\x1b]8;;https://mal.invalid\x07link\x1b]8;;\x07 \x1b[2J\x1b[?25l'
                   '\x9b31mfim \u202eodnum\u202c \u2066x\u2069 \x07\x00\x85\x1b]0;título\x1b\\ok')
        self.assertEqual(sanitize(hostile), 'Vagalink fim odnum x ok')
        self.assertEqual(sanitize('Vaga\x1b_x\nPosso continuar?'), 'Vaga\nPosso continuar?')
        self.assertEqual(sanitize('A\x90dcs\nB?'), 'A\nB?')
        plan = {**PLAN, 'direction': hostile, 'next_step': hostile}
        output = self.tty(plan, hostile, width=80)
        for bad in ('\x1b]', '\x9b', '\x9d', '\u202e', '\u2066', '\x07', '\x00', '\x85', '\x1b[2J', '\x1b[?'):
            self.assertNotIn(bad, output)
        self.assertEqual(render(plan, hostile, stream=Stream(tty=False)), 'Vagalink fim odnum x ok')

    def test_legitimate_unicode_is_preserved(self):
        """Sanitization preserves legitimate accented and non-Latin text."""
        text = 'São Paulo, ação, coração\n👩\u200d💻 Dev 👍🏽 ❤️ é\ncoluna\tdois\r\nfim'
        self.assertEqual(sanitize(text), 'São Paulo, ação, coração\n👩\u200d💻 Dev 👍🏽 ❤️ é\ncoluna\tdois\nfim')
        output = visible(self.tty({'view': 'progress', 'mode': 'off'}, text, width=60))
        for piece in ('São Paulo, ação, coração', '👩\u200d💻 Dev 👍🏽 ❤️ é'):
            self.assertIn(piece, output)

    def test_missing_rich_falls_back_to_plain(self):
        """An unavailable optional renderer leaves usable plain output."""
        with patch.dict(sys.modules, {'rich': None, 'rich.console': None}):
            self.assertEqual(render(PLAN, PLAN_TEXT, stream=Stream(), width=80), PLAN_TEXT)

    def test_render_creates_no_files(self):
        """Rendering remains read-only even when a rich view is requested."""
        with tempfile.TemporaryDirectory() as folder:
            cwd = os.getcwd()
            os.chdir(folder)
            try:
                render(PLAN, PLAN_TEXT, stream=Stream(), width=80)
                render(PLAN, PLAN_TEXT, stream=Stream(tty=False))
            finally:
                os.chdir(cwd)
            self.assertEqual(os.listdir(folder), [])


if __name__ == '__main__':
    unittest.main()
