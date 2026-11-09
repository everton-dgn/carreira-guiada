# Guia de estilo das ilustrações e dos GIFs

Esta é a referência para criar e revisar as peças do README e da documentação.
Vale para banners, diagramas, demonstrações animadas e suas versões estáticas.
Os currículos enviados às empresas seguem o [guia de currículos](CURRICULOS.md).

## Direção: documentos sobre uma superfície clara

O Carreira Guiada ajuda a organizar uma busca de emprego e avançar por etapas.
A linguagem visual parte dos documentos desse trabalho: currículo, ficha de
vaga, agenda, mensagem e registro de prática. Use ilustração plana, espaço
livre e uma hierarquia que permita reconhecer o recurso antes de ler a página.

Banners e diagramas têm fundo claro e neutro. O azul marca uma informação
relevante, um caminho ou o passo atual. Fundo escuro fica nas demonstrações de
terminal; formulários e documentos aparecem em superfícies claras dentro delas.

Toda peça publicada precisa de título dentro da arte. Mantenha uma peça
principal por seção; acrescente outra somente quando explicar uma etapa distinta.
Fichas de produção e detalhes técnicos ficam fora do README.

## O que fica fixo e o que pode variar

| Fica fixo | Pode variar conforme o recurso |
|---|---|
| Paleta por função, família tipográfica e hierarquia | Título, subtítulo e objeto principal |
| Fundo claro dos banners, sem vinheta ou brilho | Até dois objetos auxiliares com função explicável |
| Ilustração plana, frontal e com contornos uniformes | Estado mostrado, como ação marcada ou mensagem recebida |
| Margens, alinhamentos e proporção de cada tipo de peça | Uma expressão destacada no título, quando necessária |
| Cabeçalho e posição das informações nos GIFs | Conteúdo de terminal, documento ou portal fictício |
| Digitação visível e tempo de leitura por cena | Três a cinco etapas, conforme a tarefa |

Uma funcionalidade nova usa esse mesmo conjunto. Mudanças de paleta, técnica
de ilustração ou moldura precisam atualizar este guia e apresentar o efeito
no conjunto, antes de virar referência para as próximas peças.

## Paleta por função

| Função | Cor | Uso |
|---|---|---|
| Fundo claro | `#F6F8FB` | Banners, diagramas e área externa das ilustrações |
| Papel | `#FFFFFF` | Folhas, fichas e documentos |
| Texto principal | `#0F1B2D` | Títulos, conteúdo e contornos |
| Texto secundário | `#4A5A70` | Subtítulos e rótulos |
| Linha discreta | `#D5DDE8` | Divisores decorativos, sem função de texto |
| Azul de destaque | `#2864ED` | Traços, marcações e passo atual |
| Azul para texto | `#1F4FC2` | Rótulo do recurso ou expressão destacada sobre claro |
| Azul suave | `#E4EEFF` | Pequenos preenchimentos auxiliares |
| Ciano | `#60D9F4` | Destaque pequeno; texto somente sobre terminal escuro |
| Terminal | `#07152E` | Área escura das demonstrações |
| Texto do terminal | `#F3F7FF` | Conteúdo principal sobre escuro |
| Texto secundário do terminal | `#A4BCDF` | Rótulos e informações de apoio sobre escuro |
| Azul claro do terminal | `#6DA7FF` | Títulos e marcações textuais sobre escuro |

Nos banners, use como referência visual pelo menos dois terços de área neutra
e cerca de um sexto ou menos de azul, incluindo o azul suave. Reserve ciano
para um ou dois detalhes. São critérios de composição, não percentuais medidos
automaticamente. Evite preencher todo o objeto principal com azul saturado.

Contrastes calculados sobre as cores nominais: texto principal/fundo claro,
16,25:1; texto secundário/fundo claro, 6,61:1; azul para texto/fundo claro,
6,68:1; texto do terminal/terminal, 16,92:1. Ciano sobre o fundo claro tem
contraste insuficiente para o texto deste padrão. Não use azul de destaque
como texto no terminal. A exportação ainda precisa de conferência visual;
esses cálculos não certificam a acessibilidade de uma imagem inteira.

## Tipografia e composição dos banners

Use DejaVu Sans, com Arial como alternativa disponível no ambiente. Escolha
uma delas para todo o lote, incluindo os rótulos das ilustrações. Reserve
DejaVu Sans Mono, Menlo ou Consolas para comandos e saída de terminal.
Não misture fontes manuscritas, serifadas ou fontes diferentes por recurso.

Letras têm preenchimento uniforme. Não aplique sombra, halo, relevo, contorno,
gradiente ou textura ao texto. A riqueza visual vem da composição e dos
objetos que explicam a atividade.

O banner usa proporção 3:1 e exportação de 2172 × 724 pixels. A base de
composição é 1086 × 362, renderizada em 2×. Não amplie uma imagem pequena
para apresentá-la como alta resolução. Diagramas extensos podem usar outra
proporção, mantendo paleta, tipografia e regras de ilustração.

| Elemento na base de composição | Padrão |
|---|---|
| Margens | 48 px laterais; 36 px superior e inferior |
| Texto | Metade esquerda da área útil; alinhado à esquerda |
| Ilustração | Metade direita, com intervalo mínimo de 32 px para o texto |
| Rótulo do recurso | 16 px, sem fita ou caixa ao redor |
| Título | 48 px, negrito, até duas linhas; entrelinha 1,05 |
| Subtítulo | 22 px, até duas linhas curtas; entrelinha 1,25 |
| Frase para iniciar no chat, se necessária | 16 px, depois do subtítulo |
| Rótulos da ilustração | Pelo menos 16 px; até três rótulos curtos |

As medidas são da base, antes da exportação em 2×. Se o texto não couber,
reescreva ou retire conteúdo secundário. Preserve as margens e a escala.
Use até três camadas principais: rótulo, título e subtítulo; a frase de chat
é uma quarta camada opcional. A marca completa aparece no banner de abertura
e no cabeçalho dos GIFs, sem competir com o nome do recurso nas demais peças.

## Ilustrações com uma linguagem comum

Use formas planas, vista frontal, contorno de 4 a 5 px na imagem exportada
e terminações arredondadas. Preencha com papel ou azul suave, reservando azul
saturado para pequenas marcações. Sobreposições usam deslocamento e contorno.
Evite 3D, reflexos, metal, sombras difusas, textura fotográfica e colagem rasgada.

| Recurso | Objetos que explicam a atividade |
|---|---|
| Currículo e perfis | Documento, cartão de perfil ou ficha de projeto |
| Busca e candidatura | Ficha de vaga e lista de campos |
| Retornos e retomada | Mensagem, agenda e marcador de etapa |
| Entrevistas | Balão de conversa e caderno de ensaio |
| Empresa e propostas | Ficha com lupa ou documentos para comparação |
| Carreira e modelos | Alternativas organizadas em fichas comparáveis |
| Meu plano | Fichas de agora, próximas semanas e direção profissional |
| Minha evolução | Registro de práticas e linha do tempo |

O objeto precisa explicar uma ação daquele recurso. Aviões decorativos,
montanhas, foguetes, esferas, confetes e brilhos não cumprem essa função.
Conquistas podem aparecer como registros com critério; evite medalhas ou selos
que sugiram certificação profissional. Não desenhe crescimento, notas ou
percentuais como resultado comprovado sem evidência correspondente.

Ilustrações conceituais não mostram botões, menus ou painéis de um aplicativo
próprio. O projeto funciona no chat e nas ferramentas disponíveis. Telas de
terminal e portal pertencem às demonstrações, identificadas como tais.

## Moldura e movimento dos GIFs

A base é 1120 × 700, exportada em 2240 × 1400 pixels. Mantenha o mesmo
cabeçalho, margens laterais de 40 px, título de 40 px e subtítulo de 23 px.
Conteúdo principal usa pelo menos 20 px; rótulos de apoio, pelo menos 16 px.
Comandos ficam em fonte monoespaçada, sem alterar a fonte dos títulos.

O cabeçalho traz a marca à esquerda e a natureza da demonstração à direita:
"Simulação fictícia" ou "Terminal real com dados fictícios". A área de ação
fica entre o subtítulo e a nota inferior. Use um painel único de terminal ou
conversa à esquerda e documento/portal à direita, com a mesma geometria ao
longo da animação. A borda é discreta, sem neon ou brilho.

Mostre o pedido que a pessoa faria, como "meu plano", antes do efeito.
Comandos internos como `./job plan show`, quando necessários, são identificados
como consulta feita pela IA. A demonstração não deve ensinar ao usuário leigo
que precisa operar a CLI técnica do projeto.

- Conte uma sequência: pedido, ação, resultado conferido e próximo passo.
- Mostre a digitação e quadros intermediários com mudança perceptível.
- Preserve o conteúdo completo por pelo menos cinco segundos antes da troca;
  use seis segundos como ponto de partida e aumente para cenas mais densas.
- Conte a pausa desde o último caractere. Quadros em que apenas o cursor pisca
  podem compor esse intervalo; contar só quadros individuais de cinco segundos
  não mede o tempo de leitura da cena.
- Use progresso apenas para as etapas da demonstração, com segmentos que
  correspondam às cenas. Não simule tempo real de busca ou percentual de conclusão.
- Evite flashes, zooms repetidos, mudanças de moldura e texto que salta de posição.
- Confira o primeiro quadro, cada cena completa, intermediários e a volta do loop.
- Exporte um PNG do quadro completo mais informativo, com o mesmo nome-base.

Dados, pessoas e empresas são fictícios. Valores ilustrativos recebem esse
contexto; não representam resultados garantidos. Uma saída capturada realmente
do código e uma conversa desenhada precisam de identificação diferente.

## Ficha de produção reutilizável

Preencha a ficha antes de gerar uma peça. Este exemplo já cabe no padrão:

```text
Tipo: banner de recurso, 3:1
Recurso: Meu plano
Pergunta respondida: como organizar o próximo passo com pouco tempo?
Rótulo: MEU PLANO
Título: Um objetivo. / Um próximo passo.
Subtítulo: Metas possíveis para o tempo que você tem.
Frase de chat: meu plano
Objeto principal: três fichas ligadas por um caminho curto
Rótulos nas fichas: Agora / Semanas / Direção
Estado mostrado: uma ação escolhida, sem promessa de emprego
Estilo: plano, frontal, contorno uniforme, fundo claro, azul nos destaques
Referência: guia visual vigente e uma peça já conferida contra ele
Conferência: título, acentos, cores, margens, objetos e leitura reduzida
```

Reutilize a mesma referência de estilo e a mesma ficha entre gerações. Evite
pedidos soltos como "futurista", "cinematográfico" ou "mais profissional".
Mantenha texto e ilustração como camadas editáveis no processo de composição;
o arquivo publicado já contém o título e todos os rótulos revisados.

Para GIFs, acrescente as frases da pessoa, as saídas esperadas, a natureza
real ou simulada de cada cena e os tempos de leitura. Os pontos de produção
atuais são [render_docs.py](../scripts/maintainers/render_docs.py),
[render_journeys.py](../scripts/maintainers/render_journeys.py) e
[render_personal.py](../scripts/maintainers/render_personal.py).
Os comandos estão em [CONTRIBUTING.md](../CONTRIBUTING.md#documentação-e-imagens).

## Conferência antes de publicar

- [ ] A peça usa o padrão deste guia e corresponde ao recurso implementado.
- [ ] Tem título dentro da arte, acentos corretos e letras sem efeitos.
- [ ] O banner permanece predominantemente claro, com azul em áreas limitadas.
- [ ] Objetos, traços, fontes e alinhamentos combinam com as peças vizinhas.
- [ ] A 900 px de largura, o conteúdo principal é legível; a 400 px, título e
  ideia central continuam reconhecíveis. Conteúdo essencial também está no texto
  da página e no texto alternativo; imagem reduzida não é sua única fonte.
- [ ] Foram conferidos contraste, cortes e sobreposições na exportação final.
- [ ] O GIF tem quadros intermediários, pausas de leitura e PNG correspondente.
- [ ] Saída real, simulação e ilustração estão identificadas corretamente.
- [ ] A revisão declara quais arquivos e cenas foram vistos; teste de código
  aprovado não substitui inspeção visual nem teste com pessoas.
- [ ] A substituição usa nome novo, referências atualizadas e a checagem de
  publicação descrita no CONTRIBUTING, preservando a procedência dos arquivos.

## Estado atual e aplicação do padrão

Este guia define o padrão das próximas criações e substituições. Sua inclusão
não altera as imagens existentes nem os estilos dos geradores. As peças antigas
servem para conferir conteúdo e funcionalidades; não são aprovação automática
da nova direção visual.

Na inspeção de novembro de 2026, os banners escuros, as duas ilustrações de
planejamento/evolução propostas e as molduras dos GIFs ainda diferiam entre si.
As novas ilustrações propostas também precisam de adaptação antes de serem
tratadas como referência. A aplicação deve começar por elas e pela moldura de
planejamento, seguir para o banner de abertura e depois cobrir as demais peças.

Ao adaptar um GIF, ajuste seu gerador e exporte o par GIF/PNG junto. Registre
no PR os arquivos migrados, as referências usadas e as verificações executadas.
Revise a peça no contexto da página. Uma exceção necessária precisa ser descrita
aqui antes de ser repetida; um resultado isolado do gerador não muda o padrão.
