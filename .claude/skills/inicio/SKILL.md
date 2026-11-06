---
name: inicio
description: Conduzir o início e a retomada do Carreira Guiada quando a pessoa disser iniciar, começar, continuar ou perguntar o que falta. Descobrir o estado sem enviar nada, escolher a próxima etapa e seguir a skill correspondente. Não inferir consentimentos nem iniciar candidaturas por uma pergunta de status.
---

# Início guiado

Leia [AGENTS.md](../../../AGENTS.md). A pessoa não precisa entender arquivos,
comandos nem configurações. Conduza a próxima etapa com uma pergunta curta e
um exemplo. Evite apresentar uma lista de tarefas para ela executar sozinha.

No primeiro uso, ofereça uma orientação breve de
[modelos](../../../docs/MODELOS.md) antes da pergunta atual: um modelo mais
capaz ajuda a preparar perfil e currículo; a operação pode usar Terra 6.1 em
esforço médio ou alto. Não faça a pessoa escolher um modelo para conseguir
começar. Use o que estiver disponível e ofereça ajuda se ela pedir a troca.
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
2. Leia `./job start --json` e `./job status --json`. Consultar a instalação
   vazia não deve criar perfil nem iniciar trabalho externo.
   Se o pedido for somente procurar ou mostrar vagas, use
   `./job start --focus search --json`: esse caminho prepara o perfil e as
   fontes sem exigir currículo. Preserve o foco nas consultas seguintes até
   a pessoa pedir preparo ou envio. A pessoa não precisa conhecer essa opção.
3. Consulte `./job context --json` apenas quando precisar das respostas salvas.
   Não repita contatos e valores privados sem necessidade.

## Escolher a próxima etapa

- Pedido apenas de andamento: responda com o estado observado e pare aí.
- Parada registrada: "continuar" ou "retomar" já autoriza `resume-work`.
  Se a pessoa disse apenas "iniciar", pergunte se quer retomar o objetivo
  interrompido. Nunca remova a parada por conta própria.
- `next_step=curriculum_input`: peça o currículo ou ofereça montá-lo a partir
  das respostas. Siga [curriculo](../curriculo/SKILL.md). Se ela já anexou um
  arquivo, localize e importe sem pedir para anexar novamente.
- Registre a escolha com `intake choose`: `mode=create` para criar ou
  `mode=import` para importar. Depois consulte `start` de novo. A escolha fica
  salva mesmo antes da primeira informação profissional.
- `next_step=curriculum_intake`: faça somente a pergunta devolvida em
  `question`, registre a resposta com `intake answer` e siga a skill de currículo.
- Uma seção do perfil está incompleta: siga [perfil](../perfil/SKILL.md).
- `next_step=sources` após o currículo aprovado: apresente a pergunta devolvida
  para os links adiados e siga [docs/FONTES.md](../../../docs/FONTES.md).
  Não inicie pesquisa sem fontes. Se a pessoa quiser só o currículo, entregue
  a versão aprovada e preserve a busca para depois.
- `profile_approval`: apresente o resumo e peça a confirmação da versão.
- `resume_approval`: apresente o rascunho e conduza a revisão do currículo.
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
