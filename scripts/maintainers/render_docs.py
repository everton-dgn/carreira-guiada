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
    return tuple(int(value * SCALE) for value in values)


def text(draw, position, value, size=20, fill=TEXT, mono=False, bold=False):
    draw.text(coords(position), value, font=font(size, mono, bold), fill=fill)


def wrap(draw, value, width=942, size=21, mono=True):
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
    """A restrained orbital motif shared by all five native animations."""
    image = Image.new("RGB", SIZE, TERMINAL if dark else PAPER)
    draw = ImageDraw.Draw(image)
    for offset in range(0, 280, 32):
        draw.arc(coords((740 - offset, 350 - offset, 1390 + offset, 1000 + offset)),
                 185, 350, fill="#102d59" if dark else "#dce8fc", width=SCALE)
    draw.rectangle(coords((40, 32, 44, 49)), fill=ACCENT if dark else BLUE)
    text(draw, (55, 29), "CARREIRA GUIADA", 16, TEXT if dark else INK, bold=True)
    text(draw, (904, 30), "SIMULAÇÃO", 15, DIM if dark else MUTED)
    return image, draw


def progress_track(draw, number, progress=1, dark=False):
    for index in range(5):
        x = 40 + index * 210
        draw.rounded_rectangle(coords((x, 685, x + 194, 689)), 2 * SCALE,
                               fill="#1c355b" if dark else LINE)
        amount = 1 if index < number else progress if index == number else 0
        if amount:
            draw.rounded_rectangle(coords((x, 685, x + 194 * amount, 689)), 2 * SCALE,
                                   fill=ACCENT if dark else BLUE)


def frame(tool, command, title, number, conversation, note, cursor=False):
    image, draw = backdrop()
    text(draw, (40, 80), title, 36, INK, bold=True)
    text(draw, (40, 133), "Você conversa. A IA organiza os próximos passos.", 21, MUTED)
    labels = (["Começar", "Contar sua história", "Escolher fontes", "Definir permissões", "Aprovar o preparo"]
              if command == "claude" else
              ["Buscar vagas", "Preencher dados", "Conferir o envio", "Acompanhar", "Parar e retomar"])
    text(draw, (40, 205), f"0{number}", 64, BLUE, bold=True)
    for index, label in enumerate(labels):
        y = 310 + index * 48
        color = BLUE if index + 1 == number else MUTED
        draw.ellipse(coords((42, y + 6, 50, y + 14)), fill=color if index < number else LINE)
        text(draw, (64, y), label, 17, color, bold=index + 1 == number)
    draw.rounded_rectangle(coords((309, 202, 1085, 616)), 16 * SCALE, fill="#cedcf3")
    draw.rounded_rectangle(coords((300, 192, 1076, 606)), 16 * SCALE, fill=TERMINAL)
    text(draw, (324, 212), ">_ " + tool, 19, ACCENT, True)
    text(draw, (876, 215), "exemplo de terminal", 14, DIM)
    draw.line(coords((324, 255, 1052, 255)), fill="#28426a", width=SCALE)
    y, last = 277, ""
    for value, color in conversation:
        for line in wrap(draw, value, width=714, size=20):
            if y + 25 > 590:
                raise ValueError("O texto não cabe no terminal; reduza esta cena.")
            text(draw, (324, y), line, 20, color, True)
            y += 28
            last = line
    if cursor:
        cursor_x = min(1045, 324 + draw.textlength(last, font=font(20, True)) / SCALE + 3)
        draw.rectangle(coords((cursor_x, y - 23, cursor_x + 2, y - 2)), fill=ACCENT)
    for index, line in enumerate(wrap(draw, note, 1030, 18, mono=False)):
        text(draw, (40, 635 + index * 23), line, 18, INK)
    progress_track(draw, number - 1)
    return image


def render(name, tool, command, title, scenes, poster=0):
    frame(tool, command, title, poster + 1, *scenes[poster]).save(OUT / (name + ".png"))
    palette = frame(tool, command, title, 1, *scenes[0]).quantize(colors=128)
    frames, durations = [], []

    def append(number, conversation, note, duration, cursor=False):
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
        for _ in range(3):
            append(number, visible, note, 450)
            append(number, visible, note, 450, cursor=True)
        append(number, visible, note, 600)

    frames[0].save(OUT / (name + ".gif"), save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    print(f"{name}: {len(frames)} quadros, {sum(durations) / 1000:.1f} segundos")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render("inicio-guiado", "Claude Code", "claude", "Seu ponto de partida: uma conversa.", [
        ([("> iniciar", ACCENT), ("", DIM), ("Claude: Você já tem um currículo?", TEXT),
          ("Se não tiver, podemos criar juntos.", TEXT), ("> Quero criar meu primeiro currículo.", ACCENT)],
         "Depois da instalação e do login, escreva iniciar na conversa."),
        ([("> Quero trabalhar com atendimento.", ACCENT), ("", DIM),
          ("Claude: Vamos organizar o que você já fez.", TEXT),
          ("Pode contar sobre estudos, projetos ou trabalho.", TEXT),
          ("> Fiz um curso de atendimento ao público.", ACCENT)],
         "A IA organiza seus dados e ajuda a revisar o currículo, sem inventar fatos."),
        ([("Claude: Em quais sites você quer buscar vagas?", TEXT),
          ("> https://carreiras.example/vagas", ACCENT), ("", DIM),
          ("Claude: Vou incluir esse link no resumo.", TEXT),
          ("Só pesquisarei nas fontes que você aprovar.", TEXT)],
         "O endereço é fictício. Cada pessoa informa suas próprias fontes."),
        ([("Claude: Posso procurar vagas?", TEXT),
          ("> Pode pesquisar. Pergunte antes de enviar.", ACCENT), ("", DIM),
          ("Claude: Certo. Pesquisa autorizada;", TEXT),
          ("cada envio fica sujeito à sua confirmação.", TEXT)],
         "Pesquisar e enviar o currículo são permissões diferentes."),
        ([("Claude: Confira o resumo do perfil e o currículo.", TEXT),
          ("> Conferi. Aprovo esta versão.", ACCENT), ("", DIM),
          ("Claude: Preparação salva. Vamos conferir", TEXT),
          ("as ferramentas disponíveis antes da busca.", TEXT)],
         "O preparo é guiado. Sites e e-mail ainda dependem de conexões disponíveis."),
    ])
    render("candidatura-guiada", "Codex CLI", "codex", "Da busca ao envio, com a sua IA.", [
        ([("> Procure vagas nas fontes que aprovei.", ACCENT),
          ("", DIM), ("Codex: Vou usar seus filtros e conferir", TEXT),
          ("as oportunidades antes de preparar candidaturas.", TEXT),
          ("Neste exemplo: perfil e ferramentas já conferidos.", DIM)],
         "Cenário ilustrativo com perfil aprovado e ferramentas conectadas."),
        ([("Codex: A vaga da Empresa Exemplo é compatível.", TEXT),
          ("Vou preencher os campos com seus dados confirmados.", TEXT),
          ("", DIM), ("> Use o currículo que aprovei.", ACCENT),
          ("Codex: Se faltar uma resposta, eu pergunto.", TEXT)],
         "Você não precisa repetir manualmente as mesmas informações em cada formulário."),
        ([("Codex: Formulário preenchido. Confira o resumo:", TEXT),
          ("currículo aprovado, contato e respostas confirmadas.", TEXT),
          ("Posso enviar esta candidatura?", TEXT),
          ("> Conferi. Pode enviar.", ACCENT)],
         "A conferência e a autorização continuam com você."),
        ([("Codex: No cenário fictício, o portal confirmou", TEXT),
          ("o recebimento. A candidatura ficou registrada.", TEXT),
          ("", DIM), ("> Acompanhe os retornos que autorizei.", ACCENT),
          ("Codex: Vou conferir prazos e próximas etapas.", TEXT)],
         "Uma candidatura só é contada quando há confirmação do destino."),
        ([("> Parar por agora.", ACCENT),
          ("Codex: Novas ações interrompidas. Progresso salvo.", TEXT),
          ("", DIM), ("> continuar", ACCENT),
          ("Codex: Vou conferir as pendências antes de retomar.", TEXT)],
         "O trabalho depende de uma sessão ativa. A pasta guarda o progresso."),
    ], poster=2)


if __name__ == "__main__":
    main()
