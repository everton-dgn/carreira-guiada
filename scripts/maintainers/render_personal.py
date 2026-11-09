"""Capture the real terminal renderer with fictional, temporary private records."""
import html
import base64
from functools import lru_cache
import io
import os
from pathlib import Path
import tempfile

from PIL import Image
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.style import Style
from rich.terminal_theme import TerminalTheme
from rich.text import Text

from scripts.job.personal_views import entry
from scripts.job.planning import PersonalPlan
from scripts.job.practice import Practice
from scripts.job.personal_progress import PersonalProgress
from scripts.job.terminal import render
from scripts.maintainers.render_docs import BLUE, INK, LINE, MUTED, font, white_palette

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/assets'
COLORS = [(16, 41, 81), (180, 35, 24), (20, 108, 67), (143, 94, 0),
          (40, 100, 237), (123, 63, 180), (40, 100, 237), (16, 41, 81)]
THEME = TerminalTheme((255, 255, 255), (16, 41, 81), COLORS, COLORS)


class Terminal:
    """Describe a UTF-8 terminal without opening or changing a visible window."""
    encoding = 'utf-8'

    def isatty(self):
        """Enable the same visual mode used by an interactive terminal."""
        return True


def scenes(root):
    """Build projections by the same services and entry points as the CLI."""
    service = PersonalPlan(root)
    plan = service.start({'direction': 'Encontrar uma vaga de atendimento', 'weekly_minutes': 90,
                         'cycle': {'title': 'Preparar minha apresentação'}})
    for ident, title, minutes in [('intro', 'Ensaiar minha apresentação', 20), ('example', 'Preparar um exemplo profissional', 40)]:
        plan = service.action({'id': plan['id'], 'expected_version': plan['version'], 'action': {
            'id': ident, 'activity': 'practice', 'title': title, 'reason': 'Explicar minha experiência com clareza.',
            'criterion': 'Contar um exemplo e conferir o feedback.', 'estimated_minutes': minutes,
            'period': '2026-11-09', 'smaller_step': 'Ensaiar a primeira frase por cinco minutos.'}})
    result = [('Seu objetivo, um passo de cada vez.', '90 minutos disponíveis. 60 planejados. Espaço para a vida acontecer.',
               './job plan show', entry(root, 'plan'))]
    plan = service.transition({'id': plan['id'], 'expected_version': plan['version'], 'action_id': 'intro',
                              'state': 'completed', 'evidence': {'kind': 'user_report',
                              'description': 'Nina Exemplo confirmou o ensaio.', 'criterion': 'Contar um exemplo e conferir o feedback.'}})
    result.append(('O que você fez fica salvo.', 'Um próximo passo claro, com uma versão menor para os dias difíceis.',
                   './job plan show', entry(root, 'plan')))
    service.pause({'id': plan['id'], 'expected_version': plan['version']})
    result.append(('Pode parar. O plano espera.', 'Na volta, escolha continuar, ajustar ou trocar de atividade.',
                   './job start --focus plan', entry(root, 'plan')))
    practice = Practice(root)
    started = practice.start('presentation', 'coach', short=True)
    sid, qid = started['session_id'], started['question']['id']
    progress = PersonalProgress(root)
    state = progress.configure({'expected_version': 0, 'mode': 'points'})
    for version in (1, 2):
        practice.answer(sid, qid, 'Atendi clientes e organizei pedidos em uma empresa fictícia.',
                        attempt_id=f'fictional-{version}', origin='person', user_confirmation='Eu fiz este ensaio.')
        state = progress.record({'expected_version': state['version'], 'event_id': f'practice-{version}',
            'activity': 'practice', 'source': {'kind': 'practice', 'session_id': sid, 'question_id': qid, 'version': version},
            'user_confirmation': 'Ensaiei a resposta.', 'reported_minutes': 5,
            'occurred_at': f'2026-11-09T12:{version}0:00-03:00'})
    progress.milestone({'expected_version': state['version'], 'milestone_id': 'first-practices',
        'kind': 'participation', 'title': 'Primeiros ensaios', 'criterion': 'Registrar duas tentativas pessoais.',
        'event_ids': ['practice-1', 'practice-2'], 'assessment': 'Duas práticas com autoria confirmada.'})
    result.append(('Enxergue o que você praticou.', 'Conquistas com evidências. Pontos opcionais. Sem cobrança por ausência.',
                   './job progress show', entry(root, 'progress')))
    return result


def fragment(ansi):
    """Convert actual ANSI text to literal HTML with a readable terminal palette."""
    console = Console(record=True, file=io.StringIO(), width=76, force_terminal=True)
    content = Text.from_ansi(ansi)
    # ANSI dim is blended toward the background; use the guide's readable gray.
    content.spans = [span._replace(style=span.style + Style(color=MUTED, dim=False))
                     if span.style.dim else span for span in content.spans]
    console.print(content, end='')
    return console.export_html(inline_styles=True, theme=THEME, code_format='{code}')


@lru_cache
def font_css():
    """Embed the same locally selected fonts used by the other demo renderers."""
    rules = []
    for name, mono, bold in [('Editorial', False, False), ('Editorial', False, True), ('Terminal', True, False)]:
        data = base64.b64encode(Path(font(20, mono, bold).path).read_bytes()).decode('ascii')
        weight = 'bold' if bold else 'normal'
        rules.append(f"@font-face{{font-family:{name};font-weight:{weight};src:url(data:font/ttf;base64,{data})}}")
    return ''.join(rules)


def page(title, subtitle, request, command, body, scene):
    """Frame real output consistently, separating the person's request from CLI use."""
    segments = ''.join('<i class="{}"></i>'.format('done' if number <= scene else '') for number in range(4))
    operation = 'Consulta feita pela IA: ' + command if command else ''
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<style>{font_css()}
*{{box-sizing:border-box}}body{{margin:0;width:1120px;height:700px;background:#07152e;color:#f3f7ff;
font-family:Editorial,Arial,sans-serif;}}
.brand{{position:absolute;left:40px;right:40px;top:29px;height:34px;border-bottom:1px solid #28426a;
font-size:16px;display:flex;justify-content:space-between;}}
.brand strong{{border-left:4px solid #60d9f4;padding-left:11px;height:20px}}
.note{{color:#a4bcdf}}h1{{position:absolute;left:40px;top:80px;font-size:40px;margin:0;}}
.subtitle{{position:absolute;left:40px;top:136px;font-size:23px;color:#a4bcdf;margin:0}}
.terminal{{position:absolute;left:40px;top:192px;width:1040px;height:418px;padding:16px 22px;
border:1px solid {LINE};border-radius:16px;background:#ffffff;color:{INK};}}
.prompt{{color:{BLUE};font:20px Terminal,monospace;height:28px;white-space:pre}}
.command{{color:{MUTED};font:16px Editorial,sans-serif;height:27px;}}
pre{{font:20px/23px Terminal,monospace;margin:0;white-space:pre;}}
.viewport{{height:322px;overflow:hidden}}
.continuation{{font:16px Editorial,sans-serif;color:{MUTED};height:20px;padding-top:2px}}
.foot{{position:absolute;top:632px;left:40px;color:#a4bcdf;font-size:20px;}}
.steps{{position:absolute;left:40px;right:40px;top:685px;display:flex;gap:16px}}
.steps i{{height:4px;flex:1;background:#1c355b;border-radius:2px}}.steps .done{{background:#60d9f4}}
</style><div class="brand"><strong>CARREIRA GUIADA</strong><span class="note">Terminal real com dados fictícios</span></div>
<h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p>
<div class="terminal"><div class="prompt">{html.escape('Você: ' + request)}</div>
<div class="command">{html.escape(operation)}</div>
<div class="viewport"><pre>{body}</pre></div><div class="continuation"></div></div>
<div class="foot">No chat, basta pedir "meu plano" ou "minha evolução". A IA conduz cada passo.</div>
<div class="steps">{segments}</div></html>'''


def main():
    """Render a high-resolution GIF with visible typing and real output frames."""
    frames, durations = [], []
    os.environ['TERM'] = 'xterm-256color'
    os.environ.pop('NO_COLOR', None)
    with tempfile.TemporaryDirectory(prefix='career-personal-demo-') as folder, sync_playwright() as pw:
        root = Path(folder).resolve()
        data = scenes(root)
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={'width': 1120, 'height': 700}, device_scale_factor=2)
            context.route('**/*', lambda route: route.abort())
            tab = context.new_page()
            requests = ['meu plano', 'já ensaiei minha apresentação', 'parar meu plano', 'minha evolução']
            for index, (title, subtitle, command, value) in enumerate(data):
                value['welcome_back'] = None
                ansi = render(value, value['message'], width=76, stream=Terminal())
                text = fragment(ansi)
                request = requests[index]
                for length in [*range(2, len(request), 2), len(request)]:
                    tab.set_content(page(title, subtitle, request[:length] + '▏', '', '', index))
                    tab.evaluate('document.fonts.ready')
                    frames.append(Image.open(io.BytesIO(tab.screenshot())).convert('RGB'))
                    durations.append(100)
                tab.set_content(page(title, subtitle, request, command, text, index))
                tab.evaluate('document.fonts.ready')
                extent = tab.locator('.viewport').evaluate('(el) => ({width:el.clientWidth, contentWidth:el.scrollWidth, height:el.clientHeight, contentHeight:el.scrollHeight})')
                if extent['contentWidth'] > extent['width']:
                    raise ValueError('Terminal output exceeds the viewport width.')
                scroll = max(0, extent['contentHeight'] - extent['height'])
                if scroll:
                    tab.locator('.continuation').evaluate('(el) => el.textContent = "Início da saída desta consulta."')
                image = Image.open(io.BytesIO(tab.screenshot())).convert('RGB')
                frames.append(image)
                durations.append(7000 if index == 3 else 6000)
                if index == 0:
                    image.save(OUT / 'plano-evolucao-terminal.png', optimize=True)
                if scroll:
                    for step in range(1, 13):
                        tab.locator('.viewport').evaluate('(el, y) => el.scrollTop = y', round(scroll * step / 12))
                        frames.append(Image.open(io.BytesIO(tab.screenshot())).convert('RGB'))
                        durations.append(80)
                    tab.locator('.continuation').evaluate('(el) => el.textContent = "Fim da saída desta consulta."')
                    frames.append(Image.open(io.BytesIO(tab.screenshot())).convert('RGB'))
                    durations.append(7000 if index == 3 else 6000)
        finally:
            browser.close()
    # Share colors across scenes so only changed areas need to be stored.
    completed = [frame for frame, duration in zip(frames, durations) if duration >= 5000]
    width, height = frames[0].size
    samples = Image.new('RGB', (width * 4, height * ((len(completed) + 3) // 4)))
    for index, frame in enumerate(completed):
        samples.paste(frame, ((index % 4) * width, (index // 4) * height))
    palette = white_palette(samples)
    for index, frame in enumerate(frames):
        frames[index] = frame.quantize(palette=palette, dither=Image.Dither.NONE)
    frames[0].save(OUT / 'plano-evolucao-terminal.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    print(f'{len(frames)} frames; {sum(durations)} ms; 2240 x 1400 pixels; fictional records only.')


if __name__ == '__main__':
    main()
