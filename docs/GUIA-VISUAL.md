# Guia de estilo das ilustrações e dos GIFs

Este guia preserva a identidade das peças do README e da documentação.
Uma revisão visual começa pela arte existente e corrige problemas localizados.
Os currículos enviados às empresas seguem o [guia de currículos](CURRICULOS.md).

## Direção: preservar a identidade, refinar o acabamento

Os banners combinam fundo marinho, títulos claros e ilustrações de documentos
com profundidade discreta. Currículos, cadernos, fichas, agendas e mensagens
explicam o trabalho que a pessoa faz com o projeto. Essa riqueza faz parte da
identidade. Reduzir o excesso de azul não exige trocar o fundo por branco,
substituir objetos por ícones ou refazer a composição.

A referência dos banners é `retornos-progresso-banner.png`: objetos relacionados
ao recurso, papel branco, contraste e espaço entre título e ilustração.
Para os GIFs, use `minha-evolucao-demo.gif`: moldura marinha, terminal branco,
texto escuro e destaques azuis. Essa referência vale também para conversas
ao lado de um currículo, caderno ou portal. O diagrama da jornada mantém fundo
claro para separar etapas e conexões. Essas diferenças têm função.

Antes de alterar uma peça, registre o defeito concreto e a menor correção:
brilho intenso, letra com sombra, texto encostado em objeto ou detalhe ilegível.
Compare o antes e o depois. Uma mudança de direção artística exige combinar
a proposta com o mantenedor antes de aplicá-la ao conjunto.

## O que fica fixo e o que pode variar

| Fica fixo | Pode variar conforme a peça |
|---|---|
| Identidade marinha, papel branco e ciano como destaque | Diagrama claro e formatos das notas pessoais |
| Hierarquia e letras legíveis, sem efeitos sobre títulos | Objetos, papéis sobrepostos e perspectiva discreta |
| Texto separado da ilustração | Fitas e etiquetas nas peças de planejamento e evolução |
| Cabeçalho e informação de contexto nos GIFs | Painel de conversa, documento, portal ou saída real |
| Fundo branco e texto escuro em toda área de terminal | Largura do painel e posição dentro da moldura marinha |
| Digitação visível e pausa para leitura | Número de cenas necessário para mostrar a tarefa |

Toda peça publicada tem título dentro da arte. Mantenha uma peça principal por
seção, acrescentando outra apenas quando mostrar uma etapa diferente.
Detalhes de produção ficam neste guia e no CONTRIBUTING, fora do README.

## Cor, luz e profundidade

| Função | Referência | Uso |
|---|---|---|
| Fundo marinho | `#07152E` | Base dos banners e moldura externa dos GIFs |
| Texto claro | `#F3F7FF` | Títulos e conteúdo sobre escuro |
| Texto de apoio | `#A4BCDF` | Contexto e legendas sobre escuro |
| Ciano | `#60D9F4` | Rótulo, expressão destacada e pequenas marcações |
| Azul claro | `#6DA7FF` | Texto secundário e detalhes sobre escuro |
| Azul | `#2864ED` | Capas, objetos e marcações, com moderação |
| Branco | `#FFFFFF` | Terminais, documentos, fichas, páginas de cadernos e notas |
| Texto sobre claro | `#0F1B2D` | Títulos e conteúdo de documentos |

A paleta orienta novas composições; não obriga a recolorir cada pixel de uma
ilustração existente. Atenue primeiro feixes de luz, halos e grandes formas
saturadas que disputem atenção com o recurso. Preserve o contraste do texto.
Evite somar capa azul, brilho intenso e fundo saturado na mesma área.

O papel tem base branca em todos os banners, inclusive nas peças pessoais.
Folhas, páginas, notas e etiquetas de papel não usam creme, bege ou iluminação
amarelada. Preserve a textura e use sombras suaves em cinza neutro para dar
volume. Fitas, capas e marcações mantêm as cores da peça; madeira e metal podem
conservar seus tons naturais.

Ao corrigir o tom do papel, preserve o fundo azul, os textos, as dimensões e a
composição. Compare com o original para conferir que o retoque ficou restrito
às superfícies identificadas.

Sombras de contato, papéis empilhados, textura discreta e perspectiva suave
podem dar volume aos objetos. Letras dos títulos têm cor uniforme, sem sombra,
halo, relevo ou reflexo. A regra sobre letras não proíbe sombra no caderno.

Contrastes nominais sobre `#07152E`: texto claro, 16,92:1; texto de apoio,
9,38:1; ciano, 11,01:1. Confira também a região real atrás da letra: gradientes
e ilustrações podem mudar o contraste. Ciano não serve como texto sobre branco.
Essas medidas não certificam a acessibilidade de uma imagem inteira.

## Tipografia e composição

Use uma família sem serifa consistente nos títulos e rótulos. Para composições
por código, use DejaVu Sans ou Arial e mantenha a escolha no lote. Reserve
DejaVu Sans Mono, Menlo ou Consolas para comandos e saídas de terminal.
Anotações manuscritas curtas podem aparecer dentro de uma nota ilustrada;
a informação essencial também precisa estar legível no texto da página.

Nos banners, preserve a estrutura de texto à esquerda e objeto à direita.
Use rótulo, título curto e subtítulo. Evite aumentar a quantidade de texto
para preencher espaço. A marca completa pode aparecer na abertura e nas peças
pessoais; nas demais, o rótulo do recurso costuma bastar.

Para novos banners, a referência é 2172 × 724 pixels, com base 1086 × 362 em 2×.
Títulos usam aproximadamente 48 px na base; subtítulos, 22 px; rótulos, 16 px
ou mais. Reserve cerca de 48 px nas laterais e 36 px em cima e embaixo, com
espaço entre texto e objeto. Essas medidas orientam o encaixe; não distorça ou
corte uma arte existente apenas para mudar sua proporção. As duas peças
pessoais podem manter o formato 1983 × 793, e diagramas usam a proporção que
permita ler as etapas.

Quando faltar espaço, ajuste o texto ou o objeto apenas na região afetada.
Não reduza toda a composição até os rótulos ficarem ilegíveis. Composição por
código mantém texto e ilustração editáveis; o arquivo publicado contém ambos.

## Objetos que explicam o recurso

Preserve os objetos já usados quando tiverem função: documentos no currículo,
agenda nos retornos, lupa no dossiê, propostas lado a lado e caderno no plano.
As peças pessoais podem usar notas, fitas, caminho e registro de conquistas.
Uma metáfora dentro do documento pode ajudar a explicar uma direção; avalie
se ela funciona antes de trocar o objeto inteiro.

Retire decorativos soltos quando estiverem competindo com o conteúdo.
Conquistas ilustram práticas com critérios; não devem sugerir certificação
profissional, resultado garantido ou nota real que o projeto não calcula.

O projeto funciona no chat e nas ferramentas disponíveis. Ilustração de um
recurso não deve parecer uma interface própria do produto. Telas de terminal
ou portal pertencem às demonstrações e recebem identificação explícita.

## Moldura e movimento dos GIFs

A base é 1120 × 700, exportada em 2240 × 1400. Preserve a moldura escura da
família existente: marca à esquerda, natureza da demonstração à direita,
divisor, título e subtítulo. Dentro dela, toda conversa ou saída de terminal
fica em painel branco, inclusive nas cenas com documento ou portal ao lado.
Use margens de 40 px, título próximo de 40 px e subtítulo de 23 px.
Conteúdo principal usa pelo menos 20 px; rótulos de apoio, pelo menos 16 px.

### Paleta do terminal

| Elemento dentro do painel | Cor |
|---|---|
| Fundo | `#FFFFFF` |
| Texto principal | `#102951` |
| Texto de apoio e identificação | `#546D8F` |
| Pedido, comando destacado e cursor | `#2864ED` |
| Borda e divisores | `#C4D7F5` |
| Fundo de destaque discreto | `#E4EEFF` |

Use as cores claras e o ciano da moldura somente sobre o fundo marinho.
A digitação e a rolagem preservam a paleta do terminal.
Saída real mantém o conteúdo e a identificação dos estados; adapte
sua paleta de apresentação ao branco, sem trocar o tema do terminal da pessoa.
Não adicione sombras, gradientes ou reflexos às letras.

O painel fica branco em todas as cenas e quadros intermediários. Confira o GIF
exportado, pois a redução da paleta pode tingir o branco mesmo quando o PNG
está correto. Preserve a moldura marinha, a composição e os banners azuis;
padronizar terminais não autoriza redesenhar essas peças.

### Sequência e leitura

Diferencie "Simulação fictícia" de "Terminal real com dados fictícios".
Mostre primeiro o pedido da pessoa. Uma consulta como `./job plan show`,
quando aparecer, deve ser identificada como operação feita pela IA.

- Mostre pedido, ação, resultado conferido e próximo passo.
- Preserve digitação e quadros intermediários com mudança perceptível.
- Mantenha cada cena completa por pelo menos cinco segundos. Seis segundos
  são uma boa base; conteúdo denso pode exigir sete ou mais.
- Conte a pausa a partir do último caractere, incluindo piscadas do cursor.
- Use segmentos de progresso para as cenas da demonstração, sem simular
  percentual real de candidaturas ou tempo de execução.
- Preserve a geometria da moldura e evite flashes e zooms repetidos.
- Se a saída real não couber, mostre rolagem identificada com pausas de leitura;
  não encolha a fonte nem corte informação sem avisar.
- Confira início, cenas completas, intermediários e volta do loop.
- Exporte o PNG de uma cena informativa com o mesmo nome-base do GIF.

Pessoas, empresas e registros das demonstrações são fictícios. Não invente
resultados para promover o recurso nem apresente uma conversa desenhada como
captura real do código.

## Ficha de retoque e conferência

Antes de editar, registre: arquivo original, problema observado, região afetada,
o que será preservado e como conferir o resultado. Por exemplo: "atenuar o brilho
atrás das propostas, mantendo os documentos, o título e o fundo marinho".

- [ ] A composição e a identidade foram preservadas.
- [ ] Cada alteração resolve um problema identificado na peça.
- [ ] O título continua dentro da arte, com acentos e sem efeitos nas letras.
- [ ] Texto, objetos e bordas não colidem.
- [ ] A cor de destaque orienta a leitura sem cobrir a ilustração inteira.
- [ ] Folhas, páginas de cadernos e notas têm base branca, sem tom amarelado;
  a textura e as sombras suaves preservam o volume.
- [ ] Todos os painéis de conversa e saída usam fundo branco, texto escuro e
  a paleta de terminal deste guia, inclusive os painéis laterais.
- [ ] O GIF exportado mantém o branco no início, nas cenas completas,
  nos quadros intermediários e na volta do loop.
- [ ] A 900 px, o conteúdo principal é legível; a 400 px, título e ideia central
  continuam reconhecíveis. Informação essencial também aparece no texto da página.
- [ ] GIF, PNG e gerador correspondem; os tempos foram conferidos.
- [ ] A revisão informa arquivos e cenas vistos e suas limitações.
- [ ] Substituições usam nome novo e referências atualizadas. Os originais
  permanecem recuperáveis no Git; a publicação passa pela conferência do índice.

Confira o gerador responsável antes de corrigir ou regenerar uma peça:

| Gerador em `scripts/maintainers/` | GIFs |
|---|---|
| `render_docs.py` | `menu-com-contexto.gif`, `busca-com-progresso.gif` |
| `render_journeys.py` | `curriculo-revisado.gif`, `candidatura-portal.gif`, `entrevista-ensaio.gif` |
| `render_personal.py` | `plano-evolucao-terminal.gif` |
| `render_evolution.py` | `minha-evolucao-demo.gif` |

Uma saída antiga de qualquer gerador precisa passar pela paleta deste guia
antes de ser republicada. Os comandos de produção estão em
[CONTRIBUTING.md](../CONTRIBUTING.md#documentação-e-imagens).
Peça coerente e legível pode ser mantida sem alteração. Revisar o conjunto
não exige modificar todos os arquivos.
