---
name: emails
description: Consultar as caixas de e-mail registradas no perfil pela integração autenticada, identificar mensagens de processos seletivos, vinculá-las a oportunidades e etapas e registrar cobertura por conta. Usar quando a pessoa pede para ver e-mails de vagas ou dentro de uma rodada com email_read permitido. Responder, agendar ou mover para a lixeira exige autorização própria por mensagem.
---

# E-mails de processos seletivos

Leia "E-mails e etapas complementares" em [AGENTS.md](../../../AGENTS.md).

## Gate

Perfil `approved`, conta em `connections`, permissão `email_read` e sessão
autenticada observada por `./job capability`. Sem sessão: registre cobertura
pendente para aquela conta e siga as demais fontes. Login é da pessoa.

Explique qual conta e intervalo estão sendo consultados, sem expor o endereço
no resumo. Separe mensagem lida, etapa pendente e resposta enviada. Mostre
ação da pessoa e prazo verificado mesmo com a campanha parada; a exibição
não retoma envios. Consulta parcial continua incompleta na retomada.

## Consultar

Antes de ler uma conta, registre `action authorize` com `action: "email_read"`,
canal da conta e `scope_key` da consulta. Confira `action check <id>` com
`owner` e `generation` imediatamente antes do acesso. Erro impede executar.
Uma conta não autoriza outra. Ao
terminar a consulta, registre `action complete` com evidência. As chamadas de
cobertura registram o alcance, mas não substituem essa autorização.

1. Busque por empresas, vagas e portais acompanhados, inclusive mensagens
   lidas e em todas as pastas. Use janelas de tempo finitas; na primeira
   consulta, janela curta declarada; nas seguintes, sobreponha a anterior.
2. Registre por conta: período coberto, horário da última conferência
   completa, estado (`complete`, `partial`, `auth_required`, `unavailable`).
   Paginação interrompida fica `partial` e preserva o ponto de retomada.
   Use `./job mail-coverage begin|account|finish` conforme
   [operação](../../../docs/OPERACAO.md); `show` consulta o estado salvo.
3. Identifique cada mensagem por provedor + apelido da conta + ID. Sem ID
   estável, referência acessível e identidade provisória.
4. Confira remetente, empresa, cargo e destino dos links no canal oficial.
   Não abra link com token; não execute anexo.
5. Registre com `./job email` (ingestão) só os campos necessários: provedor,
   apelido, ID, oportunidade quando conferida, chave da etapa, tipo, resumo
   curto, prazo com fuso quando comprovado, URL pública segura. Nunca corpo
   integral, contatos, tokens.

## Classificar

- Confirmação de recebimento sem ação: evidência, sem pendência.
- Pedido concreto (teste, entrevista, complemento, resposta): etapa via
  [etapas](../etapas/SKILL.md). Repetição do mesmo pedido atualiza a etapa.
- Rejeição: encerra só as ações que a mensagem tornou desnecessárias;
  preserva o envio histórico. A ingestão não cancela etapas sozinha. Confira o
  vínculo e use `transition` com `state: "cancelled"` e evidência para cada
  etapa daquele processo que deixou de fazer sentido.
- Vínculo duvidoso: `vinculo_a_verificar`, mensagem preservada.

## Ações que exigem autorização própria

- Responder: `email_reply` e um "pode enviar" da pessoa para aquele rascunho e
  destinatário. Mostre o rascunho antes. Depois: `action authorize`,
  `action check <id>` com `owner` e `generation`, envio único e
  `action complete` com evidência.
- Agendar: `schedule`, disponibilidade confirmada, autorização para o horário.
- Antes de agendar ou mover para a lixeira, use `action check <id>` com
  `owner` e `generation`. Erro impede executar a ação autorizada.
- Lixeira: `email_trash`, por mensagem individual com ID e conta, sem etapa
  pendente, categoria autorizada pela pessoa. Mover para a lixeira do provedor
  (restaurável), conferir o destino, relatar qual mensagem e como restaurar.
  Nunca conversa inteira, nunca esvaziar lixeira, nunca exclusão permanente.
  Grave as categorias combinadas com `./job cleanup-rules save` antes de
  autorizar a primeira mensagem. Ofertas, entrevistas e testes são preservados.

## Devolver

Por conta: cobertura e estado. Por mensagem relevante: empresa, etapa, ação
necessária, prazo conhecido e referência segura. Marcar como lida não conclui
etapa. Avise quando só parte da caixa foi conferida e preserve o ponto de
retomada. Não prometa consultas futuras fora da execução ativa no chat.
