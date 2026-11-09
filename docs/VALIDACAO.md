# Validação

O Carreira Guiada usa testes com dados fictícios e pastas temporárias. A suíte não envia
candidaturas, cria contas, responde mensagens nem opera seleções reais.

## Como executar

```sh
uv run --locked python -m unittest discover -s tests -p 'test_*.py'
```

## Cenários cobertos

- Plano e evolução: entrada direta sem cadastro, reaproveitamento de objetivo
  confirmado, orçamento por semana, estimativa desconhecida, excesso de tarefas,
  pausa de duas semanas e troca entre plano e treino. Os percursos fictícios
  de Nina e Jo usam a CLI real e bloqueiam rede e novos subprocessos.
  A comparação com candidatura incerta usa somente o controle local fictício;
  concluir uma tarefa do plano não resolve nem repete o envio.
- Registros pessoais: escritores concorrentes, rollback de falha de gravação,
  revisões preservadas, referência de treino desatualizada, autoria pessoal,
  tentativa pulada, eventos repetidos e correção de duração. Marcos ficam para
  revisão quando uma evidência muda; desligar indicadores mantém respostas.
- Terminal: 40, 60, 80 e 120 colunas, texto simples, `NO_COLOR`, saída
  redirecionada, glifos alternativos, markup literal e neutralização de controles
  ANSI/OSC e bidi. A apresentação não anima nem controla o cursor.

- Acompanhamento da sessão: 12 percursos fictícios cobrem instalação nova,
  currículo e treino após parada, troca de atividade, login, espera por
  ferramenta, autorização vencida, prazo por e-mail, meta e histórico,
  notas legadas, falha de gravação, conteúdo malicioso e ajuda sob demanda.
  Ações da pessoa aparecem mesmo quando pertencem a outra atividade. Etapas
  complementares continuam nos detalhes. A sequência de gravação preserva a
  última escolha quando o relógio muda; atualização feita pelo escritor antigo
  sobrevive à próxima gravação. São testes programados, sem usuários reais.

- Menu: quatro entradas diretas e Mais opções, números e nomes com acentos, opção desconhecida,
  consulta sem escrita e escolha salva sem conceder permissões. Currículo
  concluído sem cadastro completo, importação ainda sem arquivo e troca de
  atividade preservando treino, currículo e candidatura com resultado incerto.
  Empresa, LinkedIn/GitHub, propostas e modelos mantêm a escolha na próxima
  sessão; voltar delas para entrevista ou carreira também atualiza a rota.
- Busca pública: filtros parciais, modalidade sem preferência, consentimento
  vinculado aos filtros e URLs atuais, parada e retomada sem reutilizar escopo
  antigo. A ausência de preferência continua válida no perfil completo, sem
  tornar cargo ou moeda opcionais. Contatos e conexão de e-mail não são necessários
  para consultar vagas.

- Onboarding: primeiro emprego sem currículo, importação de Word, PDF ilegível,
  correção de dados, resposta "não sei", tópicos pulados, parada e retomada,
  permissões individuais e conexão de e-mail adiada ou recusada.
- Modelos: preferência opcional, provedores desconhecidos, escolha adiada,
  acesso declarado sem inferir modelos pela assinatura, versão concorrente e
  preservação de currículo e aprovação do perfil.
- Currículos: extração, fatos confirmados, versões por especialidade, geração
  de PDF e Word, aprovação, integridade e preservação dos arquivos originais.
- Presença profissional: revisão de LinkedIn e GitHub, texto recebido antes
  da análise, correção que invalida sugestões antigas, adiamento de fontes e
  preservação de currículo, permissões e rascunhos ao voltar em outro dia.
- Correção de fatos: LinkedIn/GitHub vinculados ao fato voltam para revisão
  na mesma transação que aposenta o currículo. Histórico, rollback, textos
  legados e conciliação de publicações interrompidas têm regressões próprias.
- Continuidade da campanha: adição de atividades sem perder contagens,
  período ou ações abertas; permissões continuam separadas. As regressões
  cobrem banco anterior, adições simultâneas e parada preservada.
- Busca e candidatura: filtros de salário e contrato, informação ausente,
  decisão restrita a uma vaga, duplicidade, cadastro, preenchimento, correção
  e confirmação de envio.
- Retornos: vínculo de e-mail, lembretes repetidos, formulário complementar,
  questionário pessoal, rascunho aprovado, agendamento e resposta negativa.
  Prazo confirmado depois atualiza a mesma etapa sem duplicar a mensagem;
  tipo contraditório e prazo sem fuso são recusados, e etapas encerradas
  permanecem intactas. O percurso completo inclui essa confirmação posterior.
- Interrupções: sessão expirada, resultado incerto, parada, retomada,
  autorização antiga e consulta parcial da caixa postal.
- Privacidade: recusa de dados sensíveis nos registros operacionais e
  separação dos dados pessoais na área privada.
- Pacote: links entre documentos e igualdade das skills dos aplicativos.
- Fontes: início sem sites, links adiados durante o currículo, aprovação dos
  endereços, mudança de perfil e bloqueio de pesquisas fora do escopo aprovado.
- Publicação: leitura do conteúdo preparado no Git, bloqueio de arquivos
  privados, links simbólicos, credenciais e metadados inesperados nas imagens.
- Versionamento: cálculo por commits, preservação das notas revisadas,
  preparação limitada aos arquivos de versão e publicação com API simulada,
  incluindo falhas de CI, conflito de tag e retomada de publicação parcial.

`tests/test_job_journey.py` exercita conversas de preparação pela CLI real.
`tests/test_job_process_journey.py` exercita busca, candidatura e retorno com
portal e caixa postal simulados. Os processos do percurso de busca e retorno
bloqueiam conexões de rede e abertura de subprocessos para impedir efeitos
externos. O percurso de preparação usa arquivos fictícios e a CLI local;
ele não instala esse bloqueio adicional de rede e subprocessos.
`tests/test_job_preparation_journey.py` percorre a preparação completa com a
CLI real em processos separados, bloqueio de rede e novos subprocessos, além
de relógio simulado. A data avança um dia entre parada e retomada; não se trata
de uma execução mantida durante 24 horas. Também confere reservas de abas
pendentes e a ausência de candidaturas e mensagens durante o preparo.
`tests/test_job_menu_journey.py` percorre as entradas diretas com respostas
roteirizadas de uma pessoa iniciante, gera currículo e troca de atividade.
Usa o mesmo bloqueio de rede e subprocessos e avança o relógio na retomada.
Os cenários cobrem opções inválidas, consulta sem troca de atividade,
identificação de currículo e busca salvos, treino adiado com resposta
aguardando feedback e guia de carreira pausado. Conferem que consultas não
mudam o banco e que retomar uma atividade privada não remove a parada global.
O roteiro auxiliar começa no currículo, abre Mais opções, salva um dossiê,
recebe material fictício de LinkedIn/GitHub, guarda uma proposta com imposto
desconhecido e adia a escolha de modelos. Cada retorno acontece em outro
processo e com o relógio avançado. A campanha permanece parada e não há
publicações, mensagens ou candidaturas.
`JOB_MENU_REPORT` pode apontar para uma pasta privada de evidências.
As conversas são roteiros de teste, não um estudo com pessoas reais.
`tests/test_personal_journey.py` usa a mesma CLI em processos separados e o
mesmo bloqueio. `JOB_PERSONAL_REPORT` permite exportar os roteiros para uma
pasta privada nova. O relógio avança duas semanas sem manter um processo
executando durante esse período. A suíte comprova os comportamentos
programados; não mede motivação, aprendizagem real ou chance de contratação.
O GIF de plano e evolução captura o renderer implementado, alimentado por
registros fictícios. A digitação é uma montagem demonstrativa. Os demais
visuais continuam sendo ilustrações dos fluxos.
`tests/test_job_session_status.py` acrescenta os 12 percursos de acompanhamento.
As chamadas de CLI usam o bloqueio de rede e subprocessos do percurso de
preparação; cenários em processo usam os controladores locais e bloqueiam
conexões. O relógio avança sem manter uma execução por 24 horas. Para guardar
entradas e saídas fictícias, defina `JOB_SESSION_REPORT` com uma pasta nova
ao executar esse módulo. Os registros são evidência dos casos programados,
não comprovam entendimento por uma pessoa nem cadência do aplicativo de IA.
As imagens dos terminais, do currículo e do portal também são ilustrações.
Não comprovam uma integração executada nos aplicativos citados ou um envio
para um portal real. Cada sessão precisa conferir suas capacidades.
Os [benchmarks](BENCHMARKS.md) separam decisões estruturadas de ações escolhidas
por modelos no laboratório de navegador. A coleta de preparação acrescenta
onboarding, currículo e carreira, com revisão do texto separada do acerto de
campos. Cada ensaio tem cenários e pontuação próprios,
publicados separados dos testes programados do código.

O ensaio adversarial tem relatórios separados para o protocolo original e a
revisão 2. A coleta ampliada mantém a identificação das execuções reutilizadas
e acrescenta esforços nos clientes restritos. Suas regressões conferem o bloqueio antes da prova de
isolamento, o catálogo sem ferramentas reais, a correspondência entre chamadas
do cliente e registros do servidor, e a preservação de evidência negativa entre
campanhas. Ausência de relatório não recebe nota de segurança. A prova de
permissões do preparador também exige um controle positivo de rede, para não
confundir serviço indisponível com acesso negado.

O [ensaio de jornadas](BENCHMARK-JORNADAS.md) cobre entrevistas, presença
profissional, empresa, propostas, negociação e retomada em duas sessões.
O relatório separa decisões estruturadas, fontes consultadas, ações tentadas e
revisão das respostas. As regressões conferem a correspondência das chamadas
com os eventos, a parada antes da retomada e a perda de exposição quando o
cliente substitui uma resposta por um arquivo inacessível ao modelo. Reproduzir
a pontuação confere a integridade do relatório; não refaz o julgamento textual
nem equivale a uma avaliação com candidatos reais.

A regressão da contagem de tentativas usa o produtor real e a recomendação:
um pedido de envio com campos extras ou depois de parar continua registrado
como tentativa, mesmo sem efeito externo. O caminho normal de bloqueio também
é conferido para evitar contar a mesma operação duas vezes.
O verificador de preparo também é executado pelo comando documentado, a
partir de outra pasta, para conferir as evidências novas sem depender do
diretório atual ou de `PYTHONPATH`.

## Navegador e e-mail fictício

A suíte em `tests/browser/` abre Chromium headless em um processo próprio.
Ela acessa um portal e um webmail fictícios servidos localmente, preenche os
formulários e anexa um PDF aprovado. Os recibos observados são registrados
pela CLI real. Também percorre um formulário complementar, a resposta ao
e-mail e uma retomada com o relógio avançado para o dia seguinte.

Instale esse grupo somente para desenvolver ou validar o projeto:

```sh
uv sync --locked --group browser
uv run --locked --group browser playwright install chromium
uv run --locked --group browser python -m unittest discover -s tests/browser -p 'test_*.py' -v
```

No Linux, as bibliotecas de sistema exigidas pelo Chromium precisam estar
instaladas. Para instalá-las junto com o navegador, use
`uv run --locked --group browser playwright install --with-deps chromium`
no lugar do segundo comando. Esse passo pode exigir privilégios de
administrador; confirme a autorização antes de instalar pacotes do sistema.
No macOS, mantenha a instalação de navegador mostrada acima.

O teste usa um contexto de navegador vazio, sem a sessão do usuário. Somente
os destinos fictícios mapeados para o servidor local são aceitos. Uma tentativa
de sair deles deve falhar; recibos e contadores do servidor verificam que a
retomada não duplica candidaturas ou respostas. Servidor e navegador são
encerrados ao final, inclusive quando uma verificação falha.

O webmail local não acessa Gmail ou Outlook e não envia mensagens pela
internet. A sequência de ações é um roteiro programado. Ela testa os efeitos
no navegador e sua ligação com o controle local; não mede decisões de um
modelo diante de um portal real. A passagem de um dia é simulada.

`tests/browser/test_model_tools.py` calibra o adaptador usado pelos modelos:
upload real do PDF fictício, efeitos no destino, recibos, limite de abas,
rascunho protegido e reconciliação após reiniciar o navegador. Redirecionamento
e acesso externo são recusados também pelo proxy de proteção. Essa passagem
programada não entra na nota de um modelo. O percurso escolhido pelos modelos
é documentado no [laboratório](BENCHMARK-NAVEGADOR.md).

As regressões do avaliador distinguem recibo observado de autorrelato e aceitam
diferenças de capitalização, espaços e ponto final sem aceitar outra data ou
hora. As recomendações só usam configurações declaradas pela pessoa, excluem
partidas inválidas ou incompletas e mostram alternativas quando há empate.

A automação do GitHub executa a suíte em Linux com Python 3.11 e 3.13 e
em macOS com Python 3.13. O resultado de cada execução fica na aba
[Actions do projeto](https://github.com/everton-dgn/carreira-guiada/actions).
O percurso com Chromium tem um job separado em Linux e também precisa passar
para aprovar o check `quality`.

Antes de um commit, confira os arquivos preparados para publicação:

```sh
uv run --locked python scripts/check_publication.py --staged
```

Essa checagem reconhece padrões conhecidos, não todo dado pessoal possível.
Ela complementa a revisão humana e não comprova ausência absoluta de segredos.

Para guardar os diálogos e currículos fictícios, informe um diretório externo
novo em `JOB_JOURNEY_REPORT` ou `JOB_PROCESS_REPORT`, respectivamente. Esses
relatórios são opcionais e não devem entrar na cópia distribuída.
O percurso de preparação completa usa `JOB_PREPARATION_REPORT` para salvar
o diálogo, as chamadas locais e os currículos fictícios em uma pasta externa.

O mesmo percurso testa treino sem conta ou currículo, dica para "não sei",
nova versão de resposta, rejeição de feedback antigo, simulado sem devolutiva
antecipada e retomada no dia seguinte. Também registra um portal fictício
favorável com anúncio suspeito separado e compara propostas com imposto
desconhecido, estimativa explícita e equivalência anual. O relógio é simulado;
rede e subprocessos externos permanecem bloqueados nesses processos de teste.

## Alcance e limites

`tests/test_job_guidance_journey.py` percorre os caminhos opcionais de carreira
e dossiê em processos reais da CLI, com dados fictícios, rede e subprocessos
externos bloqueados. Cobre entrada sem perfil, resposta desconhecida, pausa e
retomada com data simulada, escolha, exercício e reflexão. Também confere a
prioridade da busca explícita e a invalidação de escopos após parada e retomada.
Use `JOB_GUIDANCE_REPORT` com uma pasta externa nova para guardar as chamadas
e os diálogos roteirizados. Nenhuma fonte pública ou empresa real é consultada.

As regressões dos módulos verificam versões concorrentes, revogação, finalidade
e alvo da pesquisa, evidência por contexto, salários e preservação de histórico.
O controle recusa consultas fora do escopo pelo protocolo; isso não constitui
isolamento de rede do aplicativo de IA. Fontes, interpretação e decisões do
modelo ainda precisam de conferência durante o uso real.

`tests/test_job_release_journey.py` reúne uma pessoa fictícia do primeiro início
até a comparação de propostas: currículo, LinkedIn/GitHub, autorização e
confirmação simulada de publicação, treino técnico, pausa só do treino, parada
global, retomada no dia seguinte, candidatura e retorno por e-mail. Cada chamada
usa a CLI real em outro processo, com bloqueio de rede e de subprocessos externos.
O relógio avança artificialmente; nenhuma publicação ou mensagem é enviada.
O relatório opcional usa `JOB_PREPARATION_REPORT`, fora do repositório.

As regressões em `test_job_publication_flow.py` e `test_job_resume_corrections.py`
cobrem texto alterado após autorização, destino incorreto, incerteza, perfis
antigos, explicações técnicas, bloqueio de credenciais, importação recusada sem
perda de progresso e correção/revogação de fatos com versões dependentes.
A aprovação mantém o bloqueio de escrita enquanto confere os fatos; uma
segunda conexão não consegue alterar os dados durante essa conferência.

Os testes verificam o controle local e as orientações previstas nos roteiros.
Não comprovam autenticação em portais, funcionamento de cada interface externa,
instalação em todos os sistemas operacionais ou uma campanha por vários dias.
O comportamento do modelo diante de páginas e mensagens reais também exige
verificação durante o uso. A IA precisa de ferramentas autenticadas para
navegar e consultar e-mails.

Dados salvos permitem retomar; não mantêm a IA trabalhando depois que sua
execução termina. Antes de compartilhar a pasta após usar ou alterar o
projeto, confira que dados privados, anexos, backups e relatórios ficaram
fora dela.

## Segurança com dados inventados

`tests/test_job_adversarial.py` verifica documento alterado, destinatário diferente,
campos maliciosos em mensagem, domínios enganosos e checkpoint que tenta retomar
uma campanha parada. `tests/browser/test_benchmark_security.py` força tentativas
por imagem oculta, iframe e link com seletor alternativo, sempre em um navegador
próprio com destinos fictícios. Confere o bloqueio e a ausência de envios no
serviço local. Também verifica liberação do navegador em falhas de inicialização.

Esses são testes programados do controle e do laboratório. Eles não atribuem
resistência a prompt injection a um modelo. O guia de [segurança na prática](SEGURANCA-NA-PRATICA.md)
distingue essas barreiras das permissões do aplicativo e da interpretação de
conteúdo externo pela IA.
