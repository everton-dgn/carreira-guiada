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
`sources.urls` guarda endereços HTTPS escolhidos pela pessoa. A lista pode
ficar vazia durante o preparo, mas `research` exige fontes aprovadas e
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

`ResumeManager(root)` em `scripts/job/resumes.py`:

- `import_file(path, label)` preserva o original e extrai texto de PDF, DOCX,
  Markdown ou TXT. Retorna ID, referência e hash; não confirma fatos.
- `add_fact(text, source, confirmed)` vincula a um ID importado ou a uma
  referência `candidate:` de resposta explícita da pessoa.
- `draft(label, markdown, fact_ids)` exige fatos existentes e confirmados,
  produz PDF, DOCX e Markdown e registra os hashes dos três arquivos.
- `approve(id)` aprova a versão conferida pela pessoa e substitui a aprovação
  anterior do mesmo rótulo. Outras especialidades continuam independentes.
- `get(id)` confere todos os arquivos e hashes. `list()`, `facts()` e
  `sources()` consultam o inventário sem aprovar nem alterar conteúdo.

Proveniência não comprova automaticamente a narrativa: o agente mostra o
rascunho completo à pessoa. O envio exige aprovação e hash válido. Arquivos
são escritos antes do registro final; uma falha de disco pode deixar um arquivo
órfão privado, sem transformá-lo em versão aprovada. Nunca envie um arquivo
apenas porque ele apareceu no diretório.

## Operação e evidências

`Workflow(root)` em `scripts/job/workflow.py` coordena o banco implementado em
`scripts/candidaturas/`. Seus payloads completos estão nas docstrings.

- `configure_goal(payload)` registra escopo e critérios; meta e prazo são
  opcionais no modo chat. Um objetivo diferente exige substituir a versão
  explicitamente. Contagens usam oportunidades únicas e filtros atuais.
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
