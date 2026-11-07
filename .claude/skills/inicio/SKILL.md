---
name: inicio
description: Conduzir o início e a retomada do Carreira Guiada quando a pessoa disser iniciar, começar, continuar ou perguntar o que falta. Descobrir o estado sem enviar nada, escolher a próxima etapa e seguir a skill correspondente. Não inferir consentimentos nem iniciar candidaturas por uma pergunta de status.
---

# Início guiado

Leia [AGENTS.md](../../../AGENTS.md). A pessoa não precisa entender arquivos,
comandos nem configurações. Conduza a próxima etapa com uma pergunta curta e
um exemplo. Evite apresentar uma lista de tarefas para ela executar sozinha.

Mostre `./job menu --json` quando a pessoa pedir "menu", "opções" ou "ajuda".
Apresente os quatro nomes e aceite o número ou uma frase curta. Um número
isolado só seleciona uma atividade quando responde ao menu recém-exibido.
Use `menu --choose` com a escolha reconhecida e `--remember` para salvá-la
entre sessões; a flag só é usada após a escolha explícita da pessoa.
Consultar a rota sem essa flag permanece só leitura; uma opção desconhecida mostra
o menu novamente, sem apagar dados. Pedido específico sempre entra direto.

Depois de escolher o preparo completo, ofereça `start.model_setup.question` se ela existir,
sozinha, e explique que a escolha é opcional. Pergunte pelos aplicativos ou
serviços conhecidos, sem exigir nomes técnicos de provedores. Aceite qualquer
fornecedor, inclusive modelos locais. Se a pessoa já informou, reaproveite.
Salve a escolha com `models save`, conforme
[o contrato](../../../docs/CONTRATOS.md#preferências-de-modelos), e consulte
`models recommend`. "Não sei" e "depois" ficam salvos e não reabrem a pergunta.
Não invente opções que a conta oferece: só registre modelos e esforços vistos
no aplicativo ou informados pela pessoa. Lista de modelos vazia é válida.
Leia também `tool_evidence` e `tool_alternatives` quando presentes. Explique
que o escopo é navegador e e-mail fictícios, sem prova de serviços reais.
`basis: exploratory_tools` indica evidência daquela etapa; alternativas
empatadas não definem um vencedor universal. Não misture essa nota com a
qualidade de preparar um currículo, que o laboratório não mede.

Leia `benchmark_evidence` quando presente. Se houver falha crítica na etapa,
explique o problema observado, ofereça outra opção disponível ou conduza a etapa
com conferência dos fatos e campos antes de salvar. Ressalva no texto também
exige cuidado, mesmo com pontuação máxima. Ausência de evidência não vira nota.
Explique uma recomendação por vez, seu motivo e o alcance dos testes em
[modelos](../../../docs/MODELOS.md). Não chame uma sugestão inicial de vencedor
de benchmark nem um teste de texto de prova de automação. Continue com o modelo
atual quando faltarem dados; não peça senha, chave, compra ou instalação.
Pedido específico, início de treino/carreira/empresa e retomada de campanha
têm prioridade. Não interrompa esses percursos para coletar preferências de IA.
Se a pessoa quiser rever a escolha depois, leia `models show` e atualize somente
essa preferência. Isso não invalida perfil ou currículo nem autoriza troca.
Ao longo do preparo, use as [dicas do onboarding](../../../docs/ONBOARDING.md#dicas-durante-o-preparo)
quando forem pertinentes, uma por vez. Preserve a pergunta indicada pelo
controle, sem adicionar questionário técnico ou repetir dicas já dadas.

## Conferir o que já existe

1. Use `./job doctor --json`. Se faltar `uv`, explique a instalação necessária,
   aproveite a autorização que já existir e consulte as instruções oficiais.
   Instale apenas no espaço do usuário quando autorizado. O `uv` pode resolver
   o Python e as dependências locais. Não peça senha de administrador.
   Sem `uv`, o comando termina com uma mensagem em texto antes de produzir
   JSON. Reconheça esse diagnóstico do inicializador, conduza a instalação
   autorizada e repita `doctor` depois. Não trate a ausência de JSON como
   corrupção do perfil nem peça para a pessoa resolver sozinha.
2. Leia `./job start --json` e `./job status --json`. `model_setup` é uma oferta
   opcional; não substitui `next_step`. Consultar a instalação
   vazia não deve criar perfil nem iniciar trabalho externo.
   Se o pedido for somente procurar ou mostrar vagas, use
   `./job start --focus search --json`: esse caminho coleta cargo, modalidade
   e fontes para pesquisa pública sem exigir contatos, currículo ou e-mail.
   Siga [busca](../busca/SKILL.md) para confirmar e conferir o escopo.
   Para currículo, use `start --focus curriculum --json`; peça somente os
   dados profissionais e contatos necessários ao documento. Preserve o foco nas consultas seguintes até
   a pessoa pedir preparo ou envio. A pessoa não precisa conhecer essa opção.
   Para treino de entrevista, use `start --focus practice --json` e siga
   [entrevista](../entrevista/SKILL.md), mesmo sem perfil ou currículo.
   Para ajuda sobre carreira, use `start --focus career --json` e siga
   [carreira](../carreira/SKILL.md). Para analisar uma empresa, use
   `start --focus company --json` e siga [avaliar-empresas](../avaliar-empresas/SKILL.md).
   Nenhum desses caminhos exige currículo, contatos ou fontes de vagas.
3. Consulte `./job context --json` apenas quando precisar das respostas salvas.
   Não repita contatos e valores privados sem necessidade.

## Escolher a próxima etapa

- Se `start` trouxer `welcome_back` e a pessoa disser só "iniciar", apresente
  continuar ou revisar. Se ela já pediu "continuar", "retomar" ou uma tarefa
  específica, siga esse pedido sem repetir o menu. Leia `status.checkpoint`,
  os registros atuais e `tabs status`; o ponto salvo não prova execução ativa.
- Se escolher revisar, leia as respostas privadas por seção e mostre o resumo
  existente, uma seção por vez. Pergunte o que deseja corrigir; use
  `profile answer` apenas para as correções. Preserve histórico e arquivos.
  Depois confira a nova versão do perfil, dos currículos e das sugestões de
  LinkedIn/GitHub afetadas. Refaça apenas o conteúdo que depende da correção.
  Fato de currículo importado usa `resume fact-replace` ou `resume fact-revoke`
  conforme a [skill de currículo](../curriculo/SKILL.md); acrescentar outra
  frase sem retirar o fato antigo não registra a correção.
- Pedido apenas de andamento: responda com o estado observado e pare aí.
- `next_step=career_guidance`: siga o guia de carreira e preserve as respostas
  já salvas. Uma sessão pausada só retoma quando a pessoa pedir. Se ela pedir
  busca de vagas, mude para `--focus search`; carreira continua opcional.
- `next_step=company_dossier`: consulte os dossiês salvos e esclareça a empresa
  e a dúvida da pessoa. Não use o pedido como autorização de candidatura.
- Parada registrada: "continuar" ou "retomar" já autoriza `resume-work`.
  Se a pessoa disse apenas "iniciar", pergunte se quer retomar o objetivo
  interrompido. Nunca remova a parada por conta própria.
- `next_step=curriculum_input`: peça o currículo ou ofereça montá-lo a partir
  das respostas. Siga [curriculo](../curriculo/SKILL.md). Se ela já anexou um
  arquivo, localize e importe sem pedir para anexar novamente.
- Registre a escolha com `intake choose`: `mode=create` para criar ou
  `mode=import` para importar. Inclua `route=curriculum` no atalho de currículo
  ou `route=prepare` quando a pessoa pedir o preparo completo. Depois consulte
  `start` de novo. A escolha fica
  salva mesmo antes da primeira informação profissional.
- `next_step=curriculum_intake`: faça somente a pergunta devolvida em
  `question`, registre a resposta com `intake answer` e siga a skill de currículo.
- `curriculum_complete`: entregue os arquivos aprovados e ofereça revisar,
  criar outra versão ou escolher outra atividade. Não acrescente cadastro de
  candidatura sem pedido.
- `search_scope_confirmation`, `search_ready` ou `search_paused`: siga a
  entrada pública da skill [busca](../busca/SKILL.md).
- Uma seção do perfil está incompleta: siga [perfil](../perfil/SKILL.md),
  limitada à pergunta da atividade atual; não complete todas as seções por rotina.
- `next_step=sources` após o currículo aprovado: apresente a pergunta devolvida
  para os links adiados e siga [docs/FONTES.md](../../../docs/FONTES.md).
  Se pedir ajuda para descobrir sites, siga [fontes](../fontes/SKILL.md).
  A busca de vagas espera os links escolhidos e aprovados. Se quiser só o currículo, entregue
  a versão aprovada e preserve a busca para depois.
- `profile_approval`: apresente o resumo e peça a confirmação da versão.
- `interview_preparation`: siga [entrevista](../entrevista/SKILL.md). Treino é
  opcional; continuar uma campanha preparada tem prioridade sem exigir recusa.
- Pedido de analisar proposta: siga `docs/PROPOSTAS.md`; não altera filtros,
  autoriza contraproposta nem depende de terminar o onboarding.
- `resume_approval`: apresente o rascunho e conduza a revisão do currículo.
- `professional_presence`: siga [presenca](../presenca/SKILL.md), com escolha
  explícita de revisar LinkedIn/GitHub, deixar para depois ou pular.
  Um pedido explícito de continuar uma campanha já preparada tem prioridade
  sobre essa oferta opcional. Siga as candidaturas autorizadas sem exigir a
  revisão de perfis nem registrar uma recusa que a pessoa não deu.
- Perfil e currículo prontos, com objetivo ativo e pedido de continuar:
  confira conexões e siga [candidaturas](../candidaturas/SKILL.md).
- Tudo pronto, sem objetivo: pergunte o que a pessoa quer agora, por exemplo
  procurar vagas, candidatar-se ou conferir retornos. Persista a resposta antes
  de iniciar a operação. Aproveite um objetivo já declarado no pedido atual.

Uma ação incerta bloqueia só sua repetição. Inclua a conferência no portal na
rodada e continue as outras vagas. Não peça novamente dados ou permissões que
já estão confirmados e ainda cobrem a ação.

A descoberta de estado é somente leitura. A skill da próxima etapa pode salvar
as respostas e executar o que foi autorizado. Lembre ocasionalmente que a pessoa
pode dizer "parar" e voltar depois, sem repetir esse aviso a cada resposta.

O trabalho acontece neste chat, sem instalar ou escolher um executor. Depois
do preparo, confira quais ferramentas de navegador e e-mail o aplicativo oferece.
Se faltar uma conexão, use a interface do próprio aplicativo para conduzir a
pessoa. Só descreva botões que você observou. Nunca peça para configurar MCP,
obter chave de API ou executar comandos. Sem ferramenta disponível, explique
o que ficou pendente e continue o preparo ou a pesquisa que ainda for possível.

Use [procedimento de progresso e abas](../../../docs/OPERACAO.md#progresso-e-abas) desde o início: feedback
curto durante a execução, checkpoint após progresso e antes de esperas,
reserva de abas antes de abrir e reconciliação na retomada.
