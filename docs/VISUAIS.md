# Créditos visuais

Os arquivos desta pasta explicam o fluxo sem expor documentos ou contas.
Todas as conversas e endereços das demonstrações são fictícios.

| Arquivo | Dimensões | Origem e finalidade |
|---|---|---|
| `assets/carreira-guiada-cover.png` | 2172 × 724 | Capa original gerada com a ferramenta integrada de imagens. |
| `assets/fluxo-guiado.png` | 1024 × 1536 | Diagrama ilustrado original, gerado com a ferramenta integrada de imagens, com seis etapas de cima para baixo, dois desfechos e apoio opcional separado. |
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

O diagrama usa uma coluna com seis cartões numerados e setas para baixo:
configurar, preparar, buscar e avaliar, candidatar, acompanhar e analisar o
resultado. A única bifurcação mostra continuar pela busca ou encerrar por
objetivo atingido ou pedido para parar. LinkedIn, GitHub e treino de entrevistas
ficam numa faixa opcional, fora da sequência. O texto do README explica que
novas buscas e retornos são intercalados durante a execução. A imagem explica
o processo e não representa uma interface do produto.

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

## Direção do diagrama

Edição pela ferramenta integrada de imagens, usando o original como referência.
Briefing final: "Refazer o fluxo em uma única coluna, de cima para baixo, com
seis etapas numeradas e textos curtos. Preservar o papel claro, o verde escuro
e os detalhes em verde-lima. Manter as ilustrações pequenas e as letras grandes.
Depois da última etapa, mostrar dois desfechos: continuar a busca ou encerrar.
Colocar LinkedIn, GitHub e treino de entrevistas em uma faixa de apoio opcional,
sem setas ligadas ao percurso. Não usar zigue-zague, conectores cruzados,
capturas de aplicativos ou controles de interface. Indicar que o progresso
fica salvo para parar e retomar."

O arquivo final tem resolução nativa de 1024 × 1536 pixels, sem ampliação
artificial. Foi conferido visualmente e pela estrutura PNG, preservando o
bloco de proveniência C2PA. O conteúdo de cada etapa tem uma alternativa em
texto no README.
