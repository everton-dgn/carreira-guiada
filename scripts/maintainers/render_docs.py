"""Render fictional CLI conversations directly at 2240 x 1400 pixels."""

from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/assets"
SCALE = 2
SIZE = (1120 * SCALE, 700 * SCALE)
PAPER, INK, MUTED = "#f1f6ff", "#102951", "#546d8f"
TERMINAL, TEXT, ACCENT, DIM = "#07152e", "#f3f7ff", "#60d9f4", "#a4bcdf"
BLUE, LINE, PALE = "#2864ed", "#c4d7f5", "#e4eeff"


@lru_cache
def font(size, mono=False, bold=False):
    """Load a cached font at the scaled size, trying platform-specific paths.

    Monospaced text takes precedence over bold. Raise RuntimeError when none
    of the supported fonts can be loaded.
    """
    candidates = (
        ("DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consola.ttf") if mono else
        ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf") if bold else
        ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf")
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size * SCALE)
        except OSError:
            continue
    raise RuntimeError("Use DejaVu Sans/Mono ou Arial/Menlo/Consolas para renderizar os exemplos.")


def coords(values):
    """Convert logical coordinates to integer pixels at the rendering scale."""
    return tuple(int(value * SCALE) for value in values)


def text(draw, position, value, size=20, fill=TEXT, mono=False, bold=False):
    """Draw flat text in logical coordinates, rejecting canvas overflow."""
    face = font(size, mono, bold)
    bounds = draw.textbbox(coords(position), value, font=face)
    if bounds[0] < 0 or bounds[1] < 0 or bounds[2] > SIZE[0] or bounds[3] > SIZE[1]:
        raise ValueError(f"Texto fora da imagem: {value!r}")
    draw.text(coords(position), value, font=face, fill=fill)


def wrap(draw, value, width=942, size=21, mono=True):
    """Wrap words to a logical width using the selected font's measured size.

    Individual words are never split; an empty value produces one empty line.
    """
    lines, line = [], ""
    for word in value.split():
        trial = (line + " " + word).strip()
        if line and draw.textlength(trial, font=font(size, mono)) > width * SCALE:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    return lines


def backdrop(dark=False):
    """Flat typography and a quiet background keep the demonstration readable."""
    image = Image.new("RGB", SIZE, TERMINAL if dark else PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle(coords((40, 32, 44, 49)), fill=ACCENT if dark else BLUE)
    text(draw, (55, 29), "CARREIRA GUIADA", 16, TEXT if dark else INK, bold=True)
    text(draw, (865, 30), "SIMULAÇÃO FICTÍCIA", 15, DIM if dark else MUTED)
    draw.line(coords((40, 62, 1080, 62)), fill="#28426a" if dark else LINE, width=SCALE)
    return image, draw


def progress_track(draw, number, progress=1, dark=False):
    """Draw five steps with a zero-based current step and progress from 0 to 1."""
    for index in range(5):
        x = 40 + index * 210
        draw.rounded_rectangle(coords((x, 685, x + 194, 689)), 2 * SCALE,
                               fill="#1c355b" if dark else LINE)
        amount = 1 if index < number else progress if index == number else 0
        if amount:
            draw.rounded_rectangle(coords((x, 685, x + 194 * amount, 689)), 2 * SCALE,
                                   fill=ACCENT if dark else BLUE)


def frame(tool, command, title, number, conversation, note, cursor=False):
    """Return one RGB terminal scene for a one-based step from 1 through 5.

    Conversation entries pair text with a color. Reject text that exceeds the
    terminal area and optionally draw a caret after the last visible line.
    """
    image, draw = backdrop(dark=True)
    text(draw, (40, 80), title, 40, TEXT, bold=True)
    subtitle = ("Vá direto ao que precisa. A IA guia o próximo passo." if command == "claude"
                else "Fontes aprovadas, formulários preenchidos e progresso salvo.")
    text(draw, (40, 136), subtitle, 23, DIM)
    labels = (["Escolher atividade", "Criar currículo", "Mais opções", "Trocar de atividade", "Voltar no outro dia"]
              if command == "claude" else
              ["Buscar vagas", "Ação da pessoa", "Conferir o envio", "Acompanhar", "Parar e retomar"])
    text(draw, (40, 205), f"0{number}", 64, ACCENT, bold=True)
    for index, label in enumerate(labels):
        y = 310 + index * 48
        color = ACCENT if index + 1 == number else DIM
        draw.ellipse(coords((42, y + 6, 50, y + 14)), fill=color if index < number else "#28426a")
        text(draw, (64, y), label, 18, color, bold=index + 1 == number)
    draw.rounded_rectangle(coords((300, 192, 1076, 606)), 16 * SCALE,
                           fill="#0d2242", outline="#34557c", width=SCALE)
    text(draw, (324, 212), ">_ " + tool, 19, ACCENT, True)
    text(draw, (876, 215), "exemplo de terminal", 14, DIM)
    draw.line(coords((324, 255, 1052, 255)), fill="#28426a", width=SCALE)
    y, last = 277, ""
    for value, color in conversation:
        for line in wrap(draw, value, width=714, size=23):
            if y + 28 > 590:
                raise ValueError("O texto não cabe no terminal; reduza esta cena.")
            text(draw, (324, y), line, 23, color, True)
            y += 31
            last = line
    if cursor:
        cursor_x = min(1045, 324 + draw.textlength(last, font=font(23, True)) / SCALE + 3)
        draw.rectangle(coords((cursor_x, y - 26, cursor_x + 2, y - 2)), fill=ACCENT)
    for index, line in enumerate(wrap(draw, note, 1030, 20, mono=False)):
        text(draw, (40, 632 + index * 25), line, 20, TEXT)
    progress_track(draw, number - 1, dark=True)
    return image


def render(name, tool, command, title, scenes, poster=0):
    """Write a PNG poster and a looping GIF from five conversation scenes.

    Each scene pairs colored conversation entries with a footer note. The
    zero-based poster selects a completed scene; the GIF adds typing frames,
    cursor blinks and reading pauses using a shared 128-color palette.
    """
    frame(tool, command, title, poster + 1, *scenes[poster]).save(OUT / (name + ".png"))
    palette = frame(tool, command, title, 1, *scenes[0]).quantize(colors=128)
    frames, durations = [], []

    def append(number, conversation, note, duration, cursor=False):
        """Buffer a palette-matched frame and its duration in milliseconds."""
        current = frame(tool, command, title, number, conversation, note, cursor)
        frames.append(current.quantize(palette=palette, dither=Image.Dither.NONE))
        durations.append(duration)

    for number, (conversation, note) in enumerate(scenes, 1):
        visible = []
        for value, color in conversation:
            if not value:
                visible.append((value, color))
                continue
            user_input = value.startswith("> ")
            prefix = 2 if user_input else 0
            step, delay = (2, 90) if user_input else (6, 60)
            partial = visible + [(value[:prefix], color)]
            append(number, partial, note, 240, cursor=True)
            for length in range(prefix + step, len(value), step):
                partial = visible + [(value[:length], color)]
                append(number, partial, note, delay, cursor=True)
            visible.append((value, color))
            append(number, visible, note, 180, cursor=True)
        # Keep the completed scene readable while the cursor shows that it is animated.
        for _ in range(4):
            append(number, visible, note, 450)
            append(number, visible, note, 450, cursor=True)
        append(number, visible, note, 2000)

    frames[0].save(OUT / (name + ".gif"), save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    print(f"{name}: {len(frames)} quadros, {sum(durations) / 1000:.1f} segundos")


def main():
    """Generate the fictional menu and job-search examples in the assets folder."""
    OUT.mkdir(parents=True, exist_ok=True)
    render("menu-com-contexto", "Claude Code", "claude", "Seu próximo passo, sem adivinhar.", [
        ([("> iniciar", ACCENT), ("IA: O que você quer fazer?", TEXT),
          ("1. Currículo", TEXT), ("2. Entrevistas", TEXT),
          ("3. Guia de carreira", TEXT), ("4. Busca de vagas", TEXT),
          ("5. Mais opções", TEXT), ("> Quero criar meu currículo.", ACCENT)],
         "Escolha pelo número ou pelo nome. A IA pede só o necessário para essa atividade."),
        ([("IA: O que você estudou?", TEXT),
          ("> Fiz um curso de atendimento ao público.", ACCENT), ("", DIM),
          ("IA: Salvei. Conte sobre um trabalho ou projeto.", TEXT),
          ("> Organizei pedidos em um projeto voluntário.", ACCENT)],
         "Uma pergunta por vez. Seu currículo pode começar sem configurar candidaturas."),
        ([("> Mais opções", ACCENT), ("IA: Também posso ajudar com:", TEXT),
          ("LinkedIn e GitHub", TEXT), ("Análise de empresas", TEXT),
          ("Comparação de propostas", TEXT), ("Escolha de modelos", TEXT),
          ("Preparo completo para candidaturas", TEXT)],
         "Abra o menu quando precisar. Você escolhe qual atividade quer iniciar."),
        ([("> Parar as candidaturas. Quero treinar.", ACCENT),
          ("IA: A campanha está parada. Vamos ao treino.", TEXT),
          ("Conte um desafio de trabalho ou estudo.", TEXT),
          ("> Organizei os pedidos do projeto.", ACCENT),
          ("IA: Resposta salva. Falta o feedback.", TEXT)],
         "Troque de atividade sem perder o currículo ou retomar candidaturas paradas."),
        ([("> Continuar meu treino.", ACCENT),
          ("IA: Atividade atual: entrevistas.", TEXT),
          ("Sua resposta sobre o projeto está salva.", TEXT),
          ("Vamos revisar o que você contou.", TEXT),
          ("A campanha de candidaturas continua parada.", DIM),
          ("> Depois quero voltar ao currículo.", ACCENT)],
         "No outro dia, nomeie a atividade. Perguntas e respostas continuam no ponto salvo."),
    ])
    render("busca-com-progresso", "Codex CLI", "codex", "Saiba o que acontece em cada etapa.", [
        ([("> Pode buscar e enviar nesta rodada,", ACCENT),
          ("dentro dos filtros que aprovei.", ACCENT), ("", DIM),
          ("IA: Permissão salva para esta rodada.", TEXT),
          ("Vou consultar as fontes escolhidas.", TEXT),
          ("Perfil, currículo e ferramentas conferidos.", DIM)],
         "Você escolhe: autorizar a rodada ou confirmar cada envio."),
        ([("> O que precisa de mim?", ACCENT),
          ("IA: Entre na conta do Portal Fictício.", TEXT),
          ("A aba está preservada. Não envie sua senha.", TEXT),
          ("Outra vaga autorizada pode seguir.", TEXT),
          ("> Pronto, entrei.", ACCENT),
          ("IA: Vou conferir a sessão antes de preencher.", TEXT)],
         "Ação concreta, lugar certo. Uma pendência não paralisa as demais vagas autorizadas."),
        ([("IA: Formulário preenchido e conferido.", TEXT),
          ("Currículo e destino verificados.", TEXT), ("", DIM),
          ("A vaga está dentro da sua permissão.", TEXT),
          ("Vou enviar e conferir a confirmação.", TEXT)],
         "A autorização da rodada evita repetir a mesma pergunta a cada vaga."),
        ([("IA: O portal fictício confirmou o recebimento.", TEXT),
          ("A candidatura ficou registrada.", TEXT),
          ("", DIM), ("> Acompanhe os retornos que autorizei.", ACCENT),
          ("IA: Falta sua resposta na Empresa Exemplo.", TEXT),
          ("Prazo: 9 de novembro, 18h (Brasília).", TEXT)],
         "Uma candidatura só é contada quando há confirmação do destino."),
        ([("> Parar por agora.", ACCENT),
          ("IA: Ações interrompidas. Progresso salvo.", TEXT),
          ("", DIM), ("> Continuar as candidaturas.", ACCENT),
          ("IA: Vou conferir os resultados pendentes.", TEXT),
          ("Envio incerto não será repetido.", TEXT)],
         "Peça andamento, ações que dependem de você ou detalhes, a qualquer momento."),
    ], poster=2)


if __name__ == "__main__":
    main()
