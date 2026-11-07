# Escolher o modelo e a ferramenta

O Carreira Guiada é independente do fornecedor de IA. Você pode usar o modelo
que preferir, desde que ele consiga seguir o procedimento e usar as ferramentas
da sessão. Não precisa trocar de assinatura para começar.

O modelo é a IA que interpreta e decide. O aplicativo é onde ela conversa com
você, lê os arquivos e acessa o navegador. Escolher um modelo não conecta, por
si só, sites ou e-mail.

## Primeiro, o que você já usa

No início, a IA pergunta quais aplicativos ou serviços você tem. Vale qualquer
fornecedor, inclusive modelos locais. "Não sei" e "depois" também ficam salvos.
Para rever, diga "quero mudar a escolha de modelos". O perfil, o currículo e
as permissões continuam como estavam.

Se você souber apenas o nome do aplicativo, isso basta. A IA ajuda a conferir
quais modelos aparecem na sua conta, sem pedir credenciais. Ter assinatura de
um serviço não comprova acesso a todos os modelos. Também não garante navegador,
e-mail ou execução contínua: essas capacidades precisam ser conferidas na sessão.

## Sugestões iniciais por etapa

| Etapa | Sugestão do projeto | Quando usar |
|---|---|---|
| Preparar perfil e currículo | GPT-6 Astra ou Claude Opus 5.5 | Organizar experiências, conferir fatos, definir filtros e permissões. |
| Buscar e operar candidaturas | GPT-6.1 Terra, esforço médio (`medium`) | Navegar, preencher e conferir o resultado das ações autorizadas. |
| Resolver uma etapa difícil | Terra com esforço alto (`high`), ou voltar a Astra/Opus | Formulário incomum, regra ambígua ou divergência que exige análise. |
| Organizar material já conferido | Modelo menor que você já usa, com esforço baixo ou médio quando disponível | Resumir vagas e classificar conteúdo, conferindo os resultados antes de agir. |

O esforço indica quanto o modelo deve raciocinar. Mais esforço pode consumir
mais tempo e uso da sua conta. Nem toda ferramenta oferece esse ajuste ou usa
os mesmos nomes. Comece com a opção indicada; a IA deve ajudar a localizar a
escolha no aplicativo sem pedir que você edite configurações técnicas.

Terra 6.1 com `medium` é nossa recomendação inicial para automação. Suba para
`high` se a etapa exigir mais análise. Não recomendamos reduzir o esforço
apenas porque a tarefa parece repetitiva: é preciso conferir o destino, os
campos e o resultado de cada envio. Haiku 5.5 não foi validado pelo projeto
para operar candidaturas; por isso não é nossa sugestão para essa função.

Estas são sugestões iniciais de uso, condicionadas ao acesso da pessoa.
O [benchmark público](BENCHMARKS.md) separa decisões sobre situações fictícias,
clareza da resposta e execução da aplicação. Um resultado alto em perguntas
estruturadas não comprova automação de navegador nem define o melhor modelo
para todas as etapas. O protocolo aceita contribuições com outros provedores.

As referências oficiais usadas na orientação original descrevem o
[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)
para raciocínio complexo e criação de documentos, e o
[GPT-6.1 Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra)
para raciocínio visual, uso do computador e escrita, com suporte a esforço
médio e alto. A Anthropic apresenta o
[Opus 5.5](https://www.anthropic.com/claude-opus-5-5)
para trabalho com agentes, uso do computador e tarefas complexas.
Fontes consultadas em 5 de novembro de 2026. Nomes e disponibilidade variam;
confira o catálogo da sua conta quando for escolher. Essas referências não
substituem os resultados e limites do benchmark.

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
