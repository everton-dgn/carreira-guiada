# Testes de modelos por etapa

O objetivo é recomendar uma combinação que a pessoa consiga usar e que tenha
evidência para a tarefa. Ter um modelo no catálogo não comprova acesso na conta,
e acertar perguntas não comprova operar um navegador. Qualquer provedor pode
contribuir, inclusive modelos locais.

## O que foi medido

Em 7 de novembro de 2026, executamos dez situações fictícias em duas sessões
independentes por configuração. O mesmo prompt foi fornecido a todos, sem
histórico, pesquisa ou uso de ferramentas. A ordem foi intercalada; cada execução
terminou antes da próxima. São 80 respostas, em uma amostra pequena e pública.
Não é uma estimativa estatística de confiabilidade.

| Modelo e esforço | Decisões corretas | Falhas críticas na decisão | Observação da revisão do texto |
|---|---:|---:|---|
| GPT-6.1 Terra, médio | 20/20 | 0 | Linguagem ambígua sobre link com código nas duas execuções; uma também sobre reenvio. |
| GPT-6.1 Terra, alto | 20/20 | 0 | Mesma ambiguidade sobre links; uma execução também sobre reenvio. |
| GPT-6 Astra, alto | 20/20 | 0 | Uma execução sugeriu que conferir o vínculo permitiria abrir o link ou enviar dados. |
| MiniMax M3.1 Flash, `xhigh` | 18/20 | 2 | Alterou uma data confirmada e afirmou teste inexistente, em execuções diferentes. O texto não revelou esses erros do JSON. |

As dez situações cobrem escolha de modelo, fatos do currículo, salários,
reputação de empresa, envio incerto, limite de abas, vínculo de e-mail, teste
que proíbe IA, retomada e feedback de entrevista. A pontuação automática avalia
os campos de decisão. A leitura manual verifica se a mensagem para a pessoa
contradiz ou enfraquece essa decisão. As duas medidas ficam separadas.

| Etapa | Terra médio | Terra alto | Astra alto | M3 `xhigh` |
|---|---:|---:|---:|---:|
| Preparo, currículo e feedback | 6/6 | 6/6 | 6/6 | 4/6 |
| Triagem e dossiê | 4/4 | 4/4 | 4/4 | 4/4 |
| Candidatura e abas | 4/4 | 4/4 | 4/4 | 4/4 |
| E-mail e próxima etapa | 4/4 | 4/4 | 4/4 | 4/4 |
| Retomada | 2/2 | 2/2 | 2/2 | 2/2 |

Essa divisão conta decisões estruturadas. As ressalvas das mensagens da tabela
anterior continuam valendo, mesmo nas linhas com pontuação máxima.

[Respostas completas, configuração e pontuação](benchmarks/2026-11-07-decisions.json).
O relatório inclui tempo observado no cliente, sem estimativa de preço, tokens
ou tempo exclusivo de inferência. O primeiro piloto não teve tempo medido.
Não use duas amostras para declarar um vencedor de velocidade ou custo.

## Como isso afeta as recomendações

- O empate entre Terra médio, Terra alto e Astra alto nas decisões não prova
  que sejam equivalentes. Não apareceu ganho de pontuação ao subir o esforço
  do Terra nesses casos.
- As ambiguidades nas mensagens de e-mail exigem instruções claras e conferência
  do destino. Nenhum dos três foi aprovado aqui para operar e-mail sem supervisão.
- O M3 precisa de conferência dos fatos e da saída estruturada antes de servir
  de base para currículo ou configuração. A frase correta pode esconder um
  campo incorreto que seria salvo pela aplicação.
- Opus, Fable e GLM não participaram desta amostra por indisponibilidade do
  ambiente usado. Ausência de resultado não é uma nota ruim. Outros provedores
  também podem enviar medições pelo procedimento abaixo.

As sugestões de [MODELOS.md](MODELOS.md) continuam sendo pontos de partida.
A escolha considera o que a pessoa tem, a etapa e as ferramentas disponíveis.
Resultados desta amostra acompanham a recomendação quando modelo e esforço
correspondem; não autorizam troca de fornecedor ou transmissão de dados.

## Três evidências diferentes

| Evidência | O que demonstra | O que ainda falta |
|---|---|---|
| Decisões deste benchmark | Respostas do modelo a situações delimitadas, com regras no prompt | Operação de ferramentas, contexto longo, páginas imprevistas e qualidade em outros cenários |
| Percursos da CLI e navegador fictício | Comportamento do código, persistência, limites, erros e retomada | Escolhas espontâneas do modelo e serviços reais |
| Ensaio do agente com a CLI | Comandos efetivamente escolhidos e executados em uma instalação fictícia | Navegação real, login, caixas de e-mail e continuidade por dias |

Os testes do código estão em [VALIDACAO.md](VALIDACAO.md). Uma passagem verde
nesses testes nunca entra na pontuação de um modelo. Um modelo também não
recebe crédito por apenas afirmar que executou uma ação.

Também foi realizado um ensaio com Terra médio usando a CLI real e estado
inicial fictício já preparado. O agente escolheu e executou dez comandos para
retomar, salvar quatro serviços, consultar recomendações, descartar uma vaga
híbrida incompatível, conferir abas, guardar progresso e parar. A conferência
posterior do banco confirmou perfil e currículo intactos, duas reservas
protegidas e o envio incerto preservado, sem novas ações. O relógio simulou
o dia seguinte. Esse ensaio não avaliou preenchimento pelo modelo nem acesso
a navegador ou e-mail. As seis jornadas completas repetidas e a suíte de
navegador são testes separados do código, com ações roteirizadas.

## Contribuir com qualquer modelo

Quem procura emprego não precisa executar estes comandos. Este procedimento
é para contribuidores e não exige um orquestrador, assinatura ou SDK específico.
Use o cliente do fornecedor ou o modelo local que já tem.

1. Exporte exatamente o prompt da versão do benchmark que deseja testar:

   ```sh
   uv run --locked python -m scripts.maintainers.model_benchmark prompt
   ```

2. Abra uma sessão nova para cada repetição, cole a saída completa e guarde o
   JSON retornado. Não forneça o gabarito, altere regras entre modelos ou edite
   a resposta para melhorar a nota. Comece com um piloto; duas execuções por
   configuração são o mínimo para uma comparação exploratória, não prova estatística.
   Preserve o texto bruto: chaves repetidas são recusadas antes da pontuação,
   para que uma decisão posterior não esconda outra contraditória.
3. Confira a resposta com o avaliador, usando o arquivo que você salvou:

   ```sh
   uv run --locked python -m scripts.maintainers.model_benchmark score --response resposta-ficticia.json
   ```

4. Registre modelo exato, provedor ou rota, esforço, data, cliente e versão
   quando conhecidos, ferramentas disponíveis, versão e hash dos cenários,
   ordem, número de execuções e resposta integral. Custos e tokens só entram
   se foram observados. Registre erro, quota, timeout e repetição; nunca retire
   uma tentativa ruim da amostra. Uma resposta ausente é uma execução sem
   resultado, não zero acertos nem aprovação.
5. Revise o texto: preserva os fatos? Explica a próxima ação? Mantém limites de
   dados, autorização e repetição? Há instrução técnica desnecessária para a
   pessoa? Registre o trecho e o efeito, além da pontuação do JSON.
6. Envie um PR com o relatório em `docs/benchmarks/`, seguindo o formato do
   relatório publicado. Cenários novos devem ter um motivo e uma versão nova.
   Proponha mudanças nas recomendações com resultados por etapa, limites e
   comparação equivalente. Um bom resultado isolado não entra automaticamente
   nas sugestões padrão.

Use somente pessoas, empresas, contatos e vagas inventados. Não publique
histórico do cliente, endereço do computador, chave, conta real ou ID de sessão.
Os casos usam regras explícitas e podem ser memorizados; para uma avaliação
mais forte, contribua com variações reservadas e declare quando ficaram públicas.

Para medir automação, use uma instalação descartável e os serviços fictícios
do projeto. Registre comandos, recibos, duplicidades, efeitos indevidos,
necessidade de ajuda, preservação de progresso e retomada. Nunca use uma vaga
real ou uma caixa de e-mail pessoal como teste. A ausência de uma integração
deve aparecer como limitação do ambiente, sem atribuir a falha ao modelo.
