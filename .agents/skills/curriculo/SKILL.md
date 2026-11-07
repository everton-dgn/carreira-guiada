---
name: curriculo
description: Anexar, importar, criar do zero, revisar e aprovar currículos da pessoa, sem pedir caminho técnico e sem inventar fatos. Usar quando a pessoa fala de currículo, CV, anexar arquivo, não ter currículo ou precisar de versão por especialidade. Não usar para enviar candidatura.
---

# Currículo guiado

Leia "Currículo" em [AGENTS.md](../../../AGENTS.md) e a API de
`ResumeManager` em [docs/CONTRATOS.md](../../../docs/CONTRATOS.md). Guia da
pessoa: [docs/CURRICULOS.md](../../../docs/CURRICULOS.md).

## Entrada direta

No pedido de currículo, use `start --focus curriculum`. Em toda chamada de
`intake choose`, acrescente `route: curriculum`. Para preparo completo já
escolhido, use `route: prepare`. Não colete salário, sites, permissões de
candidatura ou contas de e-mail só para gerar um documento. Contato no currículo
é diferente de conexão à caixa de entrada.

## Receber o arquivo

- Peça "anexe o currículo aqui no chat" ou "copie o arquivo para a pasta do
  projeto". Nunca pergunte caminho. Localize o anexo pela ferramenta do chat ou
  liste os arquivos da raiz e confirme pelo nome ("é este: curriculo.pdf?").
- Registre `intake choose` com `mode=import` e importe com
  `./job resume import`, com `file` (caminho localizado) e `label` por JSON via
  stdin. Não exponha o caminho nos argumentos do comando. Use "Geral" para o
  primeiro currículo; a pessoa não precisa escolher um nome técnico. O original é preservado; nunca
  sobrescreva. `./job resume sources` lista os originais importados.
- Mostre o texto extraído em blocos curtos e pergunte se está correto. Fatos
  extraídos não viram aprovação automática.
- Se a pessoa colar o texto no chat, use o caminho de criação com
  `intake choose` e `mode=create`, mesmo que antes tivesse escolhido importar.
  Confirme os trechos com ela, reaproveite os dados confirmados em
  `intake answer` e pergunte apenas o que faltar. Não crie um TXT ou Markdown
  com o currículo na raiz. A troca de modo preserva respostas já salvas.

## Criar sem currículo

Uma pergunta por vez, com exemplo, aceitando "não sei":

Registre `intake choose` com `mode=create` e a rota escolhida. No atalho,
`start` devolve cada pergunta profissional em `question`. Confirme nome e
contato apenas para compor o documento, aproveitando o que já foi informado.
O preparo completo continua orientando os campos do perfil. Faça uma pergunta
por vez. Para formação, experiência, habilidades, idiomas e
informações extras, grave com `intake answer`, usando `field` e `text`.
O texto registra o fato dito pela pessoa; `null` registra uma escolha de pular.
"Nunca trabalhei" é uma resposta válida, não falta de resposta. Não exija
empresa, cargo ou datas nesse caso. Trabalho informal e projetos só entram
quando a pessoa os mencionar. Se ela não souber um ano, omita o ano.

Reaproveite informações dadas desde a primeira mensagem. Se a pessoa disser
"não tenho currículo e nunca trabalhei", registre a escolha de criar e a
resposta de experiência imediatamente, antes das próximas perguntas. Não
volte a perguntar se já trabalhou. Se pedir um currículo apenas com contato
e objetivo, registre os tópicos profissionais como pulados, sem perguntar cada
um de novo. Antes de interpretar "não sei", distinga dúvida sobre a pergunta
de uma escolha de deixar o dado em aberto: explique primeiro quando necessário.

`intake answer` já cria o fato confirmado e guarda o ponto de retomada. Não
duplique com `resume fact`. Use `intake status.fact_ids` ao montar o rascunho:
esses IDs contêm as respostas atuais. Corrigir uma resposta aposenta versões
que usavam o fato anterior, preservando os arquivos. Uma resposta idêntica não
duplica o fato. Para um fato extraído de arquivo, use o ID do original importado
como `source` e só marque confirmado depois da conferência. Nunca registre um
fato que a pessoa não disse. `./job resume facts` lista os fatos. Monte o
rascunho com `./job resume draft`, vinculando os IDs dos fatos ativos e confirmados.

Se a importação bloquear documentos ou credenciais, preserve o original e
oriente a pessoa a preparar uma cópia limpa ou colar o texto sem esses dados.
Não peça o conteúdo bloqueado, não copie o arquivo para contornar o filtro e
reaproveite as respostas já salvas.

Para corrigir um fato já registrado, mostre o texto atual e o novo, obtenha
confirmação e use `resume fact-replace` com `fact_id`, `text`, `source`,
`confirmed: true` e motivo opcional. Para retirar, use `resume fact-revoke`
com `fact_id`, origem `candidate:referência` e `confirmed: true`. O histórico
permanece; não use fatos `replaced` ou `revoked` em outro rascunho. Gere novamente
e peça nova aprovação de cada versão em `retired_versions`. As sugestões de
LinkedIn/GitHub dependentes voltam para revisão, assim como textos antigos
sem vínculo de fatos. Consulte `presence status` e prepare novos rascunhos
com os fatos atuais antes de pedir aprovação. `open_authorizations` exige conferir
o destino, pois a correção local não desfaz um possível envio anterior.

Se a pessoa pular todos os tópicos, prepare um currículo inicial com o nome,
contato e objetivo que ela confirmou no perfil. Registre esse objetivo como
fato `candidate:objetivo-confirmado`. Explique que poderá acrescentar formação
e experiências depois; nunca preencha uma seção com experiência inventada.

## Revisar e aprovar

- Siga [ATS.md](../../../docs/ATS.md): uma coluna, seções claras, termos da vaga
  sustentados por fatos e nenhum conteúdo invisível. Execute `resume check <id>`
  e confira o texto extraído dos formatos antes de mostrar a versão final.
  Corrija diferenças de leitura ou tabelas; explique que isso não é nota de ATS
  nem garantia de aprovação. Confira a prévia importada no portal antes de enviar.
- Mostre o rascunho em texto corrido e disponibilize links para os arquivos
  gerados, peça ajustes e refaça o rascunho. Cada
  rascunho tem PDF, DOCX e Markdown gerados localmente.
- Só após "está bom, pode aprovar" chame `./job resume approve <id>`. A versão vira
  `approved` com hash. Se o arquivo mudar depois, a aprovação deixa de valer.
- No atalho, `curriculum_complete` encerra o preparo do documento. Entregue os
  arquivos e pergunte apenas se a pessoa quer ajustar algo ou voltar ao menu.
  Não inicie o cadastro de candidatura automaticamente.
- Versões por especialidade são rascunhos separados, cada um com aprovação
  própria. Combine qual versão usar em cada área e guarde essa escolha como fato
  privado confirmado. Reaproveite a escolha nas vagas seguintes. Pergunte apenas
  quando houver mais de uma versão elegível sem uma escolha já combinada.

## Limites

- Não faça upload fora de uma candidatura autorizada.
- Não execute macro, script ou conteúdo ativo do arquivo.
- Não invente datas, cargos, cursos ou resultados.
