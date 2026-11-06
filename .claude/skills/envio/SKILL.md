---
name: envio
description: Preencher e enviar uma vaga reservada, com perfil aprovado, currículo aprovado, elegibilidade e confiança confirmadas, autorização registrada antes do clique único e resultado conferido no portal. Usar somente dentro de uma rodada coordenada. Não busca, não registra como escritor, não repete envio incerto.
---

# Preenchimento e envio

Leia "Preenchimento e envio", "Duplicidade e estados" e "Segurança antes dos
dados pessoais" em [AGENTS.md](../../../AGENTS.md).

## Gate, todos obrigatórios

- Perfil `approved`.
- Vaga `eligible` na avaliação atual de `./job opportunity`, que considera
  decisões específicas registradas por `decision`. `evaluate` isolado mostra
  apenas a política geral e não aplica essas decisões.
- `alta_confianca` da [seguranca](../seguranca/SKILL.md).
- Currículo `approved` com hash conferido por `./job resume show <id>`; se houver
  mais de uma versão elegível, a pessoa escolhe.
- Permissão `fill` para preencher; `apply` para enviar (`allow`, ou `ask`
  respondido com sim para esta vaga). Pedido só de preencher para antes do
  clique.
- Ausência de envio anterior: banco e portal autenticado. Ação `uncertain`
  anterior bloqueia até `not_received` com evidência.
- Nenhuma parada ativa.

## Preencher

Após cada autorização de `register`, `fill` ou `apply`, use `action check <id>`
com `owner` e `generation` imediatamente antes do efeito. Erro impede executar;
preserve o estado e confira o destino antes de resolver a ação ou reautorizá-la.

- Se precisar criar cadastro, confira antes se a conta já existe. Só use
  `action authorize` com `action: "register"` para cadastro novo autorizado.
  Conclua esse registro separadamente. Login, senha, código e CAPTCHA ficam
  com a pessoa. Reutilize a conta nas outras vagas do mesmo portal.
- Antes de escrever ou anexar dados, registre `action authorize` com
  `action: "fill"`, a oportunidade, `resume_id` e `resume_sha256` da versão
  aprovada. Use o ID retornado durante o
  preenchimento. Conclua com `action complete` após conferir os campos;
  isso não confirma uma candidatura enviada.
  Se precisar corrigir antes do envio, autorize outro `fill` e confira o
  resultado. Preenchimento ainda aberto ou incerto bloqueia `apply` até ser
  conferido. Depois do envio, só uma etapa complementar própria permite novo
  preenchimento.
- Use contatos do perfil e fatos do currículo aprovado. Personalize em
  primeira pessoa. Não invente experiência, datas, formação, disponibilidade
  nem resposta eliminatória.
- Releia cada campo após escrever. Valor duplicado, parcial ou divergente:
  limpe e digite de novo, sem empilhar tentativas. Confira tudo antes de
  anexar, avançar ou enviar, inclusive telefone, cidade e remuneração.
- Dado obrigatório ausente ou ação exclusiva da pessoa (login, código, CAPTCHA,
  documento): preserve a aba, peça em uma frase, siga outra vaga.
  Antes de uma espera longa, registre o estado observado do preenchimento.
  Ao voltar, consulte `status`: autorização expirada vira `uncertain`. Releia
  o formulário e conclua essa ação com evidência do que foi preservado ou não
  recebido antes de autorizar uma correção. Não repita autorização incerta,
  não avance para `apply` nem registre confirmação sem conferir o destino.
- Desmarque seguir empresa e marketing, salvo instrução salva no perfil.
- Se houver pedido de dado familiar, registre o bloqueio e siga as demais
  vagas, sem pedir esse dado à pessoa. Documento obrigatório fica pendente da
  decisão da pessoa sobre digitar diretamente no portal, conforme a regra de
  segurança. Nunca peça número de documento no chat nem o copie.

## Enviar

1. `./job action authorize` com `action: "apply"`, vaga, perfil, versão do
   currículo e permissão. A autorização de preenchimento não libera o envio.
   Guarde o ID. Sem ID, não clique.
2. Confira `./job action check <id>` com `owner` e `generation`. Só após
   sucesso, confira a página e clique uma única vez.
3. Confira no portal. Confirmação inequívoca: `./job action complete` com
   `confirmed` e evidência breve (texto da confirmação, sem dados pessoais).
   Informe `checked_at` para a conferência e `submitted_at` somente para o
   horário de envio comprovado, ambos com fuso. Conferir hoje não significa
   ter enviado hoje. Sem horário comprovado, omita `submitted_at`: a confirmação
   histórica permanece, mas fica fora da meta do período.
4. Timeout ou resposta ambígua: `./job action complete` com `uncertain`
   imediatamente. Não clique de novo. Verifique a lista de candidaturas do
   portal; só `not_received` com evidência libera nova tentativa.

## Devolver

Chave da vaga, resultado observado, origem da evidência, horário, aba
preservada e próxima ação. Clique, formulário salvo ou tela de currículo não
comprovam envio. Um envio confirmado encerra só o envio inicial daquela vaga;
o coordenador continua.
