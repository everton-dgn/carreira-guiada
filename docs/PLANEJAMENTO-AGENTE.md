# Protocolo de plano e evolução pessoal

Este documento é para a IA que conduz o chat. Para a pessoa, use
[Meu plano](MEU-PLANO.md) e [Minha evolução](MINHA-EVOLUCAO.md).

## Condução

1. Entre pelo pedido específico ou por `menu --choose plano --remember`.
   "Minha evolução" usa `menu --choose evolução --remember`. Uma consulta de
   opções não autoriza escolher nem ativar acompanhamento.
2. Leia `plan show` ou `progress show`. Faça só a pergunta pertinente. Use
   `career get`, `practice show` e o plano existente para reaproveitar fatos
   confirmados; não copie sugestões como se fossem decisões da pessoa.
3. Para o plano, combine direção, ciclo e primeira ação. Disponibilidade
   desconhecida fica `null`; não converta texto livre em horas sem conferir.
   Datas são opcionais. Cada `period` identifica a segunda-feira de uma semana.
4. Proponha uma ação concreta, uma finalidade e um critério observável. Ofereça
   um passo menor e uma condição "se acontecer X, faço Y" quando forem úteis.
   Pergunte uma coisa por vez. Não transforme o planejamento em questionário.
5. Confira a soma da semana antes de apresentar o plano como viável. Ações
   sem data e estimativas incompletas permanecem explícitas. Redução de tempo
   revisa ações futuras e preserva as concluídas.
6. Salve só o combinado, releia e confirme. Abra a atividade pelo menu apenas
   quando a pessoa escolher fazê-la. O plano não concede nenhuma permissão
   externa, não aprova perfil e não retoma uma campanha parada.

## Proveniência e feedback

Use `practice answer` com `attempt_id` estável, `origin: person` e a
`user_confirmation` real quando a pessoa tiver ensaiado a resposta. Exemplos
gerados pela IA usam `origin: agent`. Registros antigos sem origem permanecem
`unknown`. Uma nova tentativa deliberada recebe outro ID; repetir uma gravação
usa o mesmo ID e conteúdo. Não registre "não sei" ou pergunta pulada como treino.

Ofereça acompanhamento depois de uma prática pertinente, sem insistir após a
recusa. `progress configure` exige escolha explícita: `off`, `tracking`,
`achievements` ou `points`. Não ative pontos ao criar um plano.

Um evento de prática referencia a tentativa exata. Relato de estudo usa
`user_report`, identificado como relato. Nunca deduza duração pela diferença
entre mensagens, por tempo de ferramenta ou por sessão aberta. Registre a
duração informada ou `null`. Não conceda pontos por automação ou envio.

Um marco `participation` registra participação. `learning` exige trechos fiéis
de resposta e feedback. `evidence.basis: observation` descreve apenas aquela
tentativa. Uma afirmação de melhora usa `comparison`, com as duas tentativas
da mesma pergunta, seus trechos e o mesmo critério discutido. O código verifica
identidade, ordem e presença dos trechos; não comprova a interpretação semântica.
A IA deve explicar a avaliação, aceitar contestação e evitar diagnóstico,
julgamento de personalidade ou promessa de contratação.

Mostre um ponto forte específico, uma prioridade e um exercício pequeno.
Uma reformulação feita pela IA ou uma nova versão por si só não demonstra
aprendizagem. Se o critério não foi atendido, diga o que falta com evidência;
evite inventar uma conquista para animar a pessoa. Trechos isolados também não
justificam uma conclusão mais ampla que a resposta observada.

## Retomada e apresentação

Leia o estado antes de retomar. Pausa longa não retira pontos, adiciona dívidas
ou muda datas automaticamente. Ofereça continuar, diminuir o passo ou rever
a direção. `plan pause` e `plan resume` afetam somente o plano; `stop` mantém
a semântica de parada da campanha. Pedido ambíguo de parar exige conferir o
escopo, preservando imediatamente qualquer execução externa.

No terminal, `--plain` desliga a decoração naquela consulta. Para guardar a
preferência, use `progress configure` com o modo já escolhido e
`appearance: plain`; isso não deve ligar o acompanhamento. `NO_COLOR` remove
cores. O parâmetro `motion` é guardado, mas esta versão não produz movimento.
No chat, não cole ANSI: use o conteúdo de `--json` e uma apresentação curta.

Versão desatualizada exige reler e reconciliar. Nunca sobrescreva uma revisão
concorrente, crie um novo evento para contornar deduplicação ou anuncie
salvamento após erro. Dados ficam em tabelas adicionais do banco privado;
consultas não criam banco nem alteram permissões.

## Contrato dos comandos

A pessoa conversa; a IA executa estes comandos. Mutações recebem um objeto
JSON por stdin. `--root` seleciona a instalação privada e `--json` devolve os
dados sem decoração. Valores opcionais desconhecidos usam `null` quando indicado.

### Plano

`plan show` e `plan status` não leem stdin. `plan get` recebe `{}` para o plano
atual, ou `id` e `version` opcional. `plan history` recebe `id`.

`plan start` recebe `{}` ou `direction` (texto ou `null`), `weekly_minutes`
(inteiro de 0 a 10080 ou `null`), `cycle` e `basis`. Reutiliza o plano não
arquivado existente; mudanças nele usam `update`. `cycle` tem `title` e
`review_on` opcional, uma data `AAAA-MM-DD`. `basis` é uma lista de referências:

- Carreira: `kind: career`, `id` e `version` existentes.
- Treino: `kind: practice`, `session_id`, `question_id` e `version` da tentativa.

Todas as outras mutações recebem `id` e `expected_version`, além destes campos:

| Ação | Campos |
|---|---|
| `update` | Campos de `start` que a pessoa quer alterar. |
| `action` | `action` com `id`, `activity`, `title`, `reason`, `criterion`, `estimated_minutes` e `period`; opcionais `smaller_step`, `if_then`, `source`. |
| `transition` | `action_id`, `state` e `evidence` quando concluída. |
| `review` | `observation`, `next_step` e `decision`: `continue`, `adjust` ou `finish`. Registra a reflexão; arquivar é uma decisão separada. |
| `pause`, `resume`, `archive` | Nenhum campo adicional. |

`estimated_minutes` aceita inteiro de 0 a 10080 ou `null`. `period` aceita a
segunda-feira de uma semana ou `null`. `source` segue os formatos de referência
acima. `activity` aceita `prepare`, `curriculum`, `practice`, `career`,
`presence`, `company`, `search`, `offers`, `models` ou `study`. Identifica o
recurso a abrir, sem executá-lo; `study` é estudo conduzido no chat. Uma ação já
iniciada precisa voltar a `planned` antes de editar seu conteúdo.

Estados da ação: `planned`, `active`, `completed`, `deferred`, `cancelled`.
`evidence` tem `kind: user_report` ou `source`, `description` e `criterion`;
o tipo `source` exige também a referência `source`. `criterion` precisa ser
igual ao critério salvo da ação. Seu cumprimento é conferido
pelo agente com a pessoa; o código não avalia se uma frase prova a conclusão.
Máximo de 50 ações por plano. Um plano arquivado preserva o histórico e permite
criar outro com `start`.

`show` expõe `view: plan`, `exists`, `id`, `version`, `state`, `direction`,
`cycle`, `actions`, `next_action`, `budget`, `basis`, `message` e `question`.
`budget.periods` separa soma, folga e excesso por semana; estimativa desconhecida
produz `null`. Ações concluídas deixam o orçamento futuro. `basis[].changed`
indica fonte diferente, inclusive feedback editado na mesma tentativa.

### Evolução

`progress show`, `status`, `get` e `history` não leem stdin. `get` expõe o
registro privado completo; `show` e `status` exibem a projeção. Todas as
mutações recebem `expected_version`, começando em 0.

| Ação | Campos adicionais |
|---|---|
| `configure` | `mode`; opcionais `appearance: auto/plain` e `motion` booleano. |
| `record` | `event_id`, `activity`, `source`, `user_confirmation`, `reported_minutes`, `occurred_at`; `note` opcional. |
| `correct` | `event_id`, `reason` e ao menos um entre `reported_minutes` e `revoked` booleano. |
| `milestone` | `milestone_id`, `kind: participation/learning`, `title`, `criterion`, `event_ids`, `assessment`; `evidence` obrigatório para `learning`. |
| `contest` | `milestone_id` e `reason`. Sinaliza revisão e preserva a avaliação. |

`reported_minutes` é inteiro de 0 a 1440 ou `null`. `occurred_at` é data e hora
ISO com fuso, informada ou confirmada pela pessoa. `source` usa a referência
de treino acima ou `{kind: user_report, description: texto}`. Um ID repetido
com conteúdo idêntico é idempotente; conteúdo diferente ou outro evento para
a mesma tentativa é rejeitado. Revogação recalcula indicadores sem apagar
o registro original.

Um marco `learning` exige `evidence` com `basis: observation/comparison`,
`event_id`, `answer_excerpt` e `feedback_excerpt`. Comparação exige ainda
`previous_event_id`, `previous_answer_excerpt` e `previous_feedback_excerpt`.
Os eventos precisam constar em `event_ids`, estar ativos e referenciar
tentativas pessoais da mesma pergunta, em ordem. Alterações de fonte e
contestações sinalizam `needs_review`; não apagam versões antigas.

`show` expõe `view: progress`, `mode`, `version`, `practice_count`,
`reported_minutes`, `unreported_time_count`, `points`, `milestones` e
`evidence_warnings`, além da próxima pergunta. `off` oculta indicadores;
`tracking` oculta marcos; apenas `points` mostra pontos. A soma de duração
exclui valores desconhecidos e informa quantos registros não têm duração.
