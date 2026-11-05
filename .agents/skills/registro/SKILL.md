---
name: registro
description: Persistir oportunidades, aliases, objetivos, autorizações de ação, resultados, capacidades e mensagens no banco privado como único registrador, relendo antes e depois, e devolver a próxima ação segura. Usar em toda gravação do fluxo. Não executa navegador, não envia nada.
---

# Registro

Leia "Registro", "Duplicidade e estados" e "Contagem" em
[AGENTS.md](../../../AGENTS.md) e a API de `Workflow` em
[docs/CONTRATOS.md](../../../docs/CONTRATOS.md).

## Responsabilidade

O principal é o registrador. Delegado só escreve após transferência explícita
e exclusiva; nunca dois escritores. Sem designação, devolva uma proposta.

## Chamadas

- Oportunidade: `./job opportunity` com chave principal (portal + ID público
  ou URL canônica), aliases, empresa, cargo, localidade, payload avaliado.
  Candidatura não é oportunidade. Em conflito de identidade, preserve a
  evidência e resolva antes de liberar ação externa.
- Objetivo: `./job goal` com critérios explícitos; não sobrescrever objetivo
  ativo incompatível.
- Decisão local: `./job decision` registra uma ausência aceita pela pessoa
  somente naquela oportunidade e versão do perfil. Preserve os filtros gerais.
- Autorização: `./job action authorize` antes de pesquisa, leitura de e-mail,
  cadastro, preenchimento, envio, resposta, agendamento ou lixeira. Cada ação
  tem ID próprio. Exige perfil aprovado, permissão,
  vaga elegível e, para envio, versão de currículo aprovada. Deve falhar após
  parada, em duplicata e com resultado incerto pendente.
- Resultado: `./job action complete` com `confirmed`, `uncertain` ou
  `not_received` e evidência breve. Relato sem evidência não é confirmação.
- Capacidade: `./job capability` com provedor, apelido, horário, estado e
  evidência. Sessão expirada revoga.
- Mensagens: `./job email` conforme [emails](../emails/SKILL.md).
- Etapa pessoal: `./job transition` pode concluir `candidate_pending` somente
  com relato explícito em `user_confirmation` e evidência, sem contar novo envio.
- Parada e retomada: `./job stop`, `./job resume-work`.

Payloads vão por stdin. Nunca grave documento, credencial, corpo integral de
e-mail ou endereço pessoal em evidência.

## Disciplina

- Releia o estado antes de gravar e depois de gravar. Diferencie gravação
  confirmada de tentada.
- Falha de gravação bloqueia só as ações externas dependentes; pesquisa e
  leitura continuam.
- Conte chaves únicas. Aliases, fichas e e-mails não somam candidaturas.
- Devolva ao coordenador: chave, estado efetivo, evidência, próxima ação
  segura e cobertura recebida da busca.
