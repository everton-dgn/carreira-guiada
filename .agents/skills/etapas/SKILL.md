---
name: etapas
description: Executar etapas complementares de processos seletivos já registrados, como complemento cadastral, teste, entrevista, agendamento e resposta ao recrutador, com reserva única, autorização por ação e resultado conferido. Usar quando houver etapa pendente ou a pessoa pedir para cuidar de um retorno de empresa. Não responde teste pessoal nem impersona entrevista.
---

# Etapas complementares

Leia "E-mails e etapas complementares" e "Duplicidade e estados" em
[AGENTS.md](../../../AGENTS.md).

## Gate

Perfil `approved`, etapa vinculada a oportunidade conhecida, permissão da
ação específica (`fill`, `email_reply`, `schedule`, `assessment`) e nenhuma
parada ativa. `candidate_pending` só avança com resposta da pessoa.

## Executar

1. Liste etapas pendentes com `./job status`; ordene por prazo verificado,
   depois por antiguidade. Prazo ambíguo: `prazo_a_confirmar`, sem converter.
2. Reserve a etapa para um único executor. Contas distintas não autorizam
   executar o mesmo pedido duas vezes.
3. Antes da ação externa: `./job action authorize`. Execute uma vez. Depois:
   `./job action complete` com `confirmed`, `uncertain` ou `not_received` e
   evidência conferida no destino. `uncertain` bloqueia repetição.
4. Complemento cadastral: fatos confirmados do perfil e do currículo aprovado,
   reaplicando filtros e regras de dados pessoais. Registre uma etapa `form`
   (ou `additional_form`, `profile_update`, `fill`) e autorize `fill` com sua
   `step_key`. A candidatura precisa estar confirmada. Não reutilize a ação de
   preenchimento inicial nem abra outra candidatura.
5. Resposta ao recrutador: rascunho mostrado, "pode enviar" da pessoa para
   aquele conteúdo e destinatário.
6. Entrevista: só aceita horário com disponibilidade confirmada e autorização
   da pessoa. Mostre dia, mês, ano, hora e fuso antes de perguntar. Se faltar
   fuso, confira antes de marcar. Envie `schedule: {starts_at: ISO com fuso}`
   na autorização de `schedule`, ligada à etapa `interview` ou `schedule`.
   A confirmação cria outra etapa, `interview_attendance`, que depende da
   pessoa. Marcar horário não conclui a participação. Nunca participe nem
   responda em nome dela.
7. Teste: só com `assessment` em `allow`, ou `ask` respondido para esse teste,
   regras do teste permitindo auxílio e
   confirmação da pessoa para aquele teste. Teste de personalidade, autorrelato
   ou identidade fica `candidate_pending`. Nunca invente autorrelato.
8. Quando a pessoa disser que terminou a etapa pessoal, registre `transition`
   com `state: "completed"`, `evidence` e `user_confirmation` com esse relato.
   Só vale para `candidate_pending`. Passagem do prazo, abertura da página ou
   silêncio da pessoa não comprovam conclusão. Resultado de ação da IA continua
   por `action complete` com prova no destino.

## Devolver

Por etapa: empresa, tipo, estado efetivo, evidência, prazo, próxima ação, e o
que depende da pessoa com a ação exata. Etapas concluídas não contam como
novos envios de candidatura.
