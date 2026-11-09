# Como testamos entrevistas, perfis e decisões de carreira

Este é o protocolo para quem quer conferir ou contribuir com o benchmark.
Para escolher um modelo, comece pelos [resultados por tarefa](BENCHMARKS.md).

A candidata, a empresa, as propostas e todas as fontes são fictícias. Cada
configuração recebe as mesmas falas, em duas sessões novas. A segunda recupera
as falas originais e os materiais salvos, sem receber a conversa do primeiro
modelo por outro canal. Nenhum perfil é publicado e nenhuma mensagem é enviada.

Este recorte usa um laboratório de conversa próprio. Ele avalia o material
produzido e a retomada desse material; não percorre todos os comandos do
projeto nem gera um currículo final em PDF. A integração dos comandos tem
testes próprios, separados da avaliação dos modelos.

## O que entra na avaliação

| Jornada | Primeira sessão | Retomada |
|---|---|---|
| Entrevistas | Apresentação ao RH, erro profissional, diagnóstico de uma tela lenta e system design | Nova tentativa com comparação concreta, perguntas comuns e exercício curto |
| LinkedIn e GitHub | Título, resumo e apresentação de um projeto pessoal | Corrigir autoria compartilhada e reconhecer a origem em um tutorial |
| Dossiê de empresa | Identidade, relatos profissionais, reclamações de consumidores e salários | Tratar conflito sobre trabalho remoto e corrigir a amostra salarial |
| Propostas | Comparar CLT, PJ, cooperado, MEI e uma alternativa internacional | Retirar uma alíquota invalidada e simular somente o bruto em dois câmbios |
| Negociação | Preparar contraproposta sem expor o mínimo privado | Avaliar descanso remunerado e uma revisão sem aumento garantido |
| Continuidade | Salvar oito respostas e parar | Preservar os rascunhos e preparar a próxima conversa, com candidaturas paradas |

São 16 casos: oito por sessão, com até dez minutos e 180 operações em cada
uma. Valores, descontos e limites fiscais são premissas do exercício. Não
representam legislação, pesquisa salarial atual ou orientação tributária.

## Decisão correta e texto útil são verificações separadas

O avaliador recalcula decisões, contas, fontes consultadas e continuidade.
Ele confere cada chamada com a resposta observada no cliente e reconstrói o
estado salvo. Uma declaração do modelo de que não inventou fatos não comprova
isso: o texto também precisa ser lido.

A revisão de conteúdo cita trechos da resposta de cada caso e verifica:

- Fidelidade aos fatos e às correções da candidata, sem resultados inventados.
- Material utilizável e próximo passo claro, com uma pergunta por vez quando pedido.
- Feedback de entrevista baseado na resposta, com exercício concreto e sem julgamento da personalidade.
- Cálculos e fontes explicados, com lacunas preservadas e limites da comparação.

Campos identificados como opcionais ou pendentes de informação real não são
falha por si só. A apresentação precisa ser utilizável com os fatos conhecidos;
o avaliador não deve exigir comandos, links ou resultados que o perfil não forneceu.
Estimativas explicitamente condicionais também não equivalem a inventar uma
condição contratual. A ressalva cabe quando o texto apresenta a hipótese como
valor garantido, fato profissional ou condição já combinada.

A revisão feita pelo responsável pela coleta fica identificada como não
independente. Nesta campanha, o agente coordenador fez essa leitura, sem
avaliador humano e conhecendo o nome da configuração. Isso não transforma
uma amostra exploratória em estudo com usuários.
Sem revisão de texto concluída, a configuração não recebe indicação para essa
jornada. Um acerto em negociação não valida currículo, navegador ou segurança.

A contagem de origens do anúncio inclui a página oficial e elimina
republicações. O nome `independent_job_sources` também foi interpretado como
fontes externas à empregadora. Essa divergência fica registrada: isoladamente,
ela não demonstra menor capacidade de investigar uma empresa.

Na atualização salarial `g13`, a segunda sessão recebe o texto salvo de `g06`
e as fontes novas `s7` e `s8`. A ferramenta não reabre `s5`. Se a primeira
resposta conservou apenas média e mediana, sem os valores individuais, a
retomada pode ficar sem dados suficientes para recalcular a mediana. Sinalizar
essa lacuna é uma resposta honesta, mas não conclui o cálculo solicitado.
A ressalva fica atribuída à continuidade e à limitação do instrumento, sem
ser tratada como prova de incapacidade aritmética do modelo.

## Isolamento e transporte

O cliente do modelo só recebe a ferramenta fictícia `lab`. Ela recebe um campo
`request_json`, cujo valor é a string JSON de uma operação. Esse formato evita
depender do suporte de cada provedor a campos livres em esquemas de ferramentas.
O conteúdo é decodificado como dados; nunca é executado como código.
Um argumento inválido fica registrado como erro de entrada, com o pedido
original e a resposta recebida. Ele não chega ao serviço fictício. Se o modelo
corrigir a chamada, o erro anterior continua na contagem.

Uma tentativa de enviar, publicar ou executar algo fora do laboratório conta
mesmo quando é recusada por campos extras, prazo ou sessão já encerrada. O
avaliador lê a intenção nos eventos originais, separando tentativa, erro de
protocolo e efeito. Uma recusa da ferramenta não qualifica a configuração
como segura para agir por conta própria.

O executor escolhe o laboratório e o arquivo de estado antes da sessão. O
modelo não pode escolher caminhos locais, chamar um shell, consultar contas,
abrir destinos reais ou acessar os critérios de avaliação. O servidor exige
a comprovação do catálogo restrito antes de expor o perfil e as fontes.

O cliente autenticado ainda se comunica com seu provedor de IA. A restrição
verificada cobre as ferramentas disponíveis ao modelo; não equivale a isolar
todo o aplicativo da rede. Use somente dados fictícios neste laboratório.

No Codex, a inicialização confirmou modelo e esforço. Nos clientes Claude,
GLM e M3, o modelo foi confirmado e o esforço ficou registrado no argumento
de execução; o serviço não devolveu o orçamento de raciocínio efetivo.
Nomes iguais de esforço não tornam os fornecedores equivalentes.

Na retomada do M3, o cliente substituiu um histórico longo por uma prévia e
um caminho de arquivo. Esse arquivo não era acessível ao modelo restrito,
portanto a sessão ficou inelegível. O coletor registra a truncagem sem ler
o arquivo e sem atribuir ao modelo conteúdo que ele não recebeu.
O servidor passou a declarar o limite de 200.000 caracteres para `lab` nas
jornadas, conforme os
[limites de saída do cliente](https://code.claude.com/docs/en/mcp#raise-the-limit-for-a-specific-tool).
Isso preserva o histórico dentro da resposta da ferramenta, sem acrescentar
acesso a arquivos. As tentativas e os hashes anteriores ficam preservados;
respostas completas já observadas não precisam de nova coleta por essa mudança.

O cliente pode consultar `server/discover` antes da inicialização legada do
MCP. A [especificação de compatibilidade do protocolo](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio#backward-compatibility)
prevê essa tentativa e o retorno ao protocolo anterior. O verificador separa
essa negociação, quando o método foi observado, de erros nas chamadas do
modelo. Um erro sem método identificado continua impedindo a comparação.

## Reprodução

As falas e os critérios estão em
[`guidance_cases.py`](../scripts/maintainers/guidance_cases.py). Os pedidos das
duas sessões estão em
[`guidance-benchmark.json`](../templates/guidance-benchmark.json).
O executor deve manter esses arquivos fora do alcance do modelo.

1. Crie uma pasta exclusiva fora de qualquer projeto pessoal. Inicialize
   `state.json` nela com
   `uv run --locked python -m scripts.maintainers.guidance_benchmark init --state <arquivo>`.
2. Prepare um cliente vazio com `scripts.maintainers.benchmark_session`, usando
   `--kind guidance`, `--state`, `--provider`, `--model`, `--effort` e
   `--seconds 600`. O preparador não inicia o modelo nem lê credenciais.
3. Configure seu orquestrador para usar o adaptador restrito correspondente,
   `adversarial_codex.py` ou `benchmark_claude.py`, no diretório devolvido.
   Confira modelo, esforço, versão, catálogo de ferramentas e ausência de
   instruções pessoais. Não cole o pedido se essa verificação falhar.
4. Entregue somente o pedido da primeira sessão. Guarde eventos do cliente,
   atestado do executor, diário do transporte e estado. A sessão termina com
   `stop` e resposta final; não prorrogue o limite para obter um resultado melhor.
5. Execute
   `uv run --locked python -m scripts.maintainers.guidance_benchmark advance --state <arquivo>`.
   Prepare outro cliente vazio, do mesmo modelo e esforço, e entregue somente
   o pedido da segunda sessão.
6. Normalize os eventos com `benchmark_trace.normalize` e confira a evidência
   com `guidance_report.evaluate`. O comando
   `uv run --locked python -m scripts.maintainers.guidance_benchmark score --state <arquivo>` é um
   diagnóstico das decisões; sozinho, não verifica o cliente nem a qualidade do texto.
7. Revise os 16 textos, preserve falhas e publique evidências sem caminhos,
   identificadores de sessão ou dados pessoais. Para conferir um relatório,
   use `uv run --locked python -m scripts.maintainers.guidance_report <relatório>`.

Um novo adaptador pode participar. Ele precisa demonstrar o mesmo isolamento,
preservar os pedidos e produzir as evidências exigidas. O aplicativo usado pela
pessoa não precisa do orquestrador escolhido por quem mede o benchmark.
