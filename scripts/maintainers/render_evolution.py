"""Render a fictional progress story backed by the real private-record services.

Run: uv run --locked --group docs python -m scripts.maintainers.render_evolution
Only the GIF and its PNG poster are written to docs/assets. Temporary records
are removed on exit. No browser, account, model or network connection is used.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import tempfile

from PIL import Image

from scripts.job.personal_progress import PersonalProgress
from scripts.job.practice import Practice
from scripts.maintainers.render_docs import (
    ACCENT, DIM, OUT, SCALE, TEXT, backdrop, coords, font, progress_track, text, wrap,
)

LABELS = ('Escolher', 'Praticar', 'Usar pontos', 'Conquistar', 'Retomar')
NAME = 'minha-evolucao-demo'


@dataclass(frozen=True)
class Scene:
    """Pair illustrative dialogue with a snapshot of verified product values."""
    title: str
    request: str
    response: str
    note: str
    state: dict


def record_practice(root, service, version, minutes):
    """Save one fictional person's confirmed rehearsal with an exact attempt link."""
    practice = Practice(root)
    if version == 1:
        started = practice.start('presentation', 'coach', short=True)
        source = (started['session_id'], started['question']['id'])
    else:
        event = service.get()['events'][0]['source']
        source = (event['session_id'], event['question_id'])
    answer = ('Atendi clientes e organizei pedidos em uma empresa fictícia.' if version == 1
              else 'Organizei os pedidos por prazo e conferi cada entrega com a equipe.')
    practice.answer(*source, answer, attempt_id=f'fictional-rehearsal-{version}',
                    origin='person', user_confirmation='Eu fiz este ensaio fictício.')
    service.record({'expected_version': service.get()['version'],
        'event_id': f'rehearsal-{version}', 'activity': 'practice',
        'source': {'kind': 'practice', 'session_id': source[0],
                   'question_id': source[1], 'version': version},
        'user_confirmation': 'Ensaiei a resposta. Pode registrar.',
        'reported_minutes': minutes, 'occurred_at': f'2026-11-09T12:{version}0:00-03:00'})


def scenes(root):
    """Exercise opt-in, two practices, points, evidence and a read-only return."""
    service = PersonalProgress(root)
    assert service.status()['mode'] == 'off'
    service.configure({'expected_version': 0, 'mode': 'tracking'})
    result = [Scene('Você escolhe como acompanhar.', 'quero guardar minhas práticas',
        'Combinado. Os pontos ficam desligados.\nDepois de um ensaio, conte o que praticou.',
        'O acompanhamento é opcional. Comece do jeito que fizer sentido para você.', service.status())]
    record_practice(root, service, 1, 5)
    result.append(Scene('Uma prática já é um começo.', 'ensaiei minha apresentação por 5 minutos',
        'Ensaio confirmado e salvo.\nVocê já tem uma prática para revisitar.',
        'Registre o que você praticou e o tempo que quiser informar.', service.status()))
    service.configure({'expected_version': service.get()['version'], 'mode': 'points'})
    state = service.status()
    assert state['points'] == 10 and state['practice_count'] == 1
    result.append(Scene('Pontos? Só se você quiser.', 'quero usar pontos também',
        f"Ativados: {state['points']} pontos pelo treino.\nCada tentativa confirmada vale 10 pontos.",
        'O tempo informado não muda os pontos. Consultar de novo não soma.', state))
    record_practice(root, service, 2, 7)
    service.milestone({'expected_version': service.get()['version'],
        'milestone_id': 'first-rehearsals', 'kind': 'participation',
        'title': 'Primeiros ensaios', 'criterion': 'Duas tentativas confirmadas.',
        'event_ids': ['rehearsal-1', 'rehearsal-2'],
        'assessment': 'Dois ensaios registrados com a confirmação da pessoa fictícia.'})
    state = service.status()
    assert state['points'] == 20 and state['reported_minutes'] == 12
    assert len(state['milestones']) == 1 and not state['evidence_warnings']
    result.append(Scene('Uma conquista com história.', 'ensaiei mais 7 minutos. pode registrar',
        'Segundo ensaio confirmado e salvo.\nConquista: ' + state['milestones'][0]['title']
        + '\nCritério: duas tentativas confirmadas.',
        'A conquista mostra o que você fez. Você pode conferir ou contestar.', state))
    before = service.get()
    resumed = PersonalProgress(root).status()
    assert resumed == state and PersonalProgress(root).get() == before
    result.append(Scene('Pode pausar. O progresso fica.', 'voltei. mostra minha evolução',
        f"Seus {resumed['practice_count']} ensaios continuam salvos.\n{resumed['points']} pontos, sem desconto pela pausa.\nQuer praticar ou conferir sua conquista?",
        'No dia seguinte, basta pedir "minha evolução". Retome no seu ritmo.', resumed))
    return result


def mix(color, amount, background='#0d2242'):
    """Blend a foreground with its fixed background for subtle reveal frames."""
    a, b = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (background, color))
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def lines(draw, value, x, y, color, size=23, width=714, cursor=False):
    """Draw wrapped terminal text and return its bottom, rejecting overlap."""
    for paragraph in value.split('\n'):
        for line in wrap(draw, paragraph, width, size):
            if y + 29 > 470:
                raise ValueError('Dialogue overlaps the saved-record receipt.')
            text(draw, (x, y), line, size, color, mono=True)
            y += 32
    if cursor:
        right = x + draw.textlength(line, font=font(size, True)) / SCALE + 3
        draw.rectangle(coords((right, y - 27, right + 2, y - 4)), fill=ACCENT)
    return y


def receipt(draw, state, amount, milestone):
    """Reveal confirmed values together; never animate through invented scores."""
    y = 495 + round(8 * (1 - amount))
    draw.line(coords((324, 480, 1052, 480)), fill=mix('#34557c', amount), width=SCALE)
    count, minutes = state['practice_count'], state['reported_minutes']
    points = 'desligados' if state['points'] is None else str(state['points'])
    for x, value, label in [(324, str(count), 'treino' if count == 1 else 'treinos'),
                            (544, f'{minutes} min', 'informados'),
                            (800, points, 'pontos opcionais')]:
        text(draw, (x, y), value, 28, mix(ACCENT, amount), bold=True)
        text(draw, (x, y + 37), label, 17, mix(DIM, amount))
    if milestone:
        draw.rounded_rectangle(coords((313, 567, 1062, 606)), 7 * SCALE,
                               outline=mix('#746f60', amount), width=SCALE)
        text(draw, (324, 576), '✓ Primeiros ensaios · conquista de participação', 18,
             mix('#f5ead4', amount), mono=True)


def frame(scene, index, request, response='', reveal=0, cursor=False):
    """Compose the existing dark demonstration family without changing banners."""
    image, draw = backdrop(dark=True)
    text(draw, (40, 80), 'Minha evolução, no seu ritmo.', 40, TEXT, bold=True)
    text(draw, (40, 136), scene.title, 23, DIM)
    text(draw, (40, 205), f'0{index + 1}', 64, ACCENT, bold=True)
    for number, label in enumerate(LABELS):
        y = 310 + number * 48
        color = ACCENT if number == index else DIM
        if number < 4:
            draw.line(coords((46, y + 14, 46, y + 54)), fill='#28426a', width=SCALE)
        draw.ellipse(coords((41, y + 5, 51, y + 15)), fill=ACCENT if number <= index else '#28426a')
        text(draw, (65, y), label, 18, color, bold=number == index)
    draw.rounded_rectangle(coords((300, 192, 1076, 616)), 16 * SCALE,
                           fill='#0d2242', outline='#34557c', width=SCALE)
    text(draw, (324, 212), '>_ Conversa no terminal', 19, ACCENT, mono=True)
    text(draw, (901, 216), 'DEMONSTRAÇÃO', 14, DIM)
    draw.line(coords((324, 255, 1052, 255)), fill='#28426a', width=SCALE)
    y = lines(draw, '> ' + request, 324, 277, ACCENT, cursor=cursor and not response)
    if response:
        lines(draw, 'IA: ' + response, 324, y + 16, TEXT, cursor=cursor)
    if reveal:
        receipt(draw, scene.state, reveal, bool(scene.state['milestones']))
    text(draw, (40, 641), scene.note, 20, TEXT)
    progress_track(draw, index, progress=1 if reveal else .3, dark=True)
    return image


def timeline(data):
    """Yield deliberate typing, short settling motions and long reading pauses."""
    for index, scene in enumerate(data):
        yield frame(scene, index, ''), 280
        for length in range(3, len(scene.request), 3):
            yield frame(scene, index, scene.request[:length], cursor=True), 80
        yield frame(scene, index, scene.request, cursor=True), 320
        for length in range(5, len(scene.response), 5):
            yield frame(scene, index, scene.request, scene.response[:length], cursor=True), 60
        for step in range(1, 9):
            ease = 1 - (1 - step / 8) ** 3
            yield frame(scene, index, scene.request, scene.response, ease), 70
        yield frame(scene, index, scene.request, scene.response, 1, cursor=True), 260
        yield frame(scene, index, scene.request, scene.response, 1), 7000 if index >= 3 else 6000


def main():
    """Generate a bounded, high-resolution animation with a shared color palette."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Write five scene PNGs; requires --output outside docs/assets.')
    parser.add_argument('--output', type=Path, help='Output directory; defaults to docs/assets except in preview mode.')
    args = parser.parse_args()
    if args.preview and (args.output is None or args.output.resolve().is_relative_to(OUT.resolve())):
        parser.error('--preview requires --output outside docs/assets.')
    args.output = args.output or OUT
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='career-evolution-demo-') as folder:
        data = scenes(Path(folder).resolve())
    completed = [frame(s, i, s.request, s.response, 1) for i, s in enumerate(data)]
    if args.preview:
        for i, image in enumerate(completed):
            image.save(args.output / f'{NAME}-{i + 1}.png')
        print('Five completed scenes rendered; fictional records cleaned up.')
        return
    # Full-size pixels retain the exact navy and cream; resized samples mix them.
    palette = completed[3].quantize(colors=128)
    frames, durations = [], []
    for image, duration in timeline(data):
        frames.append(image.quantize(palette=palette, dither=Image.Dither.NONE))
        durations.append(duration)
        if duration >= 5000:
            print(f'Scene {sum(d >= 5000 for d in durations)}/5 rendered.', flush=True)
    completed[3].save(args.output / f'{NAME}.png', optimize=True)
    frames[0].save(args.output / f'{NAME}.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    with Image.open(args.output / f'{NAME}.gif') as saved:
        print(f'{saved.n_frames} encoded frames; {sum(durations)} ms; 2240 x 1400 px; fictional records only.')


if __name__ == '__main__':
    main()
