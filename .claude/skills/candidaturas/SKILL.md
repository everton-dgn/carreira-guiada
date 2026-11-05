---
name: candidaturas
description: Coordenar uma rodada completa de busca e envio de candidaturas, do objetivo persistido à conclusão comprovada, com registro único e retomada. Usar quando a pessoa pede para procurar vagas, se candidatar, continuar a rodada ou ver o andamento. Pergunta, contagem ou revisão isolada mantém seu escopo.
---

# Conduzir candidaturas

Leia [AGENTS.md](../../../AGENTS.md) por completo e
[docs/OPERACAO.md](../../../docs/OPERACAO.md). Esta skill organiza a execução;
as regras estão no procedimento.

## Pré-requisitos

- Perfil `approved` (via `./job profile status`). Sem isso, volte a
  [perfil](../perfil/SKILL.md).
- Currículo `approved` para envio. Sem isso, busca e triagem podem seguir;
  envio não.
- Permissões: `research` para buscar, `fill` para preencher, `apply` para
  enviar. `ask` pergunta em linguagem simples no momento; `deny` não faz.
- Nenhuma parada ativa. Com parada, "continuar" ou "retomar" já é a resposta:
  use `./job resume-work` e siga. Só pergunte se a pessoa não disse nada.

## Objetivo

Reaproveite o pedido da pessoa e o objetivo salvo. Só quando faltar essa
escolha, pergunte se quer "procurar e enviar o que for compatível" ou "só me
mostrar as vagas". Persista com
`./job goal`. Não invente meta numérica, prazo ou orçamento. Se já existir um
objetivo ativo incompatível, explique o conflito antes de substituir. Objetivo
nativo do chat, quando existir, é complemento.

## Ciclo

1. Confira estado e ações `uncertain` com `./job status`. Resultado incerto
   bloqueia só o reenvio daquela vaga; a conferência no portal entra como item
   da rodada e as demais vagas seguem normalmente.
2. Confira sessões dos portais prioritários. Login é da pessoa: preserve a aba
   e peça "faça o login e me avise".
3. [busca](../busca/SKILL.md) produz um lote finito e a cobertura por fonte.
4. Para cada vaga: avaliação atual e duplicidade via `./job opportunity`,
   depois [seguranca](../seguranca/SKILL.md). Pendência afeta só aquela vaga.
5. Siga [envio](../envio/SKILL.md): cada ação tem sua própria autorização.
   Cadastro, preenchimento e candidatura não compartilham o mesmo ID.
6. Após cada ação, `./job action complete` com evidência. Não abra uma segunda
   autorização para a mesma ação já reservada.
7. Intercale etapas de e-mail autorizadas ([emails](../emails/SKILL.md) e
   [etapas](../etapas/SKILL.md)) quando `email_read` permitir.
8. Lote acabou e há consulta não coberta: próxima rodada. Parada pedida: pare.

## Relatório ao fim de cada rodada

Em linguagem simples: envios confirmados (com empresa e cargo), em dúvida,
aguardando a pessoa (com a ação exata), descartadas (motivo curto), e o que
vem a seguir. Explique que o trabalho depende da execução ativa no chat;
uma conversa aberta não mantém o trabalho em andamento.

Não marque objetivo concluído por lote terminado, formulário preenchido ou
clique. Conclusão exige cobertura do escopo e resultados comprovados.
