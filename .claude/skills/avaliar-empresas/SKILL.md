---
name: avaliar-empresas
description: Descobrir empresas e priorizar vagas por reputação como empregadora, cultura de trabalho e condições de trabalho, com evidências e data de consulta. Usar para comparar oportunidades ou quando a pessoa pergunta se uma empresa é boa. Não autoriza contato, cadastro, candidatura ou compra.
---

# Avaliar empresas

Leia [AGENTS.md](../../../AGENTS.md) e o
[protocolo de investigação](../../../docs/INVESTIGACAO-AGENTE.md). O pedido
pode começar sem perfil aprovado, currículo ou fontes de vagas. Pergunte a
empresa e a dúvida da pessoa, uma coisa por vez, aproveitando o que ela já
informou. Quando a pessoa escolher essa atividade, salve
`menu --choose company --remember`; assim a próxima sessão retoma a análise,
mesmo que antes estivesse no currículo. Criar um dossiê durante a busca
preserva a atividade escolhida. Se houver perfil aprovado, suas preferências
ajudam a contextualizar.

## Descoberta e evidência

- Consulte `company list` e `get` para retomar ou `company create` para criar
  o dossiê pedido. Nunca una homônimos por semelhança de nome.
- Combine a pergunta e os endereços públicos da investigação. Aproveite uma
  autorização explícita que já cubra esse alcance. Registre `research-scope
  grant` e confira `check` antes de cada consulta e redirecionamento. Se precisar
  ampliar, agrupe os novos endereços em uma pergunta clara. Não mude as fontes
  de candidatura. Login, bloqueio e fonte inacessível ficam como limitações.
- Identifique empregadora, consultoria e cliente final: cultura de um não
  comprova a do outro. Confirme domínio, país e entidade para não misturar
  homônimos.
- Cruze políticas oficiais, páginas de engenharia e avaliações independentes
  de funcionários. Observe data, quantidade, cargo, país e recorrência dos
  relatos; priorize os últimos 12 a 24 meses sem ocultar histórico relevante.
  Nota média, selo ou prêmio isolado não prova boa cultura. Reclamação de
  consumidor não comprova condição de trabalho.

## O que comparar

Gestão e autonomia; jornada real; engenharia e desenvolvimento profissional;
relação de trabalho (pagamentos, rotatividade, tratamento); equipamento fornecido e condições de uso, quando isso fizer parte das
preferências da pessoa.

Classifique a política de equipamento como `permitido`, `condicionado`,
`equipamento_corporativo` ou `nao_informado`, com fonte, data e alcance.
Trabalho remoto ou contrato PJ não comprova permissão. Não instale nem aceite
nada para verificar requisitos.

## Resultado

Grave uma revisão com `company revise` e confira `summary`. Separe fato,
relato e inferência; vincule inferências às evidências que as sustentam.
Agrupe cópias de um relato em uma única origem. Reclame Aqui e outras fontes
de consumidores ficam nesse contexto e não preenchem lacunas trabalhistas.
Mantenha perguntas, contradições e informação ausente visíveis. Não dê nota
geral, selo de segurança nem diagnóstico jurídico. A sugestão prática precisa
explicar a evidência e o efeito para a prioridade declarada pela pessoa.

Salário observado não é oferta. Preserve faixa, média ou mediana, cargo,
regime, local, moeda, período e amostra; desconhecido fica `null`. Não agregue
fontes incompatíveis nem transforme percentil em mínimo ou máximo. Registre
amostra ou metodologia ausente como limitação. Mostre a data da consulta e
revalide antes de usar informação antiga em uma decisão atual.

Salve `checkpoint` com fase `company`, o progresso e a próxima pergunta.
Ao parar, preserve dossiê e histórico. Retomada operacional não renova
escopos de pesquisa antigos. Nenhum parecer altera filtros ou permissões.

Devolva as vagas priorizadas à [busca](../busca/SKILL.md) para deduplicação e
triagem. Empresa sem vaga compatível fica como prospecção, sem contar como
candidatura nem encerrar a rodada.
