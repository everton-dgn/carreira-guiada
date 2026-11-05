# Seu primeiro uso do Job

Você não precisa saber programar. O Job é uma pasta que sua IA lê para
conduzir a busca de emprego, uma etapa por vez. Este guia mostra o começo;
durante o uso, a própria IA explica o próximo passo.

## Primeira vez

1. Na página do projeto no GitHub, use **Code** e **Download ZIP** para baixar
   os arquivos. Abra o arquivo baixado para extrair a pasta. Ela pode se chamar
   `job-main`; esse nome também funciona.
2. Abra essa pasta no aplicativo de IA que você usa, como Codex ou Claude Code.
   A pasta aberta deve conter `README.md`, `AGENTS.md` e o arquivo `job`.
   Só colar o link do GitHub em um chat comum não dá acesso aos arquivos locais.
3. No chat desse projeto, escreva **iniciar**.
4. A IA confere o ambiente e conduz uma pergunta por vez. Se faltar uma
   ferramenta, ela explica a instalação e pede a autorização necessária.

Se não encontrar como abrir a pasta, diga ao assistente qual aplicativo está
usando e que quer abrir a pasta do Job. Ele deve orientar com base nas opções
que conseguir observar, sem inventar nomes de botões.

O controle local usa macOS ou Linux. Windows nativo não é suportado; WSL ainda
não foi validado. A IA precisa conseguir ler arquivos e executar ferramentas.

![O início passa por currículo, objetivo, links, escolhas e aprovação.](assets/inicio-guiado.png)

## A primeira conversa

Você pode dizer:

> iniciar. Não tenho currículo e é meu primeiro emprego.

Ou:

> iniciar. Anexei meu currículo e quero revisar antes de procurar vagas.

A IA recebe o arquivo ou monta um rascunho com você. Depois confirma nome,
e-mail, tipo de trabalho, salário e permissões. Não sabe um valor ou uma data?
Diga "não sei". Nada deve ser inventado.

Ela também pergunta **onde procurar**. Copie os links que você escolheu da
barra do navegador e cole no chat. Se ainda não tiver os links, diga "deixe
para depois". O currículo pode continuar; a pesquisa espera por essa escolha.
[Ajuda para informar os links](FONTES.md).

Você confere o resumo do perfil e aprova o currículo antes de qualquer envio.
Detalhes das perguntas: [Onboarding](ONBOARDING.md).

## Uma rodada de vagas

1. Diga o que quer: "só me mostre as vagas" ou "procure vagas e me pergunte
   antes de enviar". Uma permissão de pesquisa não autoriza envio.
2. A IA busca nos endereços aprovados e explica quais vagas combinam com os
   filtros. Ela confere empresa e destino antes de fornecer seus dados.
3. Se algo importante estiver ausente, ela pergunta ou segue a regra que você
   já escolheu. Seu mínimo salarial não vira pretensão pública automaticamente.
4. Antes do envio, ela confere os dados e o currículo. A autorização segue
   as suas escolhas. A candidatura só é contada após confirmação do destino.
5. Você recebe o que foi confirmado, o que ficou em dúvida e a próxima ação.

![A candidatura tem revisão, resultado confirmado, pausa e retomada.](assets/candidatura-guiada.png)

Uma vaga bloqueada por login não impede cuidar de outra. Um envio com resultado
incerto exige conferência antes de tentar novamente.

## Retornos por e-mail

Você decide se quer permitir leitura. Faça login somente na interface da conta
ou na conexão do aplicativo. Nunca informe senha ou código no chat.

A IA procura mensagens relacionadas às vagas acompanhadas e verifica a origem.
Para responder, mostra o destinatário e o texto para sua aprovação. Para
agendar, mostra a data completa, o horário e o fuso. Comparecer à entrevista
continua sendo uma ação sua.

A limpeza usa categorias que você autorizou, preserva mensagens com etapas
pendentes e move apenas mensagens individuais para a lixeira restaurável.
Ela não deve apagar e-mails definitivamente.

## Parar, voltar e corrigir

| Você diz | O que deve acontecer |
|---|---|
| "parar" | Novas ações param; o progresso é preservado. |
| "continuar" | A IA confere o estado salvo e o próximo passo autorizado. |
| "o que falta?" | Mostra pendências e o que depende de você. |
| "quero corrigir meu salário" | Atualiza a resposta e pede aprovação do perfil. |
| "não use mais este site" | Revê as fontes e pede aprovação da nova lista. |

O trabalho depende de execução ativa. A pasta guarda progresso, mas não
mantém uma IA rodando sozinha depois que a sessão termina.

## Quando algo trava

Descreva o que aconteceu. A IA deve explicar a próxima ação em linguagem
simples. Login, CAPTCHA e avaliações pessoais ficam com você. Restrições do
serviço devem ser respeitadas, sem tentativas de contorno.

Você pode continuar preparando o perfil mesmo quando uma integração estiver
indisponível. [Mais dúvidas](FAQ.md) · [Privacidade](PRIVACIDADE.md).
