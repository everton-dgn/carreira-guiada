# Operação técnica para o agente

Este documento é para o agente. Descreve o ciclo operacional, os comandos da
entrada técnica `./job` definidos em [CONTRATOS.md](CONTRATOS.md) e os limites
reais de execução. A pessoa nunca executa nada disto.

## Princípios

- A única fonte de filtros, contatos, permissões e limites é o perfil
  aprovado em `.job/control.sqlite3`. Nenhuma regra fixa de cargo, salário,
  idioma, contrato ou empresa existe no repositório.
- Toda mutação passa pela entrada técnica. Dados pessoais e payloads vão por
  stdin em JSON, nunca na linha de comando. Use `--json` para saída
  estruturada; `start`, `status` e `doctor` são legíveis por padrão.
- O diretório `.job/` nasce no primeiro comando de escrita, com permissões
  restritas. Comandos de consulta em instalação nova informam estado vazio.
- Comando que falha é erro a diagnosticar com `doctor` e a traduzir para a
  pessoa em uma frase com próxima ação. Não é motivo para improvisar outro
  caminho de gravação.

## Instalação e diagnóstico

`./job doctor` informa Python, `uv`, perfil, currículo e
observações de sessão. Disponibilidade de ferramenta não comprova
autenticação. `doctor` não abre navegador, não lê credenciais, não instala.

Se faltar `uv` ou Python, o agente conduz a instalação no espaço da pessoa:
explica em uma frase, pede a permissão necessária, executa o instalador
oficial da ferramenta sem privilégios de administrador, confere com `doctor` e
segue. As dependências de currículo (`pypdf`, `python-docx`, `reportlab`) são
resolvidas por `uv` a partir de `pyproject.toml` e `uv.lock`; nada é instalado
globalmente. Se a instalação falhar, informe o erro em uma frase e a próxima
tentativa concreta; não encerre o turno delegando o problema à pessoa.

## Atualização de uma instalação usada

O candidato encontra o pedido em linguagem comum no
[guia de atualização](GUIA.md#atualizar-sem-perder-o-progresso). Este procedimento
é manual e assistido; não existe comando de atualização ou migração automática.

1. Identifique a pasta em uso, a versão instalada e a versão pretendida. Leia
   este procedimento da versão nova e suas notas antes de propor alterações;
   não presuma que a instalação antiga já contém estas instruções. Explique o
   que muda e use a autorização da pessoa para aquele escopo.
2. Pare a campanha e confira que nenhuma outra sessão ou processo está
   gravando no armazenamento. Uma ordem de parada não encerra outras sessões
   automaticamente. Não copie um banco em uso nem encerre processos alheios.
3. Prepare uma cópia local completa em destino privado fora da pasta alterada,
   incluindo arquivos ocultos, anexos e permissões. Preserve `.job/` inteira,
   não apenas `control.sqlite3`; não exclua arquivos auxiliares do SQLite.
   Confira a cópia antes de substituir qualquer arquivo. Não imprima dados
   privados nem use um destino de nuvem por conta própria.
4. Confira como a instalação foi obtida. Em checkout Git, inspecione mudanças
   locais e siga o fluxo do repositório sem descartar edições. Para ZIP, mantenha
   as duas pastas e confira o conteúdo antes de transferir dados privados para
   a instalação nova. Não mescle dois históricos preenchidos nem substitua
   uma área privada já existente. Incompatibilidade de versão exige diagnóstico.
5. Use as dependências do lock da versão escolhida e confira `doctor`,
   `start --json` e `status --json` sem iniciar ações externas. Compare perfil,
   currículos íntegros, contagens e pendências com o estado anterior. Uma tela
   de primeiro uso inesperada é motivo para investigar a pasta, não para apagar
   o banco ou cadastrar a pessoa de novo.
6. Após a conferência, identifique a única instalação ativa para a pessoa e
   para as sessões que continuarão o trabalho. Em atualização por ZIP, a nova
   pasta passa a ser a instalação ativa; a antiga permanece somente como cópia
   de segurança e não deve retomar campanhas. Bancos copiados não sincronizam
   entre si e podem permitir candidaturas repetidas se usados separadamente.
   Relate a versão conferida, o progresso preservado e o local privado da cópia.
   Retome somente quando a pessoa pedir. Se houver falha, preserve original e
   cópia sem tentar downgrade sobre dados já modificados.

## Comandos da entrada técnica

| Comando | Uso no fluxo |
|---|---|
| `menu` | Lista quatro atividades sem criar perfil ou retomar uma parada. `--choose` aceita número ou nome, como `1`, `currículo`, `entrevistas`, `carreira` e `vagas`; opção desconhecida reapresenta a lista. Acrescente `--remember` somente após escolha explícita para guardar a atividade entre sessões, sem retomar nem autorizar ações. |
| `start` | Descoberta de estado para `iniciar`: `message`, `question`, `next_step` (`curriculum_input`, `curriculum_intake`, seção do perfil, `sources`, `profile_approval`, `resume_approval`, `professional_presence`, `interview_preparation`, `career_guidance`, `company_dossier`, `execution_readiness`), `approved_resumes`, `welcome_back` e `resume_options`. Nunca inicia envios. |
| `status` | Estado privado: objetivo, contagens, pendências, notas de retomada e abas. Pode conter nomes e detalhes das vagas; compartilhe somente no chat confiável da pessoa. |
| `context` | Contexto privado para o agente responsável conduzir a etapa. Não repetir na conversa além do necessário. |
| `doctor` | Diagnóstico do ambiente. |
| `checkpoint show` e `save` | Último progresso comprovado e próxima ação, persistidos entre sessões. Payload: `phase`, `summary`, `next_action`, `needs_user`; veja [progresso e abas](#progresso-e-abas). |
| `tabs status`, `reserve`, `update`, `release` | Reserva compartilhada antes da abertura, proteção de formulários e encerramento com evidência. Padrão de duas abas; veja [progresso e abas](#progresso-e-abas). |
| `presence status`, `show`, `choose`, `source`, `draft`, `finish` | Revisão opcional de LinkedIn/GitHub. `source` recebe `topic`, `source` e, opcionalmente, `material` para salvar texto recebido antes da análise. Material e sugestões ficam separados e privados. Não autoriza publicação; veja a [skill](../.agents/skills/presenca/SKILL.md). |
| `practice catalog`, `show`, `status`, `choose`, `start`, `hint`, `answer`, `skip`, `feedback`, `advance`, `end-questions`, `finish` | Treino privado e opcional. `start --focus practice` entra direto; no onboarding aparece `interview_preparation`. Contratos e pausa em [treinos de entrevistas](CONTRATOS.md#treinos-de-entrevistas). |
| `research save`, `list`, `get`, `suggestions` | Mantém os pareceres anteriores; não navega. `get` recebe `record_id`; contrato em [investigação](INVESTIGACAO-AGENTE.md#pareceres-anteriores). Não confundir com a ação externa `research` em `action authorize`. |
| `research-scope grant`, `get`, `list`, `check`, `revoke` | Autoriza e confere pesquisa pública para um alvo e pergunta. Não altera fontes de candidatura nem intercepta rede. [Contrato](INVESTIGACAO-AGENTE.md#autorizar-uma-investigação-específica). |
| `company create`, `get`, `list`, `revise`, `summary` | Dossiê versionado de empresa, com evidências por tema, salários, contradições e perguntas. `start --focus company` dispensa cadastro. [Contrato](INVESTIGACAO-AGENTE.md#dossiê-de-empresa). |
| `career start`, `get`, `status`, `answer`, `propose`, `choose`, `experiment`, `reflect`, `pause`, `resume` | Guia opcional, privado e versionado. `start --focus career` consulta sem criar sessão. [Contrato](INVESTIGACAO-AGENTE.md#guia-de-carreira). |
| `offers save`, `list`, `get`, `status`, `compare`, `equivalent` | `get` recebe `offer_id`; `compare` recebe `ids`; `equivalent` recebe `base_id` e `target_id`. Comparações aceitam `base_currency` e `rates`; esquema completo em [PROPOSTAS.md](PROPOSTAS.md). |
| `profile show` | Perfil atual com versão e `approved_version`. |
| `profile status` | `next_section`, `missing`, `approved`, `version`, `questions` com exemplos. Guia o onboarding. |
| `profile answer <seção>` | Recebe `field`, `value` e, para autorização explícita, `confirmed: true`. Mescla uma resposta sem apagar as anteriores. Aceita `salary.floors` e outros campos salariais. |
| `profile save <seção>` | Grava uma seção (`identity`, `preferences`, `sources`, `permissions`, `limits`, `connections`), JSON por stdin. Mudança material invalida aprovação. |
| `profile approve --version <n>` | Aprova a versão exibida com campos necessários preenchidos; só com "sim" explícito da pessoa. |
| `intake choose` | Registra `mode: create` ou `mode: import`. `route: curriculum` mantém o atalho; `route: prepare` seleciona o preparo completo. A rota direta preserva o checkpoint operacional. |
| `intake answer` | Registra `field` e `text` da pergunta profissional. `null` é uma escolha explícita de pular. Cria o fato confirmado uma única vez. |
| `intake show` e `intake status` | Respostas privadas e próxima pergunta do currículo. `fact_ids` contém somente as respostas atuais para o rascunho. |
| `evaluate` | Payload da vaga, direto ou dentro de `vacancy`. Usa as preferências do perfil salvo; devolve `eligible`, `blocked` ou `discarded` com motivos. |
| `resume import` | Recebe `file` e `label` por JSON via stdin. Importa PDF ou DOCX, preserva original, extrai texto e devolve id e sha256. As flags antigas permanecem por compatibilidade; prefira stdin para não expor o caminho. |
| `resume sources` | Originais importados. |
| `resume fact` | Registra fato com origem e confirmação; nunca inventado. |
| `resume facts` | Fatos e histórico, com `status: active`, `replaced` ou `revoked` e `replaced_by`. Use somente fatos ativos e confirmados em novos rascunhos. |
| `resume fact-replace` | JSON com `fact_id`, `text`, `source`, `confirmed: true` e `reason` opcional. Substitui o fato sem apagar o histórico e aposenta todas as versões dependentes. |
| `resume fact-revoke` | JSON com `fact_id`, `source: candidate:referência`, `confirmed: true` e `reason` opcional. Retira o fato de novos currículos e aposenta versões dependentes. |
| `resume draft` | Rascunho com MD, PDF e DOCX a partir de fatos confirmados. |
| `resume approve <id>` | Versão `approved` após conferência de arquivos e hash. |
| `resume list` | Versões com id, rótulo, status, sha256 e caminhos. |
| `resume show <id>` | Confere os hashes de todos os formatos antes de usar uma versão. |
| `resume check <id>` | Compara o texto extraído dos arquivos gerados, verifica seções e tabelas. Não calcula pontuação de ATS. |
| `goal` | Objetivo persistido com versão e critérios; não sobrescreve objetivo ativo incompatível. |
| `goal-extend` | Acrescenta `add_actions` ao objetivo indicado em `goal_version`, com `user_confirmation`. Preserva início, meta e contagens; não concede permissões nem retoma uma parada. |
| `opportunity` | Registro de oportunidade com chave e aliases; distinto de candidatura. |
| `decision` | `opportunity_id`, `reasons` atuais e `user_confirmation`; aceita ausência permitida só nessa vaga, sem alterar os filtros gerais. |
| `capability` | Observação de capacidade (navegador, e-mail) com provedor, apelido, horário, estado, evidência. |
| `action authorize` | Intenção persistida antes de efeito externo; devolve ID; bloqueia após parada, duplicata e incerteza pendente. |
| `action check <id>` | Imediatamente antes do efeito, recebe `owner` e `generation` por stdin. Confere validade, responsável, parada, perfil, objetivo, sessão e currículo; em publicação, também o texto e a versão revisada. Erro impede executar; uma autorização antiga não substitui esta conferência. |
| `action show <id>` | Leitura privada da intenção histórica, canal e detalhes, inclusive após parada ou incerteza. Não recebe payload nem autoriza execução. Use para conferir a tentativa no destino durante a retomada. |
| `action complete <id>` | `confirmed`, `uncertain` ou `not_received` com evidência do destino. `checked_at` é a conferência; `submitted_at` é o envio comprovado de `apply`, com fuso. Sem este último, não conta na meta do período. |
| `email` | Ingestão de mensagem ou etapa vinculada; limpeza individual exige ID, conta, ausência de etapa pendente e categoria autorizada. |
| `stop` | Parada persistida; revoga novas ações. |
| `resume-work` | Nova geração; revalida estado; não resolve incerteza. |
| `jobs` e `steps` | Oportunidades e etapas já registradas. |
| `step` | Cria ou atualiza etapa local, com o payload de `Store.upsert_step`. |
| `transition` | JSON com `id`, `state` e `evidence`; registra pendência, bloqueio ou cancelamento. Para concluir uma etapa `candidate_pending`, exige também `user_confirmation` com o relato da pessoa. Efeitos externos continuam por `action complete`. |
| `coverage show` e `coverage save` | Consulta e registra cobertura de pesquisa, conforme `scripts/job/records.py`. |
| `mail-coverage show`, `begin`, `account`, `finish` | Janela e posse da rodada de consulta de e-mail, no mesmo banco. |
| `cleanup-rules show` e `cleanup-rules save` | Categorias explicitamente autorizadas para lixeira, com `categories` e `user_confirmation`. |

Esquemas de payload: `templates/profile.json` para o perfil,
`scripts/job/policy.py` para a vaga, docstrings de `scripts/job/workflow.py`
e `scripts/job/resumes.py` para os demais. Se `uv` faltar, o atalho `./job`
imprime a instrução para pedir a instalação à IA; o agente então conduz a
instalação conforme a seção anterior.

No primeiro acesso, `start` inclui o menu. `menu --choose` e `start --focus`
consultam diretamente `curriculum`, `practice`, `career` ou `search`.
Currículo concluído devolve `curriculum_complete`, sem exigir cadastro completo.
A busca pública pede cargo, modalidade e fontes e devolve
`search_scope_confirmation`, `search_ready` ou `search_paused`. Confira a
[autorização delimitada](INVESTIGACAO-AGENTE.md#busca-pública-pelo-menu) antes de
consultar uma fonte. Uma campanha já autorizada preserva `execution_readiness`.
Para o preparo completo explícito, use `start --focus prepare`. `connections.accounts` guarda as contas de e-mail autorizadas.
O canal do navegador usa um alias de sessão observado em `capability`, inclusive
`public` para páginas que não exigem login. Isso não concede permissões da ação.

Os registros Markdown em `templates/` são formatos portáteis vazios. No uso
local, o banco é a fonte operacional; não mantenha tabelas paralelas à mão.
As APIs de `scripts.candidaturas` sustentam o controle atual. Sua CLI legada,
`scripts.candidaturas.cli`, serve para importar registros
portáteis de outro candidato, somente a pedido dele. Seu banco padrão também
fica em `.job/`; não use essa entrada para contornar as autorizações do fluxo.
Mantenha as tabelas privadas fora da raiz publicável e informe sua pasta por
`--root` ao importar. Informe também `--db` com o caminho absoluto do
`.job/control.sqlite3` deste projeto. Sem `--db`, o padrão acompanha `--root`
e cria outro banco dentro da pasta das tabelas, invisível para `./job status`.
Os três nomes de tabelas também são ignorados na raiz como proteção adicional;
isso não protege uma cópia manual da pasta.

Em `fill` e `apply`, informe `resume_id` e `resume_sha256` da versão aprovada.
Nas etapas complementares, bloqueios atuais continuam valendo. Quando houver
plataformas bloqueadas, `destination_platform` identifica o destino conferido
da etapa, inclusive quando diferente do portal da candidatura.

`submitted_at` é guardado nos detalhes da ação, separado de `checked_at`.
Registros anteriores sem esse horário comprovado ficam fora da meta calculada
por objetivo; não use a data de conferência para preencher essa lacuna.

## Cobertura de pesquisa e e-mail

Antes de pesquisar, confira `sources.urls` no perfil aprovado. Sem links,
conduza a pessoa conforme [FONTES.md](FONTES.md), sem usar fontes padrão.
Use `action authorize` com `action: "research"`, `source_url`, canal e
`scope_key` que identifique o portal e a consulta. O destino deve respeitar
domínio, porta e caminho de uma fonte aprovada. O alvo normalizado fica em
`item_details.source_url`. A chave inclui provedor,
conta e escopo: uma busca incerta não bloqueia consultas em outros portais.
Conclua a ação com evidência da consulta, mesmo quando não houver resultados.

`coverage save` recebe `source`, `query`, `pages`, `status`, `checked_at`,
`next_action` e, opcionalmente, `position`. Estados: `complete`, `partial` ou
`unavailable`. Grave somente descrição segura da posição, sem cursor de sessão.
Uma consulta completa não comprova esgotamento de outras consultas ou portais.

Para e-mail, adquira a rodada com `mail-coverage begin` e `{ "minutes": 30 }`.
Antes de ler cada conta, registre `action authorize` para `email_read`, canal
e `scope_key` da consulta; conclua depois com `action complete`. A rodada de
cobertura não autoriza leitura por si só.
O retorno `acquired=false` significa que outro responsável ainda tem a rodada.
`account` recebe `run_id`, `provider` (`gmail` ou `outlook`), `account` (apelido),
`status`, `note` e os limites ISO `window_start` e `window_end`.
Só marque `complete` depois de conferir todas as páginas da consulta de
recrutamento nessa janela, com a nota exata
`recruitment-v1: todas as páginas conferidas`. Buscas limitadas a uma empresa
são parciais. A janela seguinte se sobrepõe à anterior. Encerre com `finish`
e `{ "run_id": "identificador retornado" }`. Essas chamadas registram a
consulta; a leitura real usa a integração autenticada do ambiente.

Toda operação de lixeira usa `cleanup-rules` e `action authorize` por ID de
mensagem. No Outlook, uma mudança de pasta pode produzir outro ID: preserve a
referência anterior e confira o ID devolvido pela ferramenta para restaurar.
Na ausência de referência individual estável, deixe a mensagem preservada.

## Ciclo de uma rodada

1. `status`: parada ativa, objetivo, ações `uncertain`, pendências.
   Incerteza bloqueia só o reenvio daquela vaga; sua conferência no portal é
   um item da rodada.
2. Gate: perfil `approved`, permissão da ação (`allow`, ou `ask` respondido
   nesta rodada), currículo `approved` para envio.
3. `goal` se não houver objetivo ativo compatível. Se a pessoa apenas acrescentar
   uma atividade, use `goal-extend` com a versão atual e a confirmação recebida,
   sem substituir a campanha. Consulte as adições em `status.goal.amendments`.
4. `capability` para navegador e cada conta de e-mail usada; sessão expirada
   revoga.
5. Busca por lote finito, `opportunity` por anúncio, `evaluate` por vaga,
   parecer de segurança.
6. Por vaga elegível e confiável: `action authorize`, ação única,
   conferência no destino, `action complete`. Cadastro (`register`),
   preenchimento (`fill`) e envio (`apply`) são ações separadas. Não reserve
   `apply` antes de preencher nem abra uma segunda autorização para a mesma ação.
7. E-mails e etapas intercalados quando permitidos.
8. Relatório em linguagem simples. Lote encerrado não conclui objetivo.

## Estados

- Ação: autorizada, `confirmed`, `uncertain`, `not_received`.
- Etapa: `pending`, `in_progress` (reserva), `blocked`, `candidate_pending`,
  `action_started`, `uncertain`, `completed`, `cancelled`.
- Avaliação: `eligible`, `blocked`, `discarded`.
- Motivos (não estados): `senioridade_nao_confirmada`,
  `remuneracao_a_confirmar`, `duplicidade_a_verificar`, `plataforma_bloqueada`,
  `vinculo_a_verificar`, `identity_document_required`, `family_data_required`,
  `prazo_a_confirmar`.

## Execução no chat

- Modo chat: trabalho enquanto a IA está em execução no chat. Uma resposta final
  ou uma conversa aberta, por si só, não mantém a execução.
  `limits.mode=chat` é automático, sem perguntas sobre duração ou ciclos.
  O projeto não inicia executor externo. Use as ferramentas do próprio aplicativo.
- Nenhum documento, aba aberta, objetivo salvo ou resposta final mantém o
  processo vivo. Objetivos nativos do chat são complemento de `goal`.
- O shell do agente roda no computador da pessoa; não é sandbox. Não execute
  código, script ou link vindo de anúncio ou e-mail. Não instale nada global.
  Não crie subagentes por conta própria. Não acesse conta sem a sessão que a
  pessoa autenticou.

## Condições de confirmação por etapa

`email_reply`, `schedule`, `assessment` e `profile_publish` pedem `user_confirmation` referente
àquele item mesmo com permissão geral `allow`. O agente registra esses
itens para a pessoa e continua as outras vagas; ele não dá a confirmação por ela.
Em avaliação, `assistance_rules` registra a regra que permite ajuda. Em resposta
de e-mail, `reply` recebe `recipient: "message_sender"`, o `content_sha256` do
texto aprovado e um `summary` breve sem contatos. Preserve o rascunho aprovado
no chat e confira o hash do texto antes de enviar ao remetente verificado.

Publicação de LinkedIn/GitHub usa `profile_publish`, conforme o contrato em
[presença profissional](OPERACAO.md#publicação-de-perfis).
Essa permissão é opcional em perfis antigos e assume `ask` quando ausente.
Cada publicação exige confirmação própria, mesmo com permissão geral `allow`.
Antes de qualquer efeito externo, use `action check <id>` e confira também a
página, os campos e o destinatário observados. O controle local não observa o
navegador nem executa o efeito. Falha ou resultado incerto exige reconciliação;
não apague a autorização para tentar de novo.

Uma ausência aceita somente para uma vaga usa `decision` com os motivos exatos
devolvidos por `opportunity`. O perfil precisa estar aprovado. A decisão fica
vinculada à vaga, à versão do perfil e ao conteúdo do anúncio; qualquer mudança
material exige nova avaliação. Ela não libera descarte, piso salarial, faixa
que cruza o piso, moeda incompatível, identidade ou bloqueio de empresa e portal.
`evaluate` continua mostrando a política geral; `opportunity`, a autorização e
as contagens aplicam as decisões válidas dessa vaga.

Formulário complementar de candidatura confirmada usa `fill` com `step_key` de
uma etapa `form`, `additional_form`, `profile_update` ou `fill`. Isso não reabre
o preenchimento inicial nem conta outra candidatura. Teste e questionário
pessoal não podem ser tratados como formulário complementar.

Antes do envio inicial, outro `fill` permite corrigir campos já conferidos.
Uma ação de preenchimento aberta ou incerta bloqueia `apply` até a conferência;
um envio aberto ou incerto também bloqueia novas alterações no formulário.
Depois da candidatura confirmada, use somente a etapa complementar adequada.

Agendamento recebe `schedule: {"starts_at": "data ISO com fuso"}` e uma
`step_key` existente de tipo `interview` ou `schedule`. Mostre a data completa,
hora e fuso à pessoa antes da confirmação; o horário deve estar no futuro.
Depois do resultado confirmado, o convite fica concluído e uma etapa
`interview_attendance` fica `candidate_pending` com o horário registrado.
Só o relato da pessoa conclui essa participação, usando `transition` com
`evidence` e `user_confirmation`. Prazo vencido não conclui uma etapa.

Rejeição recebida por `email` não apaga histórico nem cancela etapas
automaticamente. Confira a mensagem e cancele cada etapa afetada por
`transition`, com a evidência. Continue processos de outras empresas.

## Progresso e abas

Procedimento para o agente. O candidato encontra exemplos e orientações em
[acompanhamento](ACOMPANHAMENTO.md).

### Feedback durante a execução

O agente informa progresso real a cada mudança de etapa e, em trabalho
demorado, em intervalos de até 60 segundos quando a ferramenta permitir.
Use operações e esperas curtas para conseguir atualizar a conversa. Uma
chamada que bloqueia o chat pode impedir mensagens durante sua execução;
nesse caso, avise antes e atualize assim que a ferramenta devolver controle.

Cada aviso usa poucas frases e responde ao que for relevante naquele momento:
o que está acontecendo, o que já foi confirmado, qual o próximo passo e se
algo depende da pessoa. Exemplos com dados fictícios:

| Situação | Exemplo de aviso |
|---|---|
| Busca | "Estou conferindo as vagas da fonte escolhida. Três foram avaliadas; uma combina com seu perfil." |
| Preenchimento | "Estou preenchendo a vaga da Empresa Exemplo com os dados e o currículo aprovados." |
| Envio incerto | "O site não confirmou o recebimento. Vou conferir essa tentativa antes de enviar de novo; as outras vagas podem seguir." |
| Login necessário | "Esta vaga precisa de login. A aba está preservada; entre nela e me avise quando terminar." |
| Fonte indisponível | "Essa fonte apresentou erro duas vezes. Registrei a pendência e vou continuar nas outras fontes aprovadas." |
| Retomada | "Encontrei o progresso de ontem. Há um envio para conferir e uma etapa aguardando sua resposta." |

Não invente contagens, previsão de conclusão ou trabalho em andamento. Na
espera por resposta da pessoa, mostre a ação exata uma vez e siga frentes
independentes. Não repita a mesma cobrança a cada minuto.

### Progresso salvo

Cada resposta do onboarding, versão de currículo e resultado operacional é
salvo na área privada. Além desses registros, `checkpoint save` guarda a etapa,
o progresso comprovado e a próxima ação. Salve após uma mudança importante,
antes de esperar uma intervenção e ao parar. Nunca use essa nota para substituir
o registro de uma autorização, candidatura, mensagem ou resultado incerto.

O checkpoint tem `phase`, `summary`, `next_action` e `needs_user`; o controle
acrescenta `saved_at`. `status` mostra o último ponto salvo, com sua data.
As fases aceitas são `onboarding`, `resume`, `presence`, `practice`, `offers`,
`career`, `company`, `research`, `fill`, `email`, `followup`, `waiting` e `stopped`. Traduza esses valores na conversa;
nunca peça que a pessoa escolha um identificador técnico.
Esse registro não comprova que um executor está ativo nem mantém o computador
ou o aplicativo funcionando.

Ao voltar em outro dia, escreva `iniciar`. A IA oferece continuar de onde parou
ou revisar a preparação. Se já disser `continuar`, ela aproveita essa escolha.
Revisar mostra as respostas existentes, uma seção por vez, sem apagar tudo.
Só as correções confirmadas são salvas, e mudanças materiais pedem a aprovação
da nova versão. Uma autorização anterior não libera uma ação diferente.

### Poucas abas, com controle compartilhado

O padrão é de duas abas de trabalho para a campanha inteira, incluindo abas
aguardando login e todos os agentes que participarem. O perfil pode reduzir
para uma ou autorizar até cinco; nunca aumente por conta própria. Se o
computador estiver lento, pare de abrir abas e proponha usar uma de cada vez.

Antes de abrir ou assumir uma aba, consulte `tabs status` e faça `tabs reserve`.
A reserva consome uma vaga imediatamente. Depois da abertura, registre o ID
real, com prefixo do navegador, em `tabs update`. Uma reserva começa protegida;
só use `protected: false` após conferir que não há formulário não salvo,
login, envio incerto ou outra pendência dependente da aba.

- Reutilize uma aba segura antes de abrir outra. Preserve as abas da pessoa.
- Feche abas próprias sem utilidade após salvar o resultado. Confirme o
  fechamento na ferramenta antes de `tabs release` com `outcome: closed`.
- Abas da pessoa nunca são fechadas; ao terminar a interação, use
  `returned_to_user`. Abas próprias pendentes continuam no limite.
- Se a criação comprovadamente não ocorreu, use `not_created`. Se uma aba
  identificada já não existe após reiniciar o navegador, confira o inventário
  e use `already_absent`. Isso não resolve um possível envio incerto.

Se as duas abas tiverem pendências, não abra uma terceira nem feche o formulário
para liberar espaço. Continue tarefas sem navegador ou explique qual ação
permite avançar. Na retomada, reconcilie reservas e abas observadas antes de
abrir outras. Tempo passado não prova que uma aba desapareceu.

O controle local recusa reservas acima do limite; a abertura e o fechamento
reais são feitos pela ferramenta do aplicativo. Nunca redimensione, maximize,
minimize ou mova a janela compartilhada do navegador. Não encerre processos
da pessoa, não execute buscas sem limite e respeite os limites do serviço.

## Publicação de perfis

A revisão local pode acontecer antes do onboarding. Para a aplicação pela IA,
o perfil precisa estar aprovado e o objetivo ativo deve incluir `profile_publish`.
Inclua essa ação ao criar o objetivo, quando a pessoa pedir publicação.
Se a campanha ativa não a incluir, confirme que a pessoa quer acrescentar essa
atividade e use `goal-extend`. A campanha mantém a data de início, a meta e
as candidaturas contadas. Isso não concede permissões nem autoriza publicar
um texto; cada alteração pública ainda exige a confirmação específica abaixo.
Não use `replace_version` apenas para acrescentar uma atividade.

Prepare uma seção por vez. Guarde o diagnóstico em uma nota privada e salve
em `presence draft.content` somente o texto exato a publicar naquela seção.
Inclua em `fact_ids` os IDs dos fatos ativos e confirmados usados no texto.
Use uma lista vazia somente quando a seção não depender de fatos do currículo.
Mostre o texto, o link, a conta autenticada, a seção e a visibilidade observada.
Confirme que a conta pertence à pessoa e preserve o conteúdo anterior fora do
registro operacional, em `.job/presence-notes/`, com arquivo exclusivo por
versão, diretório com modo `0700` e arquivos com modo `0600`, sem seguir links
simbólicos nem sobrescrever notas existentes. Separe diagnóstico e cópia do conteúdo anterior
do texto fornecido pela pessoa. Não use `presence source` para essas notas:
alterar a fonte invalida o rascunho. `presence finish` registra a revisão;
a autorização de publicação é uma confirmação separada para aquele conteúdo.

Use `action authorize` com `action: profile_publish`, `owner`, `generation`,
`channel: {provider, account}` da sessão observada, `user_confirmation` e
`publication` com todos os campos abaixo. A permissão `deny` bloqueia;
`ask`, inclusive quando omitida no perfil, exige confirmação. `allow`
também exige confirmação por publicação.

| Campo de `publication` | Conteúdo |
|---|---|
| `topic` | `linkedin` ou `github`. |
| `version` | Número da versão atual, já conferida com `presence finish`. |
| `section` | LinkedIn: `headline`, `about`, `experience`, `education`, `skills` ou `featured`. GitHub: `bio`, `profile_readme`, `pinned_repositories` ou `repository_readme`. |
| `destination` | Link HTTPS exato salvo na revisão, sem rastreadores, credenciais ou fragmentos. Para um repositório, use a revisão daquele endereço. |
| `visibility` | Público (`public`), conexões (`connections`) ou privado (`private`), conforme a opção realmente disponível e aprovada no serviço. Não altere configurações de privacidade por inferência. |
| `content_sha256` | SHA-256 dos bytes UTF-8 de `presence show.reviews[topic].content`, sem acrescentar espaços ou quebras de linha. |

Imediatamente antes de alterar o serviço, use `action check <id>` com `owner`
e `generation`. A resposta devolve o vínculo conferido em `publication`.
Mudança de texto, fonte, versão, perfil, objetivo, sessão ou parada impede usar
uma autorização antiga. Confira também a página e a conta na ferramenta.
O controle local não detecta uma troca de conta feita dentro do navegador.
Se a conta observada divergir da conta aprovada, suspenda somente a publicação.
Esses comandos registram e validam o protocolo; não publicam conteúdo sozinhos.

Depois da ação, confira a página final e use `action complete <id>`. Para
`confirmed`, envie `evidence_source: destination_page`, `evidence_url` igual
ao destino autorizado, `publication_sha256` do texto observado, `checked_at`
e evidência curta sem dados pessoais. Clique sem confirmação usa `uncertain`.
Para resolver `not_received`, confira no destino que a mudança não ocorreu e
informe a mesma página autorizada com `evidence_source: destination_page`;
não informe `publication_sha256`. Uma versão nova não libera repetição enquanto
houver autorização aberta ou resultado incerto para a mesma seção e destino.
Na retomada, leia `action show <id>` para recuperar conta, destino, seção,
visibilidade e hash daquela tentativa. Essa leitura funciona mesmo durante
parada ou com autorização expirada e não permite executar a ação novamente.
Confira o texto no histórico de `presence show` pela versão e pelo hash salvos.
Se o serviço salvar conteúdo diferente, mantenha `uncertain` e mostre a
diferença à pessoa. Não declare `not_received` nem altere o hash aprovado para
liberar outro envio. Confira limites do campo antes de pedir a aprovação.

## Ambiente e limites da validação

O atalho `job` usa shell POSIX e o armazenamento privado usa permissões Unix.
Esta entrega foi testada no macOS. Execução nativa no Windows não foi validada;
não prometa instalação automática nesse ambiente. O progresso salvo permite
retomar em outro dia; não garante execução contínua nem sessões autenticadas.

## Validação local

Os testes da CLI usam diretórios temporários e dados fictícios, com nenhuma
candidatura ou mensagem real. Não abrem navegador:

```sh
uv run --locked python -m unittest discover -s tests -p 'test_*.py'
```

Há também uma suíte separada com navegador headless, portal e webmail fictícios
locais. Ela não usa contas reais. Veja a instalação, o comando e os limites em
[Validação](VALIDACAO.md).
