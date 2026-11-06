# Créditos visuais

Os arquivos desta pasta explicam o fluxo sem expor documentos ou contas.
Todas as conversas e endereços das demonstrações são fictícios.

| Arquivo | Dimensões | Origem e finalidade |
|---|---|---|
| `assets/carreira-guiada-cover.png` | 2172 × 724 | Capa original gerada com a ferramenta integrada de imagens. |
| `assets/fluxo-guiado.png` | 1586 × 992 | Diagrama editorial original, gerado com a ferramenta integrada de imagens, com três fases em cores distintas, dois desfechos e apoio opcional separado. |
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

O diagrama organiza três fases da esquerda para a direita: preparação em
violeta, candidaturas em azul e acompanhamento em laranja. Os números, títulos
e setas também indicam a sequência, sem depender apenas das cores. O fundo é
branco, com ilustrações de traço e espaço entre as colunas. Continuar ou encerrar
aparecem abaixo do percurso, junto do apoio opcional de LinkedIn, GitHub e treino
de entrevistas. A imagem e o README explicam que novas buscas e retornos são
intercalados. O desenho explica o processo e não representa uma interface do produto.

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

Edição pela ferramenta integrada de imagens, substituindo a composição anterior.
Briefing final: "Criar um diagrama editorial horizontal, com fundo branco e
três fases sem caixas: Prepare em violeta, Candidate-se em azul e Acompanhe em
laranja. Usar tipografia grande, ilustrações simples de traço e bastante espaço.
Ligar os títulos com duas setas discretas da esquerda para a direita. Explicar
que a busca continua enquanto os retornos chegam. Abaixo, separar os desfechos
Continuar e Encerrar, seguidos do apoio opcional de LinkedIn, GitHub e treino
de entrevistas. Remover cartões, sombras, texturas e enfeites. Não representar
uma interface de aplicativo."

O arquivo final tem resolução nativa de 1586 × 992 pixels, sem ampliação
artificial. Foi conferido visualmente e pela estrutura PNG, preservando o
bloco de proveniência C2PA. O conteúdo de cada etapa tem uma alternativa em
texto no README.
