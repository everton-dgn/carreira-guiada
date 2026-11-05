---
name: avaliar-empresas
description: Descobrir empresas e priorizar vagas por reputação como empregadora, cultura de trabalho e condições de trabalho, com evidências e data de consulta. Usar para comparar oportunidades ou quando a pessoa pergunta se uma empresa é boa. Não autoriza contato, cadastro, candidatura ou compra.
---

# Avaliar empresas

Leia "Busca e cobertura" em [AGENTS.md](../../../AGENTS.md) e as preferências
aprovadas do perfil. Esta skill pesquisa e recomenda; a decisão de prosseguir
continua com os filtros do perfil e com a pessoa.

## Descoberta e evidência

- Busque nas fontes do perfil aprovado, conforme
  [docs/FONTES.md](../../../docs/FONTES.md). Se precisar de outra origem para
  conferir a empresa, explique e peça a inclusão antes de pesquisar nela.
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

Comparação curta com empresa, vaga, URL, evidências, incertezas e
recomendação (`priorizar`, `considerar`, `informacao_insuficiente`), com data
da consulta e links próximos às afirmações. Separe política confirmada,
relato e inferência. Boa reputação não supera os filtros do perfil. Salário
estimado e relato salarial não são oferta da vaga.

Devolva as vagas priorizadas à [busca](../busca/SKILL.md) para deduplicação e
triagem. Empresa sem vaga compatível fica como prospecção, sem contar como
candidatura nem encerrar a rodada.
