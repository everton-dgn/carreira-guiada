# Créditos visuais

Os arquivos desta pasta explicam o fluxo sem expor documentos ou contas.
Todas as conversas e endereços das demonstrações são fictícios.

| Arquivo | Dimensões | Origem e finalidade |
|---|---|---|
| `assets/carreira-guiada-cover.png` | 2172 × 724 | Capa original gerada com a ferramenta integrada de imagens. |
| `assets/fluxo-guiado.png` | 1536 × 1024 | Diagrama ilustrado original, gerado com a ferramenta integrada de imagens, do onboarding ao resultado e à nova rodada. |
| `assets/inicio-guiado.gif` e `.png` | 2240 × 1400 | Conversa fictícia no terminal do Claude Code, do início à aprovação do perfil. |
| `assets/candidatura-guiada.gif` e `.png` | 2240 × 1400 | Conversa fictícia no Codex CLI, da busca ao preenchimento, aprovação, confirmação e retomada. |
| `assets/curriculo-guiado.gif` e `.png` | 2240 × 1400 | Conversa com uma IA genérica e prévia fictícia do currículo, dos fatos à versão aprovada. |
| `assets/portal-guiado.gif` e `.png` | 2240 × 1400 | IA genérica e portal externo fictício, com navegação, digitação, anexo e confirmação simulada. |
| `assets/entrevista-guiada.gif` e `.png` | 2240 × 1400 | IA genérica, resposta sobre um erro, feedback específico e pausa com retomada no dia seguinte. Não contém áudio. |

As animações não são gravações de contas reais nem evidência de candidaturas
enviadas. Há uma alternativa estática e um percurso em texto junto de cada GIF.
Cada animação tem cinco cenas com quadros intermediários de digitação e
respostas progressivas. Os terminais têm cursor piscando; o portal também
mostra deslocamento do ponteiro. Há pausas para ler cada cena.
Os textos e desenhos são renderizados diretamente na resolução indicada, sem ampliar uma imagem
pequena. A aparência real dos terminais varia conforme versão e tema.
O Carreira Guiada não oferece uma interface gráfica própria. A prévia do
currículo ilustra o conteúdo, não reproduz exatamente o PDF gerado. O portal
usa um domínio reservado de exemplo e nunca é acessado pelo renderizador.

A capa e o diagrama preservam a identificação de origem C2PA da ferramenta geradora.
O verificador permite somente esses arquivos exatos, conferidos por hash. Uma
substituição exige nova revisão da imagem e dos metadados antes de atualizar
essa referência. As outras imagens aceitam apenas os blocos necessários ao
desenho e à animação.

O diagrama usa nove cartões de papel ilustrados, verde escuro e verde-lima,
com setas numeradas para mostrar preparação, fontes verificadas, busca,
candidaturas, retornos, treino, propostas e resultado. LinkedIn, GitHub e voz
quando disponível aparecem numa faixa opcional. O término
indica o objetivo combinado ou a ordem da pessoa para parar. O texto completo
está disponível junto da imagem no README. A imagem explica o processo e
não representa uma interface do produto.

## Recriar as demonstrações

Execute `uv run --locked --group docs python scripts/maintainers/render_docs.py`.
Para currículo, portal e entrevista, execute
`uv run --locked --group docs python scripts/maintainers/render_journeys.py`.
O código usa Pillow e fontes de texto e monoespaçada disponíveis no sistema. As fontes não são
redistribuídas. Confira o resultado visualmente antes de publicar.

## Direção da capa

Briefing: capa editorial panorâmica para um guia de candidaturas no chat,
fundo de papel claro, verde escuro e detalhes em verde-lima. Currículo de papel,
balões de conversa e um caminho de pequenos cartões representam etapas guiadas.
Texto: "Carreira Guiada", "Automatize sua busca de emprego." e
"Sua IA cuida das candidaturas."
Sem dados pessoais, capturas de aplicativos, controles de interface ou marcas
de portais. A edição final preservou a composição abstrata e trocou a chamada
para comunicar a automação da busca e das candidaturas. Foi usada a ferramenta integrada
de imagens, com revisão visual e de metadados antes da inclusão no projeto.

Os materiais visuais originais são distribuídos sob a licença do projeto,
na medida dos direitos aplicáveis. Não são usadas capturas de produtos de
terceiros ou marcas de plataformas de vagas.

Atualização do diagrama: edição pela ferramenta integrada de imagens, usando
o original como referência. Briefing: preservar papel recortado, paleta e
legibilidade; acrescentar fontes verificadas, treino, propostas e retomada;
manter explícitos autorização, etapas pessoais e término por objetivo ou parada.
O arquivo final foi conferido visualmente e pela estrutura PNG, preservando
o bloco de proveniência C2PA.
