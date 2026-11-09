"""Render fictional resume and browser walkthroughs without network access."""

from PIL import Image

from render_docs import OUT, SIZE, SCALE, INK, MUTED, TEXT, ACCENT
from render_docs import coords, font, text, wrap, backdrop, progress_track, BLUE, LINE, DIM, white_palette


def box(draw, bounds, fill, outline=None, radius=12):
    """Draw a rounded rectangle with bounds and radius in logical pixels."""
    draw.rounded_rectangle(coords(bounds), radius=radius * SCALE,
                           fill=fill, outline=outline, width=2 * SCALE)


def paragraph(draw, position, value, width, size=19, fill=TEXT, *, cursor=False, bottom=None):
    """Draw wrapped monospaced text and return the next logical y coordinate.

    Preserve explicit line breaks, optionally append a caret, and raise
    ValueError if a line would exceed the supplied bottom boundary.
    """
    x, y = position
    last = ""
    for part in value.split('\n'):
        for line in wrap(draw, part, width=width, size=size):
            if bottom is not None and y + size + 6 > bottom:
                raise ValueError("O parágrafo ultrapassou a área de leitura.")
            text(draw, (x, y), line, size, fill, True)
            last = line
            y += size + 8
    if cursor:
        caret = x + draw.textlength(last, font=font(size, True)) / SCALE + 2
        draw.line(coords((caret, y - size - 3, caret, y - 3)), fill=fill, width=2 * SCALE)
    return y


def pointer(draw, position, clicking=False):
    """Draw a fictional pointer at logical coordinates, with an optional click ring."""
    x, y = position
    if clicking:
        draw.ellipse(coords((x - 14, y - 14, x + 14, y + 14)),
                     outline="#60d9f4", width=3 * SCALE)
    draw.polygon(coords((x, y, x + 5, y + 23, x + 11, y + 15,
                         x + 22, y + 14)), fill=INK, outline="#ffffff", width=2 * SCALE)


def base(title, subtitle, number, message, progress, note):
    """Return an RGB scene and drawing context for a zero-based journey step.

    Progress from 0 to 1 reveals the conversation during the first half of the
    step. Reject conversation overflow and draw the footer and progress track.
    """
    image, draw = backdrop(dark=True)
    text(draw, (40, 78), title, 38, TEXT, bold=True)
    text(draw, (40, 134), subtitle, 23, DIM)
    box(draw, (28, 192, 432, 610), "#ffffff", LINE)
    text(draw, (40, 206), ">_ conversa com sua IA", 19, INK, True)
    draw.line(coords((40, 244, 407, 244)), fill=LINE, width=SCALE)
    visible = message[:max(1, int(len(message) * min(1, progress * 2)))]
    end = paragraph(draw, (40, 266), visible, 374, 23, INK)
    if end > 550:
        raise ValueError("A conversa ultrapassou a área de leitura.")
    text(draw, (40, 556), f"0{number + 1}", 32, BLUE, bold=True)
    text(draw, (96, 568), "DE 05 ETAPAS", 14, MUTED)
    for index, line in enumerate(wrap(draw, note, 1030, 20, mono=False)):
        text(draw, (40, 632 + index * 25), line, 20, TEXT)
    progress_track(draw, number, progress, dark=True)
    return image, draw


def paper(draw, label):
    """A document on the stage, not a second application window."""
    text(draw, (480, 176), label, 15, DIM)
    box(draw, (468, 204, 1080, 610), "#ffffff", radius=8)
    draw.rectangle(coords((468, 226, 474, 280)), fill=BLUE)


RESUME_SCENES = [
    ("Você: Atendia clientes e organizava pedidos. Empresa Exemplo, 2023 a 2025.\n\nIA: Vou usar esses fatos.",
     "O currículo começa pela sua experiência, com fatos que você confirmou."),
    ("IA: Vou separar contato, resumo, experiência e formação.\n\nVocê: Pode organizar o texto.",
     "Uma coluna e seções claras facilitam a leitura por pessoas e sistemas de seleção."),
    ("IA: Atendimento a clientes e organização de pedidos.\n\nVocê: Correto. Também fiz um curso de atendimento.",
     "A redação fica mais clara e mantém a sua experiência real."),
    ("IA: Confira os fatos e as datas desta versão.\n\nVocê: Conferi. Aprovo o currículo.",
     "A pessoa confere os arquivos e aprova o conteúdo antes de qualquer envio."),
    ("IA: PDF, Word e texto conferidos.\n\nVou usar a versão aprovada na candidatura.",
     "O original é preservado. Cada versão tem sua própria aprovação."),
]


def resume_frame(stage, progress, blink=False):
    """Return a fictional resume frame for stage 0 to 4 and progress 0 to 1.

    Show confirmed facts, document structure, revision or approval according
    to the stage, optionally blinking the caret in the active text.
    """
    image, draw = base("Seu currículo, claro e pronto para a vaga.",
                       "Organize sua experiência e revise o conteúdo antes de enviar.", stage,
                       RESUME_SCENES[stage][0], progress, RESUME_SCENES[stage][1])
    paper(draw, "PRÉVIA DO CURRÍCULO FICTÍCIO")
    if stage == 0:
        text(draw, (506, 236), "Fatos confirmados", 27, INK)
        raw = "Pessoa Exemplo\npessoa@example.invalid\nEmpresa Exemplo | 2023 a 2025\nAtendia clientes e organizava pedidos."
        shown = raw[:int(len(raw) * progress)]
        paragraph(draw, (506, 300), shown, 538, 21, INK, cursor=blink, bottom=580)
    else:
        text(draw, (506, 224), "Pessoa Exemplo", 30, INK)
        text(draw, (506, 266), "pessoa@example.invalid", 18, MUTED)
        headings = [("RESUMO", 310), ("EXPERIÊNCIA", 402), ("FORMAÇÃO", 494)]
        for index, (label, y) in enumerate(headings):
            if stage > 1 or progress >= index / 3:
                text(draw, (506, y), label, 15, MUTED)
                draw.line(coords((506, y + 22, 1040, y + 22)), fill="#c4d7f5", width=SCALE)
        if stage >= 2:
            summary = "Atendimento a clientes.\nOrganização de pedidos."
            summary = summary[:int(len(summary) * progress)] if stage == 2 else summary
            paragraph(draw, (506, 338), summary, 534, 20, INK,
                      cursor=stage == 2 and blink, bottom=396)
            text(draw, (506, 428), "Empresa Exemplo | 2023 a 2025", 20, INK)
            text(draw, (506, 457), "Atendimento e organização de pedidos", 20, INK)
            if stage > 2 or progress > 0.65:
                text(draw, (506, 523), "Curso de atendimento ao público", 20, INK)
        if stage == 3:
            box(draw, (875, 229, 1038, 265), "#e6f0ff")
            text(draw, (892, 237), "EM REVISÃO", 15, INK)
        if stage == 4:
            box(draw, (884, 229, 1038, 265), ACCENT)
            text(draw, (903, 237), "APROVADO", 15, INK)
            for index, label in enumerate(("PDF", "WORD", "TEXTO")):
                if progress >= index / 3:
                    box(draw, (506 + index * 180, 566, 672 + index * 180, 599), "#dceaff")
                    text(draw, (550 + index * 180, 574), label, 16, INK)
    return image


PORTAL_SCENES = [
    ("IA: Encontrei uma vaga. Vou conferir a empresa e seus filtros antes de preencher.",
     "Perfil e currículo aprovados. Navegador conectado e pesquisa autorizada."),
    ("IA: Vou preencher os contatos que você confirmou e conferir os campos.",
     "Nome e contato são reaproveitados. Você não precisa digitá-los a cada vaga."),
    ("IA: Vou usar sua apresentação e anexar o currículo que você aprovou.",
     "O anexo é conferido antes do envio. A apresentação usa apenas fatos confirmados."),
    ("IA: Campos e currículo conferidos. Posso enviar?\n\nVocê: Pode enviar esta candidatura.",
     "Neste exemplo, a pessoa escolheu perguntar antes de cada envio."),
    ("IA: O portal confirmou o recebimento.\n\nVou registrar e seguir para a próxima vaga.",
     "Só a confirmação conta como envio. Resultado incerto exige conferência."),
]


def field(draw, y, label, value, active=False, blink=False):
    """Draw a labeled fictional input, adding a caret only when active and blinking."""
    text(draw, (482, y), label, 18, MUTED)
    box(draw, (482, y + 25, 1058, y + 65), "#ffffff", INK if active else "#bdd1ef", radius=6)
    text(draw, (494, y + 33), value, 20, INK)
    if active and blink:
        x = 497 + draw.textlength(value, font=font(20)) / SCALE
        draw.line(coords((x, y + 33, x, y + 56)), fill=INK, width=2 * SCALE)


def portal_frame(stage, progress, blink=False):
    """Return a fictional application frame for stage 0 to 4 and progress 0 to 1.

    Animate the pointer or field text through vacancy review, contact details,
    resume attachment, permission and simulated confirmation. No data is sent.
    """
    image, draw = base("Chega de repetir formulários.",
                       "A IA preenche o portal com os dados e o currículo aprovados.", stage,
                       PORTAL_SCENES[stage][0], progress, PORTAL_SCENES[stage][1])
    background = image.copy()
    box(draw, (456, 160, 1084, 596), "#ffffff", "#bdd1ef")
    box(draw, (470, 174, 1070, 213), "#e9f1ff", radius=7)
    text(draw, (485, 185), "carreiras.example | PORTAL FICTÍCIO", 16, INK, True)
    if stage == 0:
        text(draw, (482, 241), "Empresa Exemplo", 26, INK)
        text(draw, (482, 285), "Atendimento ao cliente", 24, INK)
        text(draw, (482, 325), "Remoto | Requisitos compatíveis", 20, MUTED)
        paragraph(draw, (482, 369), "Atender clientes e organizar pedidos. Confira a descrição antes de se candidatar.", 550, 20, INK, bottom=480)
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
    # Preserve the portal artwork while leaving space beneath the subtitle.
    bounds = coords((456, 160, 1086, 598))
    panel = image.crop(bounds)
    image.paste(background.crop(bounds), bounds[:2])
    image.paste(panel, coords((456, 176)))
    return image


PRACTICE_SCENES = [
    ("Você: Quero treinar uma entrevista.\n\nIA: Vamos ensaiar uma pergunta de cada vez.", "Comece pelo tipo de entrevista. Use voz se o seu aplicativo oferecer essa opção.", "Escolha seu treino", "RH e apresentação\nTécnica e system design\nInternacional e negociação\n\nUse voz, se o app permitir."),
    ("IA: Conte um erro e o que fez depois.\n\nVocê: Mudei a validação. Deu erro e eu corrigi.", "O feedback aponta o que ficou claro e o que você pode explicar melhor.", "O que já ficou claro", "Você explicou o erro\ne a correção.\n\nFalta contar como\nverificou o resultado."),
    ("IA: Você explicou a correção. Como testou o resultado?\n\nPode pedir uma dica.", "Um exercício de cada vez, com exemplos reais da sua experiência.", "Ensaie o que faltou", "Como você testou\na correção?\n\nResponda em uma frase,\ncom fatos que viveu."),
    ("Você: Preciso parar. Continuo amanhã.\n\nIA: Tudo bem. Seu treino está salvo.", "A pausa preserva sua pergunta, sua resposta e o feedback.", "Seu treino está salvo", "Pergunta e resposta salvas.\nFeedback preservado.\n\nPróximo passo:\nexplicar a verificação."),
    ("Você: Continuar meu treino.\n\nIA: Vamos retomar a verificação do formulário.", "Compare as tentativas e escolha o próximo exercício com a IA.", "Uma resposta mais clara", "Testei campos vazios\ne preenchidos e conferi\no envio.\n\nAgora temos uma ação\nconcreta de verificação."),
]


def practice_frame(stage, progress, blink=False):
    """Return an interview rehearsal frame for stage 0 to 4 and progress 0 to 1.

    Reveal the stage's practice notes with an optional caret, covering the
    exercise, feedback, pause and resumption using only fictional dialogue.
    """
    message, note, title, content = PRACTICE_SCENES[stage]
    image, draw = base('Ensaie a entrevista, uma resposta por vez.',
                       'Receba feedback e pratique o que ainda precisa melhorar.',
                       stage, message, progress, note)
    paper(draw, 'CADERNO DE TREINO FICTÍCIO')
    text(draw, (506, 245), title, 26, BLUE, bold=True)
    draw.line(coords((506, 287, 1028, 287)), fill=LINE, width=SCALE)
    shown = content[:int(len(content) * progress)]
    paragraph(draw, (506, 308), shown, 534, 22, INK, cursor=blink, bottom=586)
    return image


def render(name, draw_frame, poster):
    """Write a PNG poster and a looping five-stage GIF from a frame callback.

    The callback accepts a zero-based stage, progress from 0 to 1 and an optional
    blink flag. Use a shared palette and millisecond timings for typing frames,
    cursor blinks and reading pauses; poster selects a completed stage.
    """
    draw_frame(poster, 1).save(OUT / (name + ".png"))
    # A single palette keeps text colors steady and allows compact delta frames.
    samples = Image.new("RGB", (SIZE[0] * 5, SIZE[1]))
    for stage in range(5):
        samples.paste(draw_frame(stage, 1), (stage * SIZE[0], 0))
    palette = white_palette(samples)
    frames, durations = [], []
    for stage in range(5):
        timeline = [(i / 32, 100, True) for i in range(33)]
        timeline += [(1, 450, blink) for _ in range(4) for blink in (False, True)]
        timeline += [(1, 2000, False)]
        for progress, duration, blink in timeline:
            frames.append(draw_frame(stage, progress, blink).quantize(palette=palette, dither=Image.Dither.NONE))
            durations.append(duration)
    frames[0].save(OUT / (name + ".gif"), save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    print(f"{name}: {len(frames)} quadros, {sum(durations) / 1000:.1f} segundos")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    render("curriculo-revisado", resume_frame, 4)
    render("candidatura-portal", portal_frame, 3)
    render("entrevista-ensaio", practice_frame, 2)
