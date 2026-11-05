"""Render fictional, labeled walkthroughs. Run with: uv run --group docs python scripts/maintainers/render_docs.py."""

from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "assets"
INK = "#163f2d"
MUTED = "#64746a"
PAPER = "#f8f6ed"
LIME = "#d6ee79"
WHITE = "#ffffff"


@lru_cache
def font(size):
    for candidate in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                      "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    raise RuntimeError("Use DejaVu Sans ou Arial para preservar os acentos nas imagens.")


def wrapped(draw, value, x, y, width, size=22, fill=INK):
    lines, line = [], ""
    for word in value.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font(size)) > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font(size))
        y += size + 10
    return y


def frame(title, steps, active, question, answer, note):
    image = Image.new("RGB", (1120, 700), PAPER)
    draw = ImageDraw.Draw(image)
    draw.text((42, 30), "job", font=font(50), fill=INK)
    draw.rounded_rectangle((800, 36, 1076, 72), radius=18, fill=LIME)
    draw.text((819, 43), "EXEMPLO ILUSTRATIVO", font=font(17), fill=INK)
    draw.text((44, 112), title, font=font(34), fill=INK)
    draw.text((44, 161), "Uma conversa. Uma escolha de cada vez.", font=font(20), fill=MUTED)
    for index, step in enumerate(steps):
        y = 239 + index * 72
        selected = index == active
        draw.rounded_rectangle((42, y - 10, 326, y + 49), radius=14, fill=LIME if selected else PAPER)
        draw.ellipse((55, y + 1, 87, y + 33), fill=INK if index <= active else "#d9dfd2")
        draw.text((66, y + 7), str(index + 1), font=font(15), fill=WHITE if index <= active else MUTED)
        draw.text((103, y + 4), step, font=font(20), fill=INK if index <= active else MUTED)
    draw.rounded_rectangle((358, 216, 1076, 598), radius=24, fill=WHITE)
    draw.text((390, 240), "JOB", font=font(16), fill=MUTED)
    wrapped(draw, question, 390, 276, 642, size=23)
    draw.rounded_rectangle((426, 399, 1046, 518), radius=20, fill=LIME)
    draw.text((450, 415), "VOCÊ", font=font(15), fill=INK)
    wrapped(draw, answer, 450, 448, 567, size=21)
    wrapped(draw, note, 390, 544, 638, size=17, fill=MUTED)
    draw.text((44, 643), "Dados fictícios. O visual do seu aplicativo de IA pode ser diferente.", font=font(17), fill=MUTED)
    draw.rounded_rectangle((44, 677, 1076, 683), radius=3, fill="#d9dfd2")
    draw.rounded_rectangle((44, 677, int(44 + 1032 * (active + 1) / len(steps)), 683), radius=3, fill=INK)
    return image


def render(name, title, steps, conversations):
    frames = [frame(title, steps, index, *conversation) for index, conversation in enumerate(conversations)]
    frames[-1].save(OUT / (name + ".png"))
    frames[0].save(OUT / (name + ".gif"), save_all=True, append_images=frames[1:],
                   duration=[4400] * len(frames), loop=0, optimize=True, disposal=2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render("inicio-guiado", "Comece com uma palavra: iniciar", ["Seu currículo", "Seu objetivo", "Seus links", "Suas escolhas", "Sua aprovação"], [
        ("Você já tem um currículo? Pode anexar aqui. Se não tiver, montamos juntos.", "Ainda não tenho. Quero criar meu primeiro currículo.", "Você pode responder 'não sei' ou deixar um tópico para depois."),
        ("Que tipo de trabalho você procura? Pode descrever do seu jeito.", "Quero trabalhar com atendimento ao público.", "A IA ajuda a organizar o que você contou, sem inventar experiência."),
        ("Em quais sites você quer procurar vagas? Cole o endereço da página aqui.", "Quero usar https://carreiras.example/vagas", "Este endereço é fictício. Cada pessoa escolhe suas fontes de busca."),
        ("Posso procurar vagas? E para enviar seu currículo, prefere aprovar cada envio?", "Pode pesquisar. Quero conferir antes de enviar.", "Pesquisar e enviar são permissões diferentes."),
        ("Vamos conferir seu perfil e o currículo antes de continuar.", "Está certo. Pode aprovar esta versão.", "Seu progresso fica salvo. Você decide quando começar a busca."),
    ])
    render("candidatura-guiada", "Você acompanha cada decisão", ["Vaga encontrada", "Revisão", "Confirmação", "Pausa", "Retomada"], [
        ("Encontrei uma vaga nas fontes que você escolheu. Vou conferir os requisitos e a empresa.", "Quero ver os detalhes.", "Encontrar uma vaga ainda não significa enviar uma candidatura."),
        ("O formulário está pronto com os dados confirmados. Posso enviar esta candidatura?", "Conferi. Pode enviar.", "Exemplo fictício: nenhuma candidatura é enviada nesta demonstração."),
        ("O portal confirmou o recebimento. Registrei a candidatura.", "Certo. Me avise se houver uma etapa para mim.", "Um resultado em dúvida fica pendente de conferência, sem reenvio."),
        ("Vou preservar o progresso e interromper novas ações.", "Parar por agora.", "Uma janela aberta não mantém a IA trabalhando sozinha."),
        ("Ao retomar, confiro o que ficou pendente antes de continuar.", "Continuar.", "Login, entrevistas e respostas pessoais continuam com você."),
    ])


if __name__ == "__main__":
    main()
