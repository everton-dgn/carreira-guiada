"""Capture the real terminal renderer with fictional, temporary private records."""
import html
import io
import os
from pathlib import Path
import tempfile

from PIL import Image
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.terminal_theme import TerminalTheme
from rich.text import Text

from scripts.job.personal_views import entry
from scripts.job.planning import PersonalPlan
from scripts.job.practice import Practice
from scripts.job.personal_progress import PersonalProgress
from scripts.job.terminal import render

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/assets'
COLORS = [(7, 21, 46), (255, 124, 124), (121, 211, 175), (245, 209, 125),
          (109, 167, 255), (196, 163, 255), (96, 217, 244), (243, 247, 255)]
THEME = TerminalTheme((7, 21, 46), (243, 247, 255), COLORS, COLORS)


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
    console = Console(record=True, file=io.StringIO(), width=86, force_terminal=True)
    console.print(Text.from_ansi(ansi), end='')
    return console.export_html(inline_styles=True, theme=THEME, code_format='{code}')


def page(title, subtitle, command, body):
    """Keep a marketing heading outside a clearly labelled terminal capture."""
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<style>
*{{box-sizing:border-box}}body{{margin:0;width:1120px;height:700px;background:#07152e;color:#f3f7ff;
font-family:Arial,sans-serif;padding:30px 42px;}}
.brand{{color:#60d9f4;font-size:14px;font-weight:bold;letter-spacing:2px;display:flex;justify-content:space-between}}
.note{{color:#a4bcdf;font-weight:normal;letter-spacing:0}}h1{{font-size:41px;letter-spacing:-1px;margin:22px 0 10px;}}
.subtitle{{font-size:20px;color:#b7cff4;margin:0 0 24px}}
.terminal{{border-top:2px solid #2864ed;padding:18px 20px 0;background:#07152e;}}
.prompt{{color:#60d9f4;font:16px Menlo,"DejaVu Sans Mono",monospace;height:24px;white-space:pre}}
pre{{font:15px/1.32 Menlo,"DejaVu Sans Mono",monospace;margin:8px 0 0;white-space:pre;}}
.foot{{position:absolute;bottom:24px;color:#a4bcdf;font-size:16px;}}
</style><div class="brand"><span>CARREIRA GUIADA</span><span class="note">Terminal real · dados fictícios</span></div>
<h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p>
<div class="terminal"><div class="prompt">{html.escape('$ ' + command)}</div><pre>{body}</pre></div>
<div class="foot">No chat, basta pedir "meu plano" ou "minha evolução". A IA conduz cada passo.</div></html>'''


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
            for index, (title, subtitle, command, value) in enumerate(data):
                value['welcome_back'] = None
                ansi = render(value, value['message'], width=86, stream=Terminal())
                text = fragment(ansi)
                for length in [*range(3, len(command), 3), len(command)]:
                    tab.set_content(page(title, subtitle, command[:length] + '▏', ''))
                    frames.append(Image.open(io.BytesIO(tab.screenshot())).convert('RGB'))
                    durations.append(100)
                tab.set_content(page(title, subtitle, command, text))
                bottom = tab.locator('pre').bounding_box()
                if bottom['y'] + bottom['height'] > 640:
                    raise ValueError('Terminal output overlaps the footer.')
                image = Image.open(io.BytesIO(tab.screenshot())).convert('RGB')
                frames.append(image)
                durations.append(5000)
                if index == 0:
                    image.save(OUT / 'plano-e-evolucao.png', optimize=True)
        finally:
            browser.close()
    frames[0].save(OUT / 'plano-e-evolucao.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=2)
    print(f'{len(frames)} frames; {sum(durations)} ms; 2240 x 1400 pixels; fictional records only.')


if __name__ == '__main__':
    main()
