"""Render fictional resume and browser walkthroughs without network access."""

from PIL import Image, ImageDraw

from render_docs import OUT, SIZE, SCALE, PAPER, INK, MUTED, TERMINAL, TEXT, GREEN
from render_docs import coords, font, text, wrap


def box(draw, bounds, fill, outline=None, radius=12):
    draw.rounded_rectangle(coords(bounds), radius=radius * SCALE,
                           fill=fill, outline=outline, width=2 * SCALE)


def paragraph(draw, position, value, width, size=19, fill=TEXT):
    x, y = position
    for part in value.split('\n'):
        for line in wrap(draw, part, width=width, size=size):
            text(draw, (x, y), line, size, fill, True)
            y += size + 8
    return y


def pointer(draw, position, clicking=False):
    x, y = position
    if clicking:
        draw.ellipse(coords((x - 14, y - 14, x + 14, y + 14)),
                     outline="#79a53b", width=3 * SCALE)
    draw.polygon(coords((x, y, x + 5, y + 23, x + 11, y + 15,
                         x + 22, y + 14)), fill=INK, outline="#ffffff", width=2 * SCALE)


def base(title, number, message, progress, note):
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    text(draw, (36, 22), "Carreira Guiada", 30, INK)
    text(draw, (785, 32), "DEMONSTRAÇÃO FICTÍCIA", 16, MUTED)
    text(draw, (36, 75), title, 27, INK)
    text(draw, (36, 117), "Qualquer modelo com as ferramentas necessárias. Nenhuma ação real.", 18, MUTED)
    box(draw, (36, 160, 434, 596), TERMINAL)
    text(draw, (56, 180), "Conversa com sua IA", 19, GREEN)
    text(draw, (56, 212), "Terminal ilustrativo", 15, "#afc2b4", True)
    draw.line(coords((56, 244, 414, 244)), fill="#42594b", width=SCALE)
    visible = message[:max(1, int(len(message) * min(1, progress * 2)))]
    paragraph(draw, (56, 265), visible, 350, 20)
    text(draw, (56, 553), f"ETAPA {number + 1} / 5", 16, GREEN, True)
    text(draw, (36, 618), note, 19, INK)
    text(draw, (36, 652), "Ilustração do fluxo. O Carreira Guiada não tem interface gráfica própria.", 17, MUTED)
    box(draw, (36, 686, 1084, 692), "#d9dfd2", radius=3)
    box(draw, (36, 686, 36 + 1048 * (number + progress) / 5, 692), INK, radius=3)
    return image, draw


RESUME_SCENES = [
    ("Você: Atendia clientes e organizava pedidos. Empresa Exemplo, de 2023 a 2025.\n\nIA: Vou usar esses fatos que você confirmou.",
     "A IA começa pelo que você contou. Não inventa experiência ou resultados."),
    ("IA: Vou separar contato, resumo, experiência e formação.\n\nVocê: Pode organizar o texto.",
     "Seções claras ajudam a ler o currículo e conferir o que ainda falta."),
    ("IA: Sugestão: atendimento a clientes e organização de pedidos.\n\nVocê: Está correto. Fiz também um curso de atendimento.",
     "A redação melhora sem acrescentar habilidades ou números não confirmados."),
    ("IA: Confira os fatos e as datas desta versão.\n\nVocê: Conferi. Aprovo o currículo.",
     "A pessoa aprova o conteúdo antes da geração dos arquivos para envio."),
    ("IA: Versão aprovada gerada em PDF, Word e texto.\n\nVou conferir esta versão antes de anexar a uma candidatura.",
     "O original é preservado. Cada versão tem sua própria aprovação."),
]


def resume_frame(stage, progress, blink=False):
    image, draw = base("Do que você conta a um currículo pronto para enviar", stage,
                       RESUME_SCENES[stage][0], progress, RESUME_SCENES[stage][1])
    box(draw, (456, 160, 1084, 596), "#e4e9dd")
    text(draw, (478, 178), "PRÉVIA ILUSTRATIVA DO DOCUMENTO", 15, MUTED)
    box(draw, (482, 213, 1058, 575), "#ffffff", radius=3)
    if stage == 0:
        text(draw, (506, 236), "Fatos confirmados", 27, INK)
        raw = "Pessoa Exemplo\npessoa@example.invalid\nEmpresa Exemplo | 2023 a 2025\nAtendia clientes e organizava pedidos."
        shown = raw[:int(len(raw) * progress)]
        y = 292
        for line in shown.split("\n"):
            y = paragraph(draw, (506, y), line, 516, 18, INK) + 12
        if blink:
            x = 506 + draw.textlength(shown.split('\n')[-1], font=font(18, True)) / SCALE
            text(draw, (x, min(y - 38, 535)), "|", 18, INK, True)
    else:
        text(draw, (506, 232), "Pessoa Exemplo", 28, INK)
        text(draw, (506, 272), "pessoa@example.invalid", 17, MUTED)
        headings = [("RESUMO", 318), ("EXPERIÊNCIA", 383), ("FORMAÇÃO", 470)]
        for index, (label, y) in enumerate(headings):
            if stage > 1 or progress >= index / 3:
                text(draw, (506, y), label, 14, MUTED)
                draw.line(coords((506, y + 24, 1030, y + 24)), fill="#d9dfd2", width=SCALE)
        if stage >= 2:
            summary = "Atendimento a clientes e organização de pedidos."
            summary = summary[:int(len(summary) * progress)] if stage == 2 else summary
            paragraph(draw, (506, 346), summary, 520, 16, INK)
            text(draw, (506, 411), "Empresa Exemplo | 2023 a 2025", 18, INK)
            text(draw, (506, 438), "Atendimento e organização de pedidos", 17, INK)
            if stage > 2 or progress > 0.65:
                text(draw, (506, 502), "Curso de atendimento ao público", 18, INK)
            if stage == 2 and blink:
                x = 506 + draw.textlength(summary, font=font(16, True)) / SCALE
                text(draw, (x, 346), "|", 16, INK, True)
        if stage == 3:
            box(draw, (875, 229, 1038, 265), "#eef4df")
            text(draw, (892, 237), "EM REVISÃO", 15, INK)
        if stage == 4:
            box(draw, (884, 229, 1038, 265), GREEN)
            text(draw, (903, 237), "APROVADO", 15, INK)
            for index, label in enumerate(("PDF", "WORD", "TEXTO")):
                if progress >= index / 3:
                    box(draw, (506 + index * 170, 538, 662 + index * 170, 565), "#e4edce")
                    text(draw, (549 + index * 170, 543), label, 13, INK)
    return image


PORTAL_SCENES = [
    ("IA: Encontrei uma vaga nas fontes aprovadas. Vou conferir a empresa e seus filtros antes de preencher.",
     "Perfil e currículo aprovados. Navegador conectado e pesquisa autorizada."),
    ("IA: Preenchimento autorizado. Vou digitar os contatos que você confirmou e reler os campos.",
     "Nome e contato são reaproveitados. Você não precisa digitá-los a cada vaga."),
    ("IA: Vou usar sua apresentação confirmada e anexar a versão aprovada do currículo.",
     "O anexo é conferido antes do envio. A apresentação usa apenas fatos confirmados."),
    ("IA: Campos e currículo conferidos. Posso enviar?\n\nVocê: Pode enviar esta candidatura.",
     "Neste exemplo, a pessoa escolheu perguntar antes de cada envio."),
    ("IA: O portal confirmou o recebimento nesta simulação. Vou registrar o resultado e seguir para a próxima vaga.",
     "Só a confirmação conta como envio. Resultado incerto exige conferência."),
]


def field(draw, y, label, value, active=False, blink=False):
    text(draw, (482, y), label, 16, MUTED)
    box(draw, (482, y + 25, 1058, y + 65), "#ffffff", INK if active else "#ccd6c7", radius=6)
    text(draw, (494, y + 33), value, 18, INK)
    if active and blink:
        x = 497 + draw.textlength(value, font=font(18)) / SCALE
        draw.line(coords((x, y + 33, x, y + 56)), fill=INK, width=2 * SCALE)


def portal_frame(stage, progress, blink=False):
    image, draw = base("A IA navega e preenche a candidatura para você", stage,
                       PORTAL_SCENES[stage][0], progress, PORTAL_SCENES[stage][1])
    box(draw, (456, 160, 1084, 596), "#ffffff", "#ccd6c7")
    box(draw, (470, 174, 1070, 213), "#edf0e7", radius=7)
    text(draw, (485, 185), "carreiras.example | PORTAL FICTÍCIO", 16, INK, True)
    if stage == 0:
        text(draw, (482, 241), "Empresa Exemplo", 26, INK)
        text(draw, (482, 285), "Atendimento ao cliente", 24, INK)
        text(draw, (482, 325), "Remoto | Requisitos compatíveis com o perfil", 18, MUTED)
        paragraph(draw, (482, 369), "Atender clientes e organizar pedidos. Confira a descrição antes da candidatura.", 550, 18, INK)
        box(draw, (482, 485, 752, 536), INK)
        text(draw, (507, 499), "Abrir candidatura", 21)
        pointer(draw, (992 - 300 * progress, 442 + 70 * progress), blink and progress == 1)
    elif stage == 4:
        box(draw, (484, 251, 1054, 435), "#eff5df")
        text(draw, (510, 283), "Candidatura recebida", 30, INK)
        text(draw, (510, 334), "Confirmação simulada", 20, MUTED)
        text(draw, (510, 373), "Empresa Exemplo | Atendimento", 19, INK)
        text(draw, (484, 472), "Registro local: envio confirmado", 22, INK)
        text(draw, (484, 518), "Próxima ação: continuar pelas outras vagas", 18, MUTED)
    else:
        text(draw, (482, 232), "Candidatura | Atendimento", 22, INK)
        name, email = "Pessoa Exemplo", "pessoa@example.invalid"
        if stage == 1:
            name = name[:int(len(name) * min(1, progress * 2))]
            email = email[:int(len(email) * max(0, progress * 2 - 1))]
        field(draw, 274, "Nome", name, stage == 1 and progress <= 0.5, blink)
        field(draw, 348, "E-mail", email, stage == 1 and progress > 0.5, blink)
        if stage >= 2:
            intro = "Atendia clientes e organizava pedidos."
            if stage == 2:
                intro = intro[:int(len(intro) * min(1, progress * 1.5))]
            field(draw, 422, "Apresentação", intro, stage == 2, blink)
            if stage > 2 or progress > 0.7:
                text(draw, (484, 510), "Anexo: curriculo-exemplo.pdf", 17, INK)
                text(draw, (484, 544), "Versão aprovada conferida", 16, MUTED)
        if stage == 3:
            box(draw, (827, 535, 1058, 580), INK)
            text(draw, (848, 547), "Enviar candidatura", 18)
            pointer(draw, (1030 - 70 * progress, 464 + 91 * progress), blink and progress == 1)
    return image


def render(name, draw_frame, poster):
    draw_frame(poster, 1).save(OUT / (name + ".png"))
    # A single palette keeps text colors steady and allows compact delta frames.
    samples = Image.new("RGB", (SIZE[0] * 5, SIZE[1]))
    for stage in range(5):
        samples.paste(draw_frame(stage, 1), (stage * SIZE[0], 0))
    palette = samples.quantize(colors=128)
    frames, durations = [], []
    for stage in range(5):
        timeline = [(i / 32, 100, True) for i in range(33)]
        timeline += [(1, 450, blink) for _ in range(3) for blink in (False, True)]
        timeline += [(1, 1000, False)]
        for progress, duration, blink in timeline:
            frames.append(draw_frame(stage, progress, blink).quantize(palette=palette, dither=Image.Dither.NONE))
            durations.append(duration)
    frames[0].save(OUT / (name + ".gif"), save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    print(f"{name}: {len(frames)} quadros, {sum(durations) / 1000:.1f} segundos")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    render("curriculo-guiado", resume_frame, 4)
    render("portal-guiado", portal_frame, 3)
