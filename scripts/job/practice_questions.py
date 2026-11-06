"""Question bank for private practice; exercises are not employer assessments."""

CATALOG = {
    'rh': [
        ('apresentacao', 'Conte sobre você e resuma sua trajetória.', 'Apresentar uma trajetória verdadeira e relevante.'),
        ('motivacao', 'O que despertou seu interesse pela vaga?', 'Relacionar motivação ao contexto disponível.'),
        ('saida', 'Como você explica sua saída ou desejo de mudança?', 'Explicar a transição com respeito e clareza.'),
        ('desafio', 'Conte um desafio que enfrentou e sua contribuição.', 'Explorar contexto, ação e resultado.'),
        ('erro', 'Conte um erro e o que aprendeu com ele.', 'Identificar aprendizado sem inventar fatos.'),
        ('qualidade', 'Qual qualidade sua ajuda no trabalho? Conte um exemplo.', 'Sustentar uma qualidade com uma situação real.'),
        ('desenvolvimento', 'Qual ponto você precisa desenvolver e o que está fazendo a respeito?', 'Demonstrar autoconhecimento sem usar um defeito disfarçado de elogio.'),
        ('futuro', 'O que você gostaria de desenvolver no futuro?', 'Relacionar objetivos a passos possíveis.'),
        ('perguntas', 'O que você gostaria de perguntar à pessoa recrutadora?', 'Investigar expectativas, equipe, etapas e condições da vaga.'),
    ],
    'presentation': [
        ('trajetoria', 'Como você resumiria sua trajetória para esta oportunidade?', 'Conectar presente, experiências relevantes e direção desejada.'),
        ('contribuicao', 'Qual contribuição sua melhor demonstra o que você pode oferecer?', 'Explicar participação individual sem apagar o trabalho da equipe.'),
        ('transicao', 'Como sua experiência anterior se conecta ao trabalho que procura agora?', 'Apresentar habilidades transferíveis e limites com honestidade.'),
        ('resumo', 'Agora faça uma apresentação curta que você diria em voz alta.', 'Escolher o essencial sem decorar um discurso artificial.'),
    ],
    'behavioral': [
        ('desafio', 'Conte sobre o maior desafio profissional ou de estudo que enfrentou.', 'Entender contexto, decisão, ação e resultado conhecido.'),
        ('erro', 'Conte um erro seu e como você lidou com as consequências.', 'Assumir responsabilidade e explicar mudanças de comportamento.'),
        ('conflito', 'Como você lidou com uma discordância no trabalho ou em um projeto?', 'Mostrar escuta, respeito e resolução concreta.'),
        ('feedback', 'Conte um feedback difícil que recebeu e o que fez depois.', 'Distinguir reação inicial de aprendizado e ação.'),
        ('prioridades', 'O que você faz quando duas demandas urgentes competem pelo seu tempo?', 'Explicar critérios, comunicação e negociação de prazo.'),
        ('limite', 'Como você comunica que ainda não sabe fazer algo?', 'Expressar limites com um plano realista para aprender ou pedir ajuda.'),
    ],
    'technical': [
        ('experiencia', 'Explique uma solução técnica que você conhece e as decisões tomadas.', 'Comunicar contexto, contribuição e escolhas.'),
        ('investigacao', 'Como você investigaria uma falha que ainda não entende?', 'Explicitar hipóteses, evidências e validação.'),
        ('tradeoffs', 'Descreva uma decisão técnica e suas alternativas.', 'Explicar custos, limites e consequências.'),
        ('qualidade', 'Como você verificaria que a solução funciona para quem vai usá-la?', 'Considerar testes, acessibilidade quando pertinente e evidência de resultado.'),
        ('incidente', 'Como você responderia a um incidente depois de publicar uma mudança?', 'Conter impacto, investigar, comunicar e prevenir recorrência.'),
    ],
    'coding': [
        ('requisitos', 'Para um exercício original adequado à sua área, quais requisitos e exemplos você confirmaria antes de começar?', 'Entender entradas, saídas e casos de borda.'),
        ('solucao', 'Explique ou escreva uma solução para o exercício combinado e como a testaria.', 'Avaliar raciocínio, implementação e testes sem executar código automaticamente.'),
        ('bordas', 'Que casos de borda ou entradas inválidas sua solução precisa tratar?', 'Explicitar decisões e demonstrar casos verificáveis.'),
        ('revisao', 'O que você mudaria na solução se tivesse mais tempo?', 'Priorizar melhorias e explicar complexidade e limitações.'),
    ],
    'system_design': [
        ('requisitos', 'Quais requisitos, restrições e hipóteses você confirmaria para o sistema proposto?', 'Definir escopo e hipóteses.'),
        ('escala', 'Que volume e escala você espera? Como suas hipóteses afetam o projeto?', 'Dimensionar sem tratar estimativas como fatos.'),
        ('dados_api', 'Como organizaria dados, armazenamento e APIs?', 'Justificar contratos e persistência.'),
        ('diagrama', 'Descreva um diagrama textual ou Mermaid dos componentes e fluxos.', 'Comunicar a arquitetura.'),
        ('decisoes', 'Quais alternativas e tradeoffs orientam suas decisões?', 'Comparar escolhas e custos.'),
        ('falhas', 'Como lidaria com falhas, segurança e recuperação?', 'Discutir riscos e resiliência.'),
        ('operacao', 'Como observaria o sistema e controlaria custos?', 'Discutir métricas, alertas e custo.'),
    ],
    'international': [
        ('apresentacao', 'Como você apresentaria sua experiência no idioma combinado para o treino?', 'Treinar comunicação sem presumir fluência nem exigir sotaque específico.'),
        ('remoto', 'Como você se organizaria para trabalhar com uma equipe em outro fuso?', 'Explicitar disponibilidade real e comunicação assíncrona.'),
        ('clareza', 'Como pediria esclarecimento quando não entendesse uma pergunta?', 'Praticar confirmação respeitosa sem fingir compreensão.'),
        ('contratacao', 'Que condições da contratação internacional você precisa confirmar?', 'Separar localização permitida, contrato, autorização de trabalho e remuneração.'),
        ('colaboracao', 'Conte uma situação de colaboração com pessoas de contextos diferentes.', 'Mostrar adaptação com fatos reais, sem estereótipos.'),
    ],
    'negotiation': [
        ('expectativa', 'Como responderia à pergunta sobre sua pretensão salarial?', 'Usar a pretensão autorizada sem revelar automaticamente o mínimo privado.'),
        ('pacote', 'O que falta entender antes de comparar esta proposta com outra?', 'Conferir moeda, período, regime, benefícios, custos e condições.'),
        ('contraproposta', 'Como pediria uma revisão da proposta com base no que pode entregar?', 'Fazer um pedido claro, fundamentado e sem inventar ofertas concorrentes.'),
        ('alternativas', 'Se o valor fixo não puder mudar, que condições fariam diferença para você?', 'Explorar benefícios e condições realmente relevantes.'),
        ('pressao', 'Como responderia a uma pressão para aceitar imediatamente?', 'Pedir prazo e proposta por escrito, preservando uma decisão consciente.'),
    ],
}

LABELS = {'rh': 'Conversa com RH', 'presentation': 'Apresentação e trajetória',
          'behavioral': 'Perguntas comportamentais', 'technical': 'Entrevista técnica',
          'coding': 'Exercício prático', 'system_design': 'Arquitetura e system design',
          'international': 'Entrevista internacional', 'negotiation': 'Negociação salarial'}

EXERCISES = {
    'coding': 'Exercício fictício: receba uma lista de tarefas com id, título e estado (pendente ou concluída). Retorne as pendentes sem repetir IDs, preservando a ordem. Combine o tratamento de entradas inválidas e de IDs repetidos com estados diferentes antes de implementar. Você pode usar uma linguagem que conhece ou explicar em texto.',
    'system_design': 'Exercício fictício: projete um sistema de reserva de salas. Pessoas consultam horários, reservam e cancelam. Duas pessoas não podem reservar a mesma sala no mesmo horário. Volume, disponibilidade e integrações ainda precisam ser combinados; trate números propostos como hipóteses.',
}

HINTS = {
    'rh': 'Use uma situação verdadeira. Contexto: o que acontecia. Ação: o que você fez. Resultado ou aprendizado: o que conseguiu observar. Não precisa inventar números.',
    'presentation': 'Comece pelo trabalho que faz ou procura, escolha uma experiência que sustente isso e diga qual direção busca. Se for o primeiro emprego, use estudos e projetos reais.',
    'behavioral': 'Escolha um episódio específico. Separe o problema, sua responsabilidade, a ação que tomou e o aprendizado. Você pode omitir nomes e detalhes confidenciais.',
    'technical': 'Explique o problema antes da ferramenta. Depois mostre uma hipótese, como a verificaria e o que mudaria se a evidência contrariasse sua ideia.',
    'coding': 'Comece com um exemplo pequeno de entrada e saída. Depois explique os passos da solução e um teste que mostre se ela funciona.',
    'system_design': 'Requisitos: quem usa e para quê. Hipóteses: o que ainda não sabemos. Comece com poucos componentes e explique uma decisão por vez; uma lista de tecnologias não basta.',
    'international': 'Você pode pedir para repetir ou reformular a pergunta. Faça uma frase curta com uma ideia por vez; clareza importa mais que tentar usar palavras difíceis.',
    'negotiation': 'Agradeça, confirme os componentes da proposta e faça um pedido objetivo com sua justificativa. Seu mínimo privado e sua pretensão são informações diferentes.',
}
