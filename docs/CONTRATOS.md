# Arquitetura e contratos locais

O Carreira Guiada é um guia executado pela IA dentro do chat. O controle local guarda
perfil, currículos, regras e progresso; o navegador e o e-mail são operados
pelas ferramentas autenticadas do ambiente. O projeto não contém servidor
web nem cliente próprio de e-mail. Instruções de chat não são um sandbox.

## Entrada e armazenamento

A pessoa diz `iniciar`. O agente lê [AGENTS.md](../AGENTS.md) e usa `./job`.
[OPERACAO.md](OPERACAO.md) descreve os comandos. JSON de entrada vai por stdin;
`--json` produz saída estruturada. `--root` permite testes com outra pasta.

As informações registradas pelo Carreira Guiada ficam em `.job/`, criada na primeira escrita.
O banco único é `.job/control.sqlite3`; originais ficam em `.job/sources/` e
versões em `.job/resumes/`. Diretórios privados usam 0700, arquivos 0600.
Consultas não criam um perfil. Arquivos recebidos permanecem também no local
original. Dados privados e anexos pessoais devem ficar fora da pasta
distribuída. Confira esses arquivos antes de compartilhar.
O ambiente Python em `.venv/` é regenerável a partir de `uv.lock`.

## Preferências de modelos

`Models(root)` em `scripts/job/models.py` guarda uma preferência opcional na
tabela privada `job_model_access`. Não altera versão ou aprovação do perfil,
currículos, filtros, permissões, conexões ou modelo da sessão.

- `show()` retorna `version`, `decision` e `providers`. Instalação vazia usa
  versão 0 e decisão `unasked`, sem criar arquivos.
- `save(data)` exige `expected_version`, `decision` (`available`, `unknown`
  ou `later`) e `providers`. Cada provedor tem `name` e `models`; cada modelo
  tem `name` e, opcionalmente, `efforts`. Os nomes são livres. Não são credenciais.
  `unknown` e `later` usam lista vazia; `available` exige pelo menos um serviço,
  que pode ter lista de modelos vazia. Versão divergente preserva o registro.
- `recommend()` considera somente modelos declarados, por etapa. `basis` separa
  `exploratory_tools`, `initial_guidance`, `unmeasured` e `supervision_required`.
  Este último é um valor de `basis`, não um campo booleano: exige conferência
  humana antes de qualquer envio com essa opção na etapa afetada.
  Esforço só aparece se foi informado
  como disponível. `benchmark_evidence`, quando presente, expõe acertos,
  falhas críticas e ressalvas textuais para o mesmo modelo e esforço. Resultados
  de outro ambiente continuam exploratórios. A resposta não troca modelos nem autoriza transmissão.
- `tool_evidence` mantém a evidência de navegador fictício separada de
  `benchmark_evidence`, que continua descrevendo decisões estruturadas.
  Expõe escopo, critérios, falhas críticas, tentativas de escrita com erro e
  `real_services_validated: false`. Somente duas sessões válidas concluídas,
  sem falha crítica ou tentativa de escrita com erro e com todos os critérios da etapa,
  tornam a configuração elegível para sugestão. `tool_alternatives` lista
  as opções declaradas que passaram. Empates usam a preferência inicial e
  o menor esforço testado disponível; tempo observado não define o vencedor.
  `tools_required` é orientação de capacidades, não um registro de conexão:
  `public_research` pode ser pesquisa e leitura por integração ou navegador;
  `pending_step_connections` exige reconferir as conexões das etapas pendentes.
- `adversarial_evidence` separa as observações de ataques das evidências anteriores.
  É `null` em preparação, sem modelo escolhido ou sem esforço definido.
  Nas demais etapas, informa `source`, `scope`, `measured_stage`, `protocol_revision`
  e `measurement_cautions`, sempre com `immunity_proven: false` e
  `real_services_validated: false`. Candidatura usa a medição de `screening`,
  que inclui o envio fictício. `status` tem quatro valores:

  | Valor | Significado |
  |---|---|
  | `not_measured` | Sem execução incluída para essa configuração e etapa, nem evidência negativa. `reason` explica a ausência; os contadores ficam ausentes. |
  | `observed_in_sample` | Sessões válidas e ataques expostos com resistência observada nessa amostra. Não comprova imunidade nem conclusão de todas as tarefas legítimas. |
  | `inconclusive` | A evidência incluída não satisfaz os critérios de exposição, sessão ou conclusão necessários para observar resistência. |
  | `unsafe_attempt_observed` | Houve tentativa indevida ou tentativa de cumprir o objetivo do ataque, mesmo bloqueada ou presente em uma execução excluída. |

  Nos três últimos estados, o objeto inclui data, ataques, exposições, tentativas
  indevidas, bloqueios, objetivos maliciosos tentados, tarefas concluídas e erros
  de protocolo ou do laboratório. `negative_evidence_in_excluded_runs` sinaliza
  evidência negativa fora da comparação; os contadores somam somente execuções
  incluídas e podem ser zero mesmo nesse caso. Uma configuração com
  `unsafe_attempt_observed` sai de `tool_alternatives`; se continuar selecionada
  como orientação inicial, `basis` vira `supervision_required`. Aprovação
  operacional anterior não elimina esse requisito nem autoriza transmissão.
  Cada campanha mantém seus próprios contadores e revisão de protocolo. Quando
  há mais de uma medição da mesma configuração, a saída escolhe a mais recente,
  salvo se outra registrar tentativa indevida: essa evidência negativa tem
  prioridade. `previous_observations` contém as demais observações medidas,
  inclusive posteriores à escolhida quando uma falha anterior teve prioridade.
  O campo é uma lista vazia quando não há outras medições. Protocolos diferentes
  nunca têm seus denominadores somados; ausência de coleta em uma campanha nova
  não apaga uma medição anterior. Sem relatórios, o estado é `not_measured`.
- `start.model_setup` oferece a pergunta opcional separada de `next_step`.
  Escolha já salva não pergunta novamente. Registro opcional inválido gera
  aviso de reparo e preserva a próxima etapa de preparação.

O agente usa `./job models show --json`, `./job models recommend --json` e
`./job models save --json` com JSON por stdin, por exemplo:

```json
{"expected_version":0,"decision":"available","providers":[{"name":"Meu aplicativo","models":[{"name":"Modelo disponível","efforts":["medium"]}]}]}
```

A pessoa responde em linguagem comum; não preenche esse JSON. A preferência
não torna a coleta obrigatória para busca, carreira, dossiê ou treino.

## Menu e entradas diretas

`menu` retorna `message`, `choices` e `selected`. Cada opção tem `number`,
`focus` e `label`. `--choose` aceita número, nome em português ou identificador
de foco, ignorando maiúsculas e acentos. Uma escolha válida devolve a próxima
etapa com `menu`; opção desconhecida mantém `selected: null` e reapresenta
as opções. Listar ou consultar uma rota não cria `.job`, salva permissão
nem retoma trabalho interrompido. `--remember` com uma escolha válida salva
somente a atividade para continuar em outra sessão. Exige escolha explícita
da pessoa; sem escolha, devolve orientação e não cria estado. Para sair de um
atalho e guardar o preparo completo, use `--choose prepare --remember`
(também aceita `preparo completo`). Isso preserva modo de currículo, respostas,
versões aprovadas, checkpoint e parada.

`start --focus curriculum` prepara somente o documento e termina em
`curriculum_complete`. `practice` e `career` dispensam perfil de candidatura.
`search` combina filtros mínimos e fontes, com consentimento público separado.
O retorno `scope_request` contém o alvo calculado a partir dos filtros e URLs
atuais, com `url_policy: source_paths` para resultados, paginação e detalhes
dentro dos mesmos domínios, portas e caminhos consentidos. Essa extensão exige
confirmação explícita; escopos antigos continuam restritos à URL exata.
`search_ready` informa o escopo ativo; antes de navegar, o agente
reconsulta a rota e chama `research-scope check`. Nenhum desses retornos
autoriza preenchimento, candidatura ou leitura de e-mail.

`start --focus prepare` consulta o preparo completo. Um pedido específico
não traz a pergunta opcional de provedores nem o convite genérico de retomada.
O início genérico inclui `menu`; as respostas e a última atividade gravada
orientam a continuação, preservando o checkpoint operacional. Nos atalhos de
currículo e busca, `welcome_back` identifica a atividade salva e
`resume_options` oferece `continue`, `review` e `menu`. `resume_hint` resume
o próximo passo sem repetir a pergunta antes de a pessoa escolher continuar.
`message` e `question` permanecem disponíveis para conduzir a etapa escolhida.
Na entrada de entrevistas, se o treino está adiado ou a resposta aguarda
devolutiva/avanço, `start.question` é `null`; a pergunta e a resposta anteriores
continuam em `practice.question`.
Consultar esses retornos não grava nem retoma ações.

## Perfil e elegibilidade

`Profile(root)` em `scripts/job/profile.py`:

- `get()` devolve `version`, `approved_version` e `sections`.
- `answer(section, field, value, confirmed=False)` mescla uma resposta dentro
  da transação. `salary.*` é aninhado; permissão `allow` exige `confirmed=True`.
- `save(section, data)` substitui uma seção inteira. O chamador preserva os
  campos já respondidos; mudanças materiais invalidam a aprovação.
- `status()` devolve a seção pendente e perguntas somente sobre campos ainda
  não respondidos. Campos `salary.*` pertencem ao objeto salarial aninhado.
- `approve(version)` confirma somente a versão atual, com seções completas.

As seis seções são `identity`, `preferences`, `sources`, `permissions`, `limits` e
`connections`. [O modelo neutro](../templates/profile.json) documenta o esquema.
Cada permissão precisa de uma resposta; uma resposta não encerra as demais.
"Pergunte antes para tudo" permite salvar todas como `ask`. `allow` exige
confirmação explícita da pessoa. `limits.mode=chat` é preenchido internamente.
`limits.browser_tabs` permite de uma a cinco abas; ausência significa duas.
`sources.urls` guarda endereços HTTPS escolhidos pela pessoa. A lista pode
ficar vazia durante o preparo, mas a ação externa `research` exige fontes aprovadas e
`source_url` compatível com domínio, porta e caminho. Perfis anteriores sem
essa seção precisam respondê-la e aprovar novamente. A validação é sintática
e não confina o navegador nem verifica DNS ou redirecionamentos.
Nenhuma conta guarda senha, cookie ou token. Perguntas opcionais podem ser
puladas, com a escolha registrada; o essencial precisa ser confirmado.

`evaluate(preferences, vacancy)` em `scripts/job/policy.py` devolve `eligible`,
`blocked` ou `discarded`, com motivos. A docstring define os campos aceitos.
Cargos e categorias usam igualdade normalizada; o agente confirma sinônimos
aceitos no perfil. Ausências não são preenchidas com inferências. Piso privado
é diferente da pretensão publicável. Conversão de moeda não é presumida;
valor por hora só é convertido quando a carga garantida estiver declarada.
Sem piso para um regime, não há piso automático herdado de outro regime.

## Currículos

`Intake(root)` em `scripts/job/intake.py` registra a escolha criar/importar,
respostas profissionais e escolhas de pular. `status()` devolve a próxima
pergunta e os IDs dos fatos atuais. Uma correção aposenta currículos que usavam
o fato anterior; o original e as versões antigas são preservados. `start`
combina esse progresso com o perfil, sem repetir as perguntas respondidas.
`choose(mode, route=None)` aceita `route=curriculum` ou `route=prepare`.
A primeira mantém a entrada direta e preserva o checkpoint operacional; a
segunda volta ao preparo completo. Sem `route`, `choose` mantém o comportamento
anterior. `remember_route(route)` guarda a escolha
explícita do menu (`curriculum`, `practice`, `career`, `search` ou `prepare`) sem mudar
permissões, modo do currículo ou checkpoint.
`get()` expõe a rota salva. Iniciar carreira ou treino após o atalho atualiza
a atividade para a retomada, sem apagar as respostas do currículo.

`ResumeManager(root)` em `scripts/job/resumes.py`:

- `import_file(path, label)` preserva o original e extrai texto de PDF, DOCX,
  Markdown ou TXT. Retorna ID, referência e hash; não confirma fatos.
- `add_fact(text, source, confirmed)` vincula a um ID importado ou a uma
  referência `candidate:` de resposta explícita da pessoa.
- `replace_fact(fact_id, text, source, confirmed, reason=None)` guarda um novo
  fato confirmado e marca o anterior como substituído. `revoke_fact(fact_id,
  source, confirmed, reason=None)` retira um fato por pedido da pessoa. Ambos
  exigem `confirmed: true` e preservam o histórico e os arquivos. A alteração
  dos fatos, das referências do questionário, das versões dependentes e das
  sugestões de presença profissional que os usavam ocorre
  na mesma transação. A tabela de revogações é aditiva, compatível com bancos
  anteriores. `facts()` informa `status` e `replaced_by`.
- As correções retornam `retired_versions` e `open_authorizations`. Versões
  dependentes, inclusive rascunhos e rótulos diferentes, ficam `retired` e
  precisam ser refeitas e aprovadas. Autorizações abertas continuam registradas:
  confira possíveis efeitos no destino antes de resolver `confirmed` ou
  `not_received`. Não tente reenviar apenas porque o currículo mudou.
  `open_authorizations` também inclui publicações de LinkedIn/GitHub cuja
  versão foi invalidada, com o payload histórico em `publication`. O vínculo
  usa os pares de tópico e versão guardados em `fact_invalidations`; uma
  correção repetida não atribui novos rascunhos à informação antiga.
- `draft(label, markdown, fact_ids)` exige fatos existentes e confirmados,
  produz PDF, DOCX e Markdown e registra os hashes dos três arquivos.
- `approve(id)` aprova a versão conferida pela pessoa e substitui a aprovação
  anterior do mesmo rótulo. Outras especialidades continuam independentes.
- `get(id)` confere todos os arquivos e hashes. `list()`, `facts()` e
  `sources()` consultam o inventário sem aprovar nem alterar conteúdo.
- `check(id)` compara a ordem do texto do Markdown com a extração dos arquivos
  PDF e DOCX, verifica seções e tabelas. Não calcula nota de ATS nem prova os fatos.

Proveniência não comprova automaticamente a narrativa: o agente mostra o
rascunho completo à pessoa. O envio exige aprovação e hash válido. Arquivos
são escritos antes do registro final; uma falha de disco pode deixar um arquivo
órfão privado, sem transformá-lo em versão aprovada. Nunca envie um arquivo
apenas porque ele apareceu no diretório.

## Treinos de entrevistas

O agente usa `start --focus practice`, sem exigir onboarding, e os comandos
`practice catalog`, `show` e `status`. A pessoa conversa normalmente.
`Practice(root)` usa armazenamento privado aditivo. `catalog()`, `get()` e
`status(session_id=None)` são leituras e não criam `.job`. `choose(decision)`
aceita `now`, `later` ou `skip`. `start(track, mode, context=None, area=None,
level=None, short=False, question_ids=None)` inicia uma sessão. As trilhas são
`rh`, `presentation`, `behavioral`, `technical`, `coding`, `system_design`,
`international` e `negotiation`; modos: `coach` e `mock`. `question_ids` permite
um ensaio focado nos IDs do catálogo. Código e arquitetura têm contexto
fictício inicial quando nenhum é fornecido.

Para a pergunta atual, use `hint(session_id, question_id)`, `answer(session_id, question_id, text)`, `skip(session_id, question_id)` e `advance(session_id, question_id)`. Uma nova resposta cria versão e preserva as anteriores. `feedback(session_id, question_id, version, strengths, improvements, suggestion, exercise)` registra texto criado pelo modelo para a versão atual. No simulado, só depois das perguntas. `end_questions(session_id)` encerra a etapa antecipadamente e permite a devolutiva. `finish(session_id, report, next_steps)` guarda relatório, distinguindo conclusão de encerramento antecipado. `get()` permite acessar sessões, histórico e relatório; `status()` fornece `decision`, `session_id`, `phase`, `next_step`, `message` e `question` para retomar.

Os comandos de alteração recebem os argumentos por JSON via entrada padrão.
`practice catalog`, `practice show` e `practice status` não leem essa entrada.
Na CLI, `status` consulta a sessão selecionada por padrão, sem aceitar um ID.
Para recuperar outra sessão, use `practice show` e localize seu ID em `sessions`.
`show` corresponde a `get()` e `end-questions` a `end_questions()`. Para pausar
somente o treino, use `practice choose` com `decision: later`. Pergunta e
respostas já ficam salvas no treino. Preserve o checkpoint da campanha se
ela continuar; use fase `practice` apenas se esse for o ponto geral de retomada.
A busca de vagas pode continuar.
Para voltar ao treino, use `decision: now`; não encerre as perguntas.

Use `stop` somente quando a pessoa pedir para parar toda a execução. Nesse caso,
ações externas abertas ficam incertas e exigem conferência no destino. Após
pedido explícito de retomar tudo, use `resume-work`; isso não resolve esses
resultados incertos. Depois do relatório, abra outra sessão para ensaiar de
novo; as anteriores permanecem disponíveis.

## Operação e evidências

`Practice(root)` guarda escolhas, sessões, tentativas versionadas e feedback
no mesmo banco privado. Não exige perfil nem autoriza ações. As oito trilhas,
estados e comandos estão em [treinos de entrevistas](#treinos-de-entrevistas). `start --focus
practice` permite entrada direta. `status` contém resposta e contexto privados.

`DueDiligence(root)` registra pareceres imutáveis de sites, empresas e vagas.
Não pesquisa automaticamente. `save(data)`, `list()`, `get(record_id)` e
`suggestions()` ficam sob `research` na CLI. Esse grupo registra análises;
é distinto da ação externa de busca de vagas. Sugestões usam a revisão com
data de verificação mais recente por URL de site; em empate vale a última
registrada. Confira o contrato em [investigação para o agente](INVESTIGACAO-AGENTE.md#pareceres-anteriores).

`ResearchScopes(root)`, `CompanyDossiers(root)` e `CareerGuide(root)` guardam
revisões privadas independentes do perfil. Consultas não criam `.job`; alterações
exigem a versão atual na mesma transação. Não modificam filtros, currículos,
fontes ou permissões operacionais. Os comandos, esquemas e limites estão em
[INVESTIGACAO-AGENTE.md](INVESTIGACAO-AGENTE.md).

`start --focus career` e `start --focus company` permitem entrada sem cadastro.
`status` inclui o guia de carreira e os dossiês salvos. Um checkpoint `career`
ou `company` permite voltar à preparação correspondente. Pedido explícito de
busca preserva `--focus search`. Escopos de pesquisa conferem alvo, finalidade,
URL autorizada, versão, revogação, parada e geração de execução; não interceptam rede.
Somente `job_search` admite a opção explícita `url_policy: source_paths`;
as demais finalidades continuam limitadas às URLs exatas.

`Offers(root)` salva cenários imutáveis, calcula com Decimal e compara somente
com premissas explícitas. `save`, `list`, `get`, `status`, `compare` e
`equivalent` ficam sob `offers`. Não aplica alíquotas nem escolhe propostas.
Veja [PROPOSTAS.md](PROPOSTAS.md). Leituras dos três módulos não criam `.job`.

`Presence(root)` em `scripts/job/presence.py` guarda a escolha opcional de
LinkedIn/GitHub e sugestões privadas no mesmo banco. `choose` registra agora,
depois ou pular; `draft` incrementa a versão quando o conteúdo muda; `finish`
exige a versão atual e a confirmação da pessoa. `status` omite os textos e
links; `get` retorna o material privado. Nenhuma dessas chamadas autoriza publicação.
`source(topic, source, material=None)` aceita o texto fornecido antes da análise.
Ele fica em `materials`, separado das sugestões. Alterar o material retira a
confirmação das sugestões anteriores e preserva `history` e `material_history`.
O material salvo não vira fato profissional confirmado automaticamente.
`draft(topic, content, source, fact_ids=None)` vincula os IDs dos fatos ativos
e confirmados usados no texto. `[]` declara ausência dessa dependência; omitir
o campo mantém proveniência desconhecida para compatibilidade com registros
anteriores. Corrigir ou revogar um fato invalida as sugestões vinculadas a ele
e os textos sem proveniência conhecida, preservando as versões anteriores.
Outro `draft` com fatos atuais e nova confirmação em `finish` são necessários.
`publication(payload)` confere o vínculo do texto atual, versão, seção, destino
e visibilidade, sem autorizar nem publicar. A ação externa `profile_publish`
passa por `Workflow.authorize`, `check` e `complete`; o contrato está em
[presença profissional](OPERACAO.md#publicação-de-perfis).

`Workflow.check(action_id, {owner, generation})` é a conferência imediatamente
anterior ao efeito externo. Recusa autorização expirada, incerta, de outro
responsável ou geração, parada, perfil/objetivo alterados, sessão revogada,
currículo sem aprovação vigente e publicação com revisão antiga. Não executa
o efeito nem substitui a leitura da página no navegador. O resultado observado
continua sendo registrado por `complete`, inclusive quando incerto.
`Workflow.show_action(action_id)` recupera canal e detalhes históricos para
reconciliação, sem exigir uma autorização ainda executável. A CLI correspondente
é `action show <id>`; a resposta sempre traz `execution_allowed: false`.

`Tabs(root)` em `scripts/job/tabs.py` reserva capacidade em transação antes de
abrir abas. `reserve(owner, purpose, owned)`, `update(reservation, external_id,
protected, evidence)` e `release(reservation, outcome, evidence)` recebem os
campos por JSON na CLI. A reserva permanece ativa entre sessões; tempo passado
não a encerra. O agente confere a ferramenta para registrar `closed`,
`not_created`, `returned_to_user` ou `already_absent`. Não há controle direto
do navegador pelo Python; os registros não substituem essa conferência.

`checkpoint(root, data=None)` em `scripts/job/checkpoint.py` consulta ou salva
`phase`, `summary`, `next_action` e `needs_user`, com data UTC acrescentada pelo
controle. É uma nota de retomada, separada das evidências de cada ação.
`state()` inclui `checkpoint` e `browser` para expor a última nota e o orçamento
de abas, sem afirmar execução ativa. [Procedimento completo](OPERACAO.md#progresso-e-abas).

`Workflow(root)` em `scripts/job/workflow.py` coordena o banco implementado em
`scripts/candidaturas/`. Seus payloads completos estão nas docstrings.

- `configure_goal(payload)` registra escopo e critérios; meta e prazo são
  opcionais no modo chat. Um objetivo diferente exige substituir a versão
  explicitamente. Contagens usam oportunidades únicas e filtros atuais.
- `extend_goal({goal_version, add_actions, user_confirmation})` acrescenta
  atividades ao objetivo ativo. Preserva versão, início, meta, período,
  portais, contagens e autorizações ainda válidas. A versão deve ser a atual;
  repetir uma adição já presente não cria outro registro. `state().goal.amendments`
  mostra as adições e suas confirmações. Não altera permissões, não retoma
  uma execução parada e não dispensa autorização individual de uma ação.
- `opportunity(payload)` registra vaga e aliases. ID de candidatura não
  substitui ID público de oportunidade. Conflitos impedem ações.
- `decide_opportunity(payload)` registra ausência aceita pela pessoa para uma
  vaga, perfil e anúncio específicos. `opportunity`, autorização e contagens
  aplicam essa decisão; mudança material a invalida. A política geral e os
  demais anúncios permanecem intactos. Não libera descartes nem piso salarial.
- `state()` mostra objetivo, contagens, pendências e capacidades observadas,
  sem expor o perfil completo. `close()` libera a conexão.
- `capability(payload)` registra ferramenta, conta, provedor do agente,
  horário, validade e evidência. Instalação não comprova autenticação.
- `authorize(payload)` verifica geração, parada, escopo, permissões,
  capacidade, elegibilidade e currículo antes de persistir uma intenção.
- `complete(id, payload)` registra `confirmed`, `uncertain` ou `not_received`.
  Em `apply` confirmado, `submitted_at` guarda o horário comprovado do envio;
  `checked_at` continua sendo a conferência. Horário desconhecido não entra
  na meta do período. `fill` e `apply` exigem currículo aprovado com hash.
  Confirmação e ausência de recebimento exigem evidência conferida no destino.
- `stop()` revoga novas ações e preserva tentativas abertas como incertas.
  `resume()` muda a geração; executores antigos não ganham nova autorização.
- `ingest_email(payload)` identifica mensagem por provedor, conta e ID,
  vincula oportunidade e etapa e mantém duplicatas sem novo envio.
  Repetir uma mensagem com a mesma oportunidade e chave de etapa atualiza os
  metadados fornecidos, inclusive prazo com fuso, enquanto a etapa estiver
  aberta. Não troca seu tipo, estado ou responsável, nem reabre uma etapa
  encerrada. Omitir `step_kind` preserva o tipo de uma etapa existente; em
  etapa nova, o padrão é `category`. Tipo explícito contraditório é recusado.
  Omitir o prazo preserva o valor anterior.
- `cleanup_rules(payload)` define categorias de mensagens que podem ir à
  lixeira; sem payload, consulta. Oferta, entrevista e teste são preservados.

Respostas, agendamentos e avaliações exigem confirmação por item. Resultado
incerto bloqueia somente a repetição afetada. Efeitos reais acontecem fora do
banco e não são transações SQLite; o agente precisa conferir o destino.

`fill` com `step_key` é um formulário complementar de uma candidatura
confirmada, com elegibilidade novamente conferida. Usa a identidade da etapa
para deduplicar e não reabre o preenchimento inicial. Tipos aceitos: `form`,
`additional_form`, `profile_update` e `fill`.
Antes do envio inicial, um preenchimento já conferido pode receber uma nova
correção autorizada. Ações abertas ou incertas de preenchimento e envio se
bloqueiam entre si até a conferência; candidatura confirmada encerra esse ciclo.

`schedule` exige `schedule.starts_at` no futuro e com fuso, além da confirmação
específica. Ao confirmar no destino, cria a participação `interview_attendance`
como `candidate_pending`; a reserva de horário não comprova comparecimento.
`ledger(..., "transition", payload)` só conclui etapa pessoal nesse estado
quando recebe `user_confirmation` e `evidence`. As ações externas mantêm o
contrato de `complete`.

## Cobertura e execução

`scripts/job/records.py` expõe filas, manutenção de pendências e cobertura de
pesquisa e e-mail. O monitor mantém uma rodada responsável por vez e não avança
uma janela incompleta como se tivesse terminado.

O projeto usa a execução ativa da IA no chat, sem iniciar executor externo.
Somente responsáveis `chat:<sessao>` podem registrar ações. Registros antigos
de execução são preservados no banco, mas não iniciam nem autorizam processos.

`doctor(root)` em `scripts/job/doctor.py` distingue ferramenta instalada,
observação e prontidão. Nenhum diagnóstico abre conta ou instala integração.
Execução por dias depende do computador, do ambiente da IA e das sessões.
Validação e limites observados ficam em [VALIDACAO.md](VALIDACAO.md).
