# Escolher o modelo e a ferramenta

O Carreira Guiada é independente do fornecedor de IA. Você pode usar o modelo
que preferir, desde que ele consiga seguir o procedimento e usar as ferramentas
da sessão. Não precisa trocar de assinatura para começar.

O modelo é a IA que interpreta e decide. O aplicativo é onde ela conversa com
você, lê os arquivos e acessa o navegador. Escolher um modelo não conecta, por
si só, sites ou e-mail.

## Se ainda não tem um aplicativo compatível

Comece pelo aplicativo, antes de comparar modelos ou pagar por outra assinatura.
Para usar o projeto e guardar seu progresso, ele precisa abrir uma pasta local
e executar os comandos dela. Um chat que só recebe texto pode ajudar a redigir,
mas não mantém o controle local do Carreira Guiada.

Se já tem um aplicativo de IA, procure no guia oficial dele como abrir uma
pasta de projeto. Se não encontrar, informe seu aplicativo e sistema operacional
ao assistente e peça orientação uma etapa por vez. Ele deve conferir as opções
disponíveis, sem inventar um botão ou exigir uma chave de API no chat.

Para começar com um dos exemplos documentados, escolha **um**:
[Claude Code](https://code.claude.com/docs/en/quickstart) ou
[Codex CLI](https://learn.chatgpt.com/docs/codex/cli). Siga a instalação e o login
do guia oficial escolhido, depois volte a [Primeira vez](GUIA.md#primeira-vez).
Os exemplos usam terminal; o guia do projeto explica os comandos de entrada.
Outros aplicativos com as mesmas capacidades também servem. O controle local
foi preparado para macOS e Linux; Windows nativo não é suportado.

Depois que a pasta estiver aberta, escreva:

> iniciar. Confira o que funciona neste aplicativo e me ajude com o que faltar.

| Quero fazer | O que a IA precisa conferir |
|---|---|
| Currículo, entrevista, carreira ou comparação de propostas | Leitura da pasta, comandos locais e gravação do progresso. Navegador e e-mail podem ficar para depois. |
| Pesquisar vagas ou investigar uma empresa | Acesso a fontes públicas pela ferramenta de pesquisa ou navegador, conforme a tarefa. |
| Preencher e enviar uma candidatura | Navegador utilizável no destino, perfil e currículo aprovados e autorização para aquela ação. |
| Acompanhar retornos | Acesso autorizado à caixa escolhida, pela integração ou pelo navegador disponível. |

A conferência do controle local mostra requisitos e observações salvas. A IA
também precisa verificar a ferramenta da sessão e o acesso ao destino antes
de agir. Ter o modelo instalado ou uma conexão registrada ontem não comprova
que o acesso funciona agora.

Se faltar uma ferramenta, a IA explica o que continua disponível e ajuda a
localizar a conexão no aplicativo. Login é feito por você, na tela do serviço.
Ela não instala integrações, troca de aplicativo ou concede permissões por
conta própria. Você pode deixar a conexão para depois e seguir outra atividade.

## Primeiro, o que você já usa

No preparo completo, a IA oferece uma pergunta sobre os aplicativos ou
serviços que você tem. Também pode abrir **Mais opções** e escolher modelos.
Os atalhos para outras atividades seguem sem essa pergunta. Vale qualquer
fornecedor, inclusive modelos locais. "Não sei" e "depois" também ficam salvos.
Para rever, diga "quero mudar a escolha de modelos". O perfil, o currículo e
as permissões continuam como estavam.

Se você souber apenas o nome do aplicativo, isso basta. A IA ajuda a conferir
quais modelos aparecem na sua conta, sem pedir credenciais. Ter assinatura de
um serviço não comprova acesso a todos os modelos. Também não garante navegador,
e-mail ou execução contínua: essas capacidades precisam ser conferidas na sessão.

## Peça uma indicação para a tarefa

Diga, por exemplo: "Tenho estes modelos. Qual uso para revisar meu currículo?"
A IA confere suas opções e consulta a [tabela por tarefa e provedor](BENCHMARKS.md#escolha-pela-tarefa-e-pelo-provedor).
Você escolhe no aplicativo; o projeto não muda o modelo sozinho.

| Sua atividade | Evidência que importa |
|---|---|
| Começar, revisar currículo ou escolher um foco de carreira | Clareza da orientação, respeito aos fatos e material útil para aquela tarefa. |
| Treinar entrevistas, revisar LinkedIn/GitHub ou investigar empresa | Respostas completas, correções incorporadas e continuidade entre sessões. |
| Comparar propostas ou negociar | Contas conferidas, premissas explícitas e mensagem fiel ao que você autorizou. |
| Buscar vagas, preencher e acompanhar e-mail | Operações concluídas no navegador fictício, conferência do resultado e respeito às permissões. |

Um modelo pode ter bom resultado em carreira e acrescentar fatos no currículo.
Por isso, confira a tarefa específica. Passar no teste de currículo também não
comprova que ele consegue operar o navegador da sua sessão.

## Entenda o esforço sem configurar nada técnico

O esforço é uma opção de raciocínio oferecida por alguns aplicativos. Pode
aparecer como `low`, `medium`, `high`, `xhigh`, `max` ou `ultra`. A IA ajuda a
localizar a escolha que existe na sua conta; você não precisa editar arquivos.

A [matriz de esforços](BENCHMARKS.md#quais-esforços-foram-comparados) mostra o que
foi medido para cada modelo. Nomes iguais em fornecedores diferentes não
significam o mesmo orçamento de raciocínio. Uma opção no catálogo também não
comprova que o serviço aplicou esse esforço: os relatórios distinguem o ajuste
solicitado da confirmação observada no cliente.

Entre opções com evidência suficiente para a tarefa, a indicação preserva a
ordem dos modelos que você informou e escolhe o menor esforço disponível que
cumpriu os critérios daquele modelo. As outras opções elegíveis aparecem como
alternativas. Isso evita escolher uma marca por hábito; não prova que o menor
esforço terá o mesmo desempenho em qualquer situação ou será mais barato.

Se a etapa ficar difícil, a IA primeiro explica o problema: falta informação,
falhou uma ferramenta ou a resposta precisa de revisão. Aumentar o esforço
não resolve falta de acesso nem concede permissão para agir.

## Como ler uma recomendação

- Com evidência na tarefa: a configuração cumpriu os critérios dos recortes
  fictícios e as exigências de revisão. É um ponto de partida para conferir
  na sua sessão.
- Com ressalvas: houve erro, falta de conclusão ou problema no texto. A IA
  explica o cuidado necessário antes de aproveitar o resultado.
- Sem medição: não há evidência compatível com aquela tarefa e esforço. Você
  pode continuar com o modelo atual e revisar o material.
- Com tentativa indevida observada: a etapa exige conferência humana antes
  de envio. Uma ferramenta ter bloqueado a ação não significa que o modelo
  respeitou a autorização.

As recomendações consideram apenas as opções que você informou. Não é preciso
contratar outro serviço para começar. Resultados completos, falhas e limites
ficam no [benchmark](BENCHMARKS.md); a coleta aceita contribuições de outros
fornecedores e modelos locais.

## Segurança e limites da comparação

Os [testes de instruções maliciosas](BENCHMARKS.md#instruções-maliciosas-em-vagas-e-mails-e-retomada)
observam o que o modelo tentou fazer ao ler vagas, e-mails e anotações de
retomada fictícios. A evidência de ataques é separada da qualidade do texto e
do uso de ferramentas. Uma nova coleta bem-sucedida preserva falhas anteriores
para consulta; não demonstra imunidade.

A revisão de conteúdo é feita por modelo, sem estudo com candidatos reais.
Navegador e e-mail são serviços de laboratório, com isolamento e ferramentas
limitadas. Não foram validados login, CAPTCHA, navegação por imagens, serviços
reais ou campanhas por dias. Tempos de uma rodada não estabelecem superioridade
estatística, preço ou consumo de assinatura.

Na prática, a IA confere as ferramentas e acompanha com você a primeira etapa.
Antes de retomar um envio incerto, verifica o resultado no destino. Trocar de
modelo mantém essas regras e suas permissões.

## Usar outra ferramenta ou outro LLM

A IA deve conferir as capacidades, sem depender da marca:

1. Ler `AGENTS.md` e os documentos referenciados na pasta aberta.
2. Executar os comandos locais do projeto e salvar o progresso privado.
3. Usar uma ferramenta de navegador para as etapas que exigem sites.
4. Usar uma conexão autorizada para e-mail, se você quiser acompanhar retornos.

Se o aplicativo não carregar `AGENTS.md` automaticamente, diga:

> Leia o AGENTS.md desta pasta e me guie pelo início do Carreira Guiada.

As skills canônicas estão em `.agents/skills/` e podem ser lidas como arquivos
normais. Não dependem de uma função de skills do aplicativo. As cópias para
Claude Code e os exemplos de Codex CLI facilitam o uso nessas ferramentas;
não restringem a escolha de modelo. Um chat que só responde texto pode ajudar
a redigir, mas não executa o fluxo local nem opera sites sem essas capacidades.

## Trocar de modelo sem recomeçar

Diga que quer trocar de modelo. A IA salva e confere o estado antes da troca;
você seleciona a opção disponível na ferramenta. Se isso abrir uma nova sessão,
use a mesma pasta e diga `continuar`. O novo agente relê o procedimento, o
perfil aprovado, o objetivo e as pendências, e confere as conexões.

As respostas salvas não precisam ser repetidas. Formulários ainda abertos
precisam ser preservados, e um envio incerto deve ser verificado antes de
qualquer nova tentativa. A IA não troca de assinatura, instala outro agente
nem transfere seus dados para outro fornecedor sem sua decisão.

## Continuidade por objetivo

Use o modo objetivo (`goal`) da ferramenta quando ele existir e estiver
disponível para a sessão. Ele ajuda a continuar o trabalho autorizado entre
rodadas. A IA confere o recurso real antes de explicar como ativá-lo; não há
um comando universal para todos os aplicativos.

O projeto também guarda o objetivo localmente para retomadas. Esse registro
não mantém um processo rodando. Uma campanha por dias exige que o ambiente
mantenha a execução e as conexões disponíveis, dentro dos limites da conta.
[Veja como pedir a busca por objetivo](GUIA.md#buscar-por-objetivo).
