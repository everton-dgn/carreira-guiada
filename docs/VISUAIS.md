# Créditos visuais

Os arquivos desta pasta explicam o fluxo sem expor documentos ou contas.
Todas as conversas e endereços das demonstrações são fictícios.

| Arquivo | Origem e finalidade |
|---|---|
| `assets/job-cover.png` | Ilustração original gerada com a ferramenta integrada de imagens para a capa deste projeto. |
| `assets/inicio-guiado.gif` e `.png` | Demonstração ilustrativa do onboarding, renderizada pelo script do projeto. |
| `assets/candidatura-guiada.gif` e `.png` | Demonstração ilustrativa de aprovação, confirmação, pausa e retomada. |

As animações não são gravações de contas reais nem evidência de candidaturas
enviadas. Há uma alternativa estática e um percurso em texto junto de cada GIF.

A capa preserva a identificação de origem C2PA da ferramenta geradora.
O verificador permite somente esse arquivo exato, conferido por hash. Uma
substituição exige nova revisão da imagem e dos metadados antes de atualizar
essa referência. As outras imagens aceitam apenas os blocos necessários ao
desenho e à animação.

## Recriar as demonstrações

Execute `uv run --locked --group docs python scripts/maintainers/render_docs.py`.
O código usa Pillow e uma fonte disponível no sistema. As fontes não são
redistribuídas. Confira o resultado visualmente antes de publicar.

## Direção da capa

Briefing: capa editorial panorâmica para um guia de candidaturas no chat,
fundo de papel claro, verde escuro e detalhes em verde-lima. Currículo de papel,
balões de conversa e um caminho de pequenos cartões representam etapas guiadas.
Texto: "job" e "Sua próxima oportunidade começa com uma conversa." Sem nomes,
contatos ou marcas de portais. Foi usada a ferramenta integrada de imagens.

Os materiais visuais originais são distribuídos sob a licença do projeto,
na medida dos direitos aplicáveis. Não são usadas capturas de produtos de
terceiros ou marcas de plataformas de vagas.
