---
name: presenca
description: Conduzir a revisão opcional de LinkedIn e GitHub, com posicionamento baseado em fatos, sugestões privadas e aprovação separada antes de publicar. Usar no onboarding ou quando a pessoa pedir para melhorar sua apresentação profissional.
---

# Presença profissional

Leia [PRESENCA-PROFISSIONAL.md](../../../docs/PRESENCA-PROFISSIONAL.md) e as
regras de dados e navegador em [AGENTS.md](../../../AGENTS.md).

1. Reaproveite o objetivo de carreira e os fatos confirmados. Ofereça LinkedIn,
   GitHub quando pertinente, ambos, depois ou pular. Salve a escolha explícita
   com `presence choose`: `decision` (`now`, `later`, `skip`), `topics`
   (`linkedin`, `github`) e `confirmation`, JSON por stdin.
2. Em `now`, peça apenas o link do perfil escolhido. Não pergunte por senha.
   Confirme que pertence à pessoa e qual material ela autoriza analisar. Leitura
   de perfil não autoriza mensagens, contatos, candidaturas ou mudança pública.
   Esses links não entram automaticamente nas fontes de busca de vagas.
   Salve o link imediatamente com `presence source`, usando `topic` e `source`,
   antes da leitura externa. Na retomada, consulte `presence show` e reaproveite
   `reviews[topic].link` já dado, sem pedir a mesma informação novamente.
   O link fica separado de `source`, que pode ser `candidate_text` quando o
   rascunho veio de texto colado. Preserve ambos; versões antigas ficam em `history`.
3. Se o perfil estiver indisponível, use o texto fornecido pela pessoa, com
   `source: candidate_text`. Explique o limite da análise. Não contorne login,
   bloqueio de automação ou privacidade para obter o perfil.
4. Prepare diagnóstico priorizado e textos prontos conforme o guia: LinkedIn
   completo, posicionamento coerente e GitHub com README e projetos selecionados.
   Separe fatos confirmados de sugestões. Se não houver projetos, ajude a
   apresentar o que existe; não invente repositórios ou experiência.
5. Salve com `presence draft`: `topic`, `content`, `source` (link HTTPS limpo ou
   `candidate_text`). Leia `presence show` somente para retomar o texto privado.
   Mostre uma seção por vez. Cada alteração gera nova versão e retira a
   confirmação de revisão anterior.
6. Quando a pessoa conferir, use `presence finish` com `topic`, `version` e
   `confirmation`. Isso conclui a revisão local e nunca autoriza publicação.
   Para aplicar, mostre texto exato, conta, destino e visibilidade e obtenha
   autorização específica. Preserve o conteúdo público anterior para reversão.
   Sem ferramenta ou permissão do serviço, guie a pessoa na aplicação manual.
7. Salve o resultado observado e a próxima ação no checkpoint. Alteração com
   resultado incerto exige conferência antes de repetir. Não declare aplicado
   apenas porque o rascunho ficou pronto. Retome o onboarding com `start`.

`later` e `skip` liberam o restante do preparo sem repetir a oferta em todo
início. A pessoa pode reabrir a revisão quando quiser com nova escolha.
Não publique salário mínimo, e-mail de login ou outro dado privado por padrão.
