"""Render fictional CLI conversations directly at 2240 x 1400 pixels."""

from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/assets"
SCALE = 2
SIZE = (1120 * SCALE, 700 * SCALE)
PAPER, INK, MUTED = "#f8f6ed", "#163f2d", "#607266"
TERMINAL, TEXT, GREEN, DIM = "#15221d", "#eff5ee", "#d6ee79", "#afc2b4"


@lru_cache
def font(size, mono=False):
    candidates = (
        ("DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consola.ttf") if mono else
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


def text(draw, position, value, size=20, fill=TEXT, mono=False):
    draw.text(coords(position), value, font=font(size, mono), fill=fill)


def wrap(draw, value, width=942, size=21):
    lines, line = [], ""
    for word in value.split():
        trial = (line + " " + word).strip()
        if line and draw.textlength(trial, font=font(size, True)) > width * SCALE:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    return lines


def frame(tool, command, title, number, conversation, note, cursor=False):
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    text(draw, (42, 27), "Carreira Guiada", 32, INK)
    text(draw, (770, 38), "SIMULAÇÃO NO TERMINAL", 17, MUTED)
    text(draw, (44, 86), title, 27, INK)
    text(draw, (44, 130), "Conversas fictícias. A aparência real depende da versão e do tema.", 18, MUTED)
    draw.rounded_rectangle(coords((42, 177, 1078, 583)), radius=18 * SCALE, fill=TERMINAL)
    text(draw, (66, 194), tool + " | terminal ilustrativo", 16, DIM, True)
    text(draw, (970, 194), f"{number}/5", 16, DIM, True)
    draw.line(coords((64, 228, 1054, 228)), fill="#3b5144", width=SCALE)
    y = 244
    lines = [("$ cd carreira-guiada", DIM), ("$ " + command, GREEN), ("", DIM)]
    lines.extend(conversation)
    for value, color in lines:
        for line in wrap(draw, value):
            if y + 26 > 568:
                raise ValueError("O texto não cabe no terminal; reduza esta cena.")
            text(draw, (67, y), line, 21, color, True)
            y += 29
    if cursor:
        cursor_x = 67 + draw.textlength(line, font=font(21, True)) / SCALE + 3
        draw.rectangle(coords((cursor_x, y - 25, cursor_x + 2, y - 3)), fill=GREEN)
    text(draw, (44, 606), note, 19, INK)
    text(draw, (44, 646), "Sem contas reais, sem envios. A IA usa as ferramentas disponíveis na sua sessão.", 17, MUTED)
    draw.rounded_rectangle(coords((44, 680, 1076, 686)), radius=3 * SCALE, fill="#d9dfd2")
    draw.rounded_rectangle(coords((44, 680, 44 + 1032 * number / 5, 686)), radius=3 * SCALE, fill=INK)
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
    render("inicio-guiado", "Claude Code", "claude", "Comece conversando, uma pergunta por vez", [
        ([("> iniciar", GREEN), ("", DIM), ("Claude: Você já tem um currículo?", TEXT),
          ("Se não tiver, podemos criar juntos.", TEXT), ("> Quero criar meu primeiro currículo.", GREEN)],
         "Depois da instalação e do login, escreva iniciar na conversa."),
        ([("> Quero trabalhar com atendimento.", GREEN), ("", DIM),
          ("Claude: Vamos organizar o que você já fez.", TEXT),
          ("Pode contar sobre estudos, projetos ou trabalho.", TEXT),
          ("> Fiz um curso de atendimento ao público.", GREEN)],
         "A IA organiza seus dados e ajuda a revisar o currículo, sem inventar fatos."),
        ([("Claude: Em quais sites você quer buscar vagas?", TEXT),
          ("> https://carreiras.example/vagas", GREEN), ("", DIM),
          ("Claude: Vou incluir esse link no resumo.", TEXT),
          ("Só pesquisarei nas fontes que você aprovar.", TEXT)],
         "O endereço é fictício. Cada pessoa informa suas próprias fontes."),
        ([("Claude: Posso procurar vagas?", TEXT),
          ("> Pode pesquisar. Pergunte antes de enviar.", GREEN), ("", DIM),
          ("Claude: Certo. Pesquisa autorizada;", TEXT),
          ("cada envio fica sujeito à sua confirmação.", TEXT)],
         "Pesquisar e enviar o currículo são permissões diferentes."),
        ([("Claude: Confira o resumo do perfil e o currículo.", TEXT),
          ("> Conferi. Aprovo esta versão.", GREEN), ("", DIM),
          ("Claude: Preparação salva. Vamos conferir", TEXT),
          ("as ferramentas disponíveis antes da busca.", TEXT)],
         "O preparo é guiado. Sites e e-mail ainda dependem de conexões disponíveis."),
    ])
    render("candidatura-guiada", "Codex CLI", "codex", "Automatize a busca e o preenchimento de candidaturas", [
        ([("> Procure vagas nas fontes que aprovei.", GREEN),
          ("", DIM), ("Codex: Vou usar seus filtros e conferir", TEXT),
          ("as oportunidades antes de preparar candidaturas.", TEXT),
          ("Neste exemplo: perfil e ferramentas já conferidos.", DIM)],
         "Cenário ilustrativo com perfil aprovado e ferramentas conectadas."),
        ([("Codex: A vaga da Empresa Exemplo é compatível.", TEXT),
          ("Vou preencher os campos com seus dados confirmados.", TEXT),
          ("", DIM), ("> Use o currículo que aprovei.", GREEN),
          ("Codex: Se faltar uma resposta, eu pergunto.", TEXT)],
         "Você não precisa repetir manualmente as mesmas informações em cada formulário."),
        ([("Codex: Formulário preenchido. Confira o resumo:", TEXT),
          ("currículo aprovado, contato e respostas confirmadas.", TEXT),
          ("Posso enviar esta candidatura?", TEXT),
          ("> Conferi. Pode enviar.", GREEN)],
         "A conferência e a autorização continuam com você."),
        ([("Codex: No cenário fictício, o portal confirmou", TEXT),
          ("o recebimento. A candidatura ficou registrada.", TEXT),
          ("", DIM), ("> Acompanhe os retornos que autorizei.", GREEN),
          ("Codex: Vou conferir prazos e próximas etapas.", TEXT)],
         "Uma candidatura só é contada quando há confirmação do destino."),
        ([("> Parar por agora.", GREEN),
          ("Codex: Novas ações interrompidas. Progresso salvo.", TEXT),
          ("", DIM), ("> continuar", GREEN),
          ("Codex: Vou conferir as pendências antes de retomar.", TEXT)],
         "O trabalho depende de uma sessão ativa. A pasta guarda o progresso."),
    ], poster=2)


if __name__ == "__main__":
    main()
