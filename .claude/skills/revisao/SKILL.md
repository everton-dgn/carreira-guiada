---
name: revisao
description: Revisar regras, skills, agentes, documentação e registros do projeto Job em modo somente leitura, relatando defeitos com arquivo, linha, cenário e correção mínima. Usar em pedidos de "revise", "confira", "está certo?". Não edita, não envia, não altera perfil.
---

# Revisão somente leitura

Leia [AGENTS.md](../../../AGENTS.md), [docs/CONTRATOS.md](../../../docs/CONTRATOS.md),
[docs/OPERACAO.md](../../../docs/OPERACAO.md), [docs/FONTES.md](../../../docs/FONTES.md),
as skills em `.agents/skills/` e, quando o pedido abranger, o estado via
`./job status --json`.

## Regras

- Revisão autoriza leitura e parecer. Correção exige pedido de alteração.
- Não envie candidaturas, não altere perfil, não crie objetivo, não abra
  portais. Simule decisões com dados sintéticos.
- Não exponha valores pessoais no parecer.

## Cenários a verificar

- `iniciar` com instalação incompleta, perfil vazio, perfil em andamento,
  parada ativa e ação incerta: a próxima etapa proposta é a correta?
- Mudança de perfil após aprovação invalida a aprovação?
- Vaga com dado ausente segue a política de informação ausente do perfil,
  sem suposição?
- Envio: autorização antes do clique, clique único, `uncertain` bloqueia
  repetição, `not_received` exige evidência?
- Mesma vaga em dois portais: uma oportunidade, aliases, nenhum reenvio?
- Mesmo lembrete em duas contas: duas mensagens, uma etapa, nenhum envio?
- Lixeira: só individual, autorizada, sem etapa pendente, restaurável?
- Documentos: nenhuma skill ou doc pede, copia ou guarda documento, senha ou
  código?
- Limites: os documentos explicam que o trabalho depende da execução ativa
  no chat, sem instalar ou sugerir executor externo?
- Integração: nenhum documento afirma comando implementado que não existe na
  árvore?

## Formato do parecer

Para cada defeito: gravidade, arquivo e linha, cenário demonstrável, impacto,
correção mínima. Distinga validação estrutural, simulação e execução real
observada. Parecer de outro modelo é evidência a conferir.
