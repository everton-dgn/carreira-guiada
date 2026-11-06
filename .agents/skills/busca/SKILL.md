---
name: busca
description: Pesquisar vagas nos portais a partir do perfil aprovado, triar, deduplicar e registrar cobertura por fonte. Usar na etapa de pesquisa de uma rodada ou em pedido isolado de "procurar vagas". Não preenche, não envia, não grava como registrador sem designação.
---

# Busca de vagas

Leia "Busca e cobertura", "Elegibilidade pelo perfil aprovado" e "Duplicidade
e estados" em [AGENTS.md](../../../AGENTS.md), e as fontes escolhidas pela pessoa conforme
[docs/FONTES.md](../../../docs/FONTES.md).

## Gate

Perfil `approved` e permissão `research` (`allow`, ou `ask` respondido com
sim nesta rodada), `sources.urls` não vazio e alvo aprovado. Sem links, ajude
a pessoa a informá-los, sem escolher portais por ela. Sem perfil aprovado, volte a
[perfil](../perfil/SKILL.md).

## Executar

Leia `tabs status` antes de usar o navegador e siga
[procedimento de progresso e abas](../../../docs/OPERACAO.md#progresso-e-abas). Reutilize abas seguras,
reserve antes de abrir outra e respeite o limite global, inclusive se houver
outros agentes. Mostre progresso observado durante buscas demoradas.

Antes da consulta, peça ao registrador `action authorize` para `research`, com
o canal, `source_url` dentro das fontes aprovadas e `scope_key` identificando
portal e consulta. Confira `action check <id>` com `owner` e `generation`
imediatamente antes da pesquisa; erro impede executar. Depois, devolva a evidência
para `action complete`. Consultas diferentes têm escopos distintos.

1. Monte consultas a partir de cargos, tecnologias, modalidade e regimes das
   preferências aprovadas. Varie termos e acentos. Filtros de data e
   candidatura simplificada são opcionais, nunca a única busca.
2. Use somente os endereços de `sources.urls` e a prioridade combinada com a
   pessoa. Não há catálogo do projeto. Nova origem de pesquisa exige inclusão
   e aprovação no perfil antes da consulta.
3. Para cada anúncio, extraia o payload da vaga (campos em
   `scripts/job/policy.py`) sem preencher ausências com suposição.
4. Consulte duplicidade com `./job opportunity` antes de devolver o achado.
   Use a avaliação devolvida e separe `eligible`, `blocked` e `discarded`.
   `evaluate` isolado serve para conferir os filtros gerais, sem as decisões
   já registradas para uma vaga específica.
5. Em `blocked`, prepare a pergunta curta que resolve a dúvida (exemplo: "esta
   vaga não diz se é remota; quer que eu considere?"). Uma pergunta por vaga,
   só quando a pessoa estiver disponível; caso contrário, registre e siga.
   Para ausência que a pessoa aceitou somente nesta vaga, use `./job decision`
   com `opportunity_id`, os `reasons` atuais e `user_confirmation`. Releia o
   resultado. Não mude os filtros gerais nem preencha o anúncio com suposição.
   Se a pessoa não souber, mantenha a vaga pendente e continue as outras.
   Piso salarial, faixa que cruza o piso, bloqueio de empresa ou plataforma e
   identidade duvidosa exigem informação verificada; essa decisão não os libera.
   Mudança no anúncio ou no perfil exige nova avaliação e invalida a decisão.

## Devolver

Lote finito com: empresa, cargo, portal, ID ou URL pública, decisão e motivos
de `evaluate`, confiança preliminar, e próxima ação. Por fonte: consulta
usada, páginas percorridas, horário, último ponto verificado, pendências,
próxima consulta. Diferencie paginação concluída, parcial e fonte
indisponível. Resultado vazio não comprova esgotamento.

O registrador salva essa cobertura com `./job coverage save` e consulta com
`./job coverage show`. Não deixe o ponto de retomada somente na conversa.

## Limites

- Não clique em candidatar, não preencha dados, não anexe arquivo.
- Não marque vaga encontrada como enviada.
- Reputação e equipamento: [avaliar-empresas](../avaliar-empresas/SKILL.md)
  é priorização; informação ausente não bloqueia vaga elegível.
