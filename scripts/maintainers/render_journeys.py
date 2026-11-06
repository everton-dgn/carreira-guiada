"""Render fictional resume and browser walkthroughs without network access."""

from PIL import Image

from render_docs import OUT, SIZE, SCALE, INK, MUTED, TEXT, ACCENT
from render_docs import coords, font, text, wrap, backdrop, progress_track, BLUE, LINE, PALE, DIM


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
                     outline="#60d9f4", width=3 * SCALE)
    draw.polygon(coords((x, y, x + 5, y + 23, x + 11, y + 15,
                         x + 22, y + 14)), fill=INK, outline="#ffffff", width=2 * SCALE)


def base(title, number, message, progress, note):
    image, draw = backdrop(dark=True)
    text(draw, (40, 78), title, 35, TEXT, bold=True)
    text(draw, (40, 132), "Do que você conta ao próximo passo concreto.", 20, DIM)
    text(draw, (40, 206), ">_ conversa com sua IA", 19, ACCENT, True)
    draw.line(coords((40, 244, 407, 244)), fill="#28426a", width=SCALE)
    visible = message[:max(1, int(len(message) * min(1, progress * 2)))]
    end = paragraph(draw, (40, 266), visible, 374, 20)
    if end > 550:
        raise ValueError("A conversa ultrapassou a área de leitura.")
    text(draw, (40, 556), f"0{number + 1}", 32, ACCENT, bold=True)
    text(draw, (96, 568), "DE 05 ETAPAS", 14, DIM)
    for index, line in enumerate(wrap(draw, note, 1030, 18, mono=False)):
        text(draw, (40, 635 + index * 23), line, 18, TEXT)
    progress_track(draw, number, progress, dark=True)
    return image, draw


def paper(draw, label):
    """A document on the stage, not a second application window."""
    text(draw, (480, 177), label, 14, DIM)
    box(draw, (492, 221, 1076, 606), "#14366a", radius=8)
    box(draw, (480, 210, 1064, 594), "#ffffff", radius=8)
    draw.rectangle(coords((480, 226, 486, 280)), fill=BLUE)
    draw.polygon(coords((1026, 210, 1064, 248, 1064, 210)), fill="#a9c8fb")
    draw.polygon(coords((1026, 210, 1026, 248, 1064, 248)), fill=PALE)


RESUME_SCENES = [
    ("Você: Atendia clientes e organizava pedidos. Empresa Exemplo, de 2023 a 2025.\n\nIA: Vou usar esses fatos que você confirmou.",
     "A IA começa pelo que você contou. Não inventa experiência ou resultados."),
    ("IA: Vou separar contato, resumo, experiência e formação.\n\nVocê: Pode organizar o texto.",
     "Seções claras ajudam a ler o currículo e conferir o que ainda falta."),
    ("IA: Sugestão: atendimento a clientes e organização de pedidos.\n\nVocê: Está correto. Fiz também um curso de atendimento.",
     "A redação melhora sem acrescentar habilidades ou números não confirmados."),
    ("IA: Confira os fatos e as datas desta versão.\n\nVocê: Conferi. Aprovo o currículo.",
     "A pessoa confere os arquivos e aprova o conteúdo antes de qualquer envio."),
    ("IA: PDF, Word e texto conferidos. Versão aprovada.\n\nVou conferir esta versão antes de anexar a uma candidatura.",
     "O original é preservado. Cada versão tem sua própria aprovação."),
]


def resume_frame(stage, progress, blink=False):
    image, draw = base("Sua história. Um currículo pronto para enviar.", stage,
                       RESUME_SCENES[stage][0], progress, RESUME_SCENES[stage][1])
    paper(draw, "PRÉVIA DO CURRÍCULO FICTÍCIO")
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
                draw.line(coords((506, y + 24, 1030, y + 24)), fill="#c4d7f5", width=SCALE)
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
            box(draw, (875, 229, 1038, 265), "#e6f0ff")
            text(draw, (892, 237), "EM REVISÃO", 15, INK)
        if stage == 4:
            box(draw, (884, 229, 1038, 265), ACCENT)
            text(draw, (903, 237), "APROVADO", 15, INK)
            for index, label in enumerate(("PDF", "WORD", "TEXTO")):
                if progress >= index / 3:
                    box(draw, (506 + index * 170, 538, 662 + index * 170, 565), "#dceaff")
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
    box(draw, (482, y + 25, 1058, y + 65), "#ffffff", INK if active else "#bdd1ef", radius=6)
    text(draw, (494, y + 33), value, 18, INK)
    if active and blink:
        x = 497 + draw.textlength(value, font=font(18)) / SCALE
        draw.line(coords((x, y + 33, x, y + 56)), fill=INK, width=2 * SCALE)


def portal_frame(stage, progress, blink=False):
    image, draw = base("Chega de preencher os mesmos dados.", stage,
                       PORTAL_SCENES[stage][0], progress, PORTAL_SCENES[stage][1])
    box(draw, (456, 160, 1084, 596), "#ffffff", "#bdd1ef")
    box(draw, (470, 174, 1070, 213), "#e9f1ff", radius=7)
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
        box(draw, (484, 251, 1054, 435), "#e2efff")
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


PRACTICE_SCENES = [
    ("Você: Quero treinar uma entrevista.\n\nIA: Vamos começar com uma pergunta e ajuda a cada resposta?", "O treino é opcional. Você pode começar sem currículo ou conta em um portal.", "Treinar do seu jeito", "RH e apresentação\nTécnica e arquitetura\nInternacional e negociação\n\nVoz, se seu app oferecer.\nTexto também funciona."),
    ("IA: Conte um erro e o que fez depois.\n\nVocê: Alterei a validação do formulário. Deu erro e eu corrigi.", "Uma pergunta por vez. A resposta fica salva antes da análise.", "Primeira tentativa", "Contexto: formulário\nAção: corrigir a validação\n\nAinda falta explicar como\nvocê verificou o resultado."),
    ("IA: Você assumiu o erro. Como conferiu a correção?\n\nNão precisamos inventar números para contar o resultado.", "Feedback sobre a resposta, com evidências e um próximo passo concreto.", "Um exercício pequeno", "Descreva a verificação\nem uma frase.\n\nUse somente fatos que\nvocê consegue confirmar.\nPode pedir uma dica."),
    ("Você: Fiquei cansada. Continuo amanhã.\n\nIA: Salvei sua resposta e o exercício. Podemos parar aqui.", "Pausa preserva a pergunta, a resposta e o feedback. Não há trabalho de fundo.", "Progresso salvo", "Treino: comportamento\nPergunta: erro e aprendizado\nTentativa: 1\nPróximo passo: ensaiar\na verificação da correção."),
    ("Você: Continuar meu treino.\n\nIA: Vamos retomar a verificação do formulário, de onde paramos.", "Ao refazer, compare o que ficou mais claro e escolha o próximo exercício.", "No dia seguinte", "Você: Testei campos vazios\ne preenchidos e conferi\no envio.\n\nIA: Agora a verificação\nestá concreta. Próximo:\ncomo prevenir esse erro?"),
]


def practice_frame(stage, progress, blink=False):
    message, note, title, content = PRACTICE_SCENES[stage]
    image, draw = base('Ensaie hoje. Chegue mais preparado.', stage, message, progress, note)
    paper(draw, 'CADERNO DE TREINO FICTÍCIO')
    text(draw, (506, 245), title, 26, BLUE, bold=True)
    draw.line(coords((506, 287, 1028, 287)), fill=LINE, width=SCALE)
    shown = content[:int(len(content) * progress)]
    paragraph(draw, (506, 308), shown, 520, 21, INK)
    if blink:
        text(draw, (1018, 538), '|', 20, INK, True)
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
    render("entrevista-guiada", practice_frame, 2)
