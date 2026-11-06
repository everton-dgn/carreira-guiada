---
name: fontes
description: Ajudar a pessoa a descobrir e avaliar fontes públicas de vagas quando ela pedir ou aceitar ajuda.
---

Use a entrada técnica `research save` para registrar o parecer e `research
list`, `get` (com `record_id`) ou `suggestions` para consultar. O comando só
registra informação; não navega nem concede permissão. A API abaixo documenta
os campos. Nunca substitua a avaliação de segurança da candidatura por este parecer.

Ajude somente após pedido ou aceite. Pesquise informação pública com as ferramentas disponíveis, sem transmitir dados pessoais. Não há lista de sites padrão. Confira identidade, origem oficial, evidência independente e pedidos de dados; registre sinais e incertezas observados. Um relato é opinião atribuída, não prova. Popularidade não garante segurança. Não contorne bloqueio ou CAPTCHA, nem baixe anexos executáveis. Não inclua segredos em registros.

Use `DueDiligence(root).save(data)` com `kind`, `subject`, `url`, `checked_at`, `identity`, `official_origin`, `data_requests`, `red_flags`, `evidence` e `uncertainties`. Cada evidência tem `url`, `observation`, `kind` (`official`, `independent`, `report`). Datas têm fuso; URLs são HTTPS públicas sem parâmetros. Estados de identidade e origem: `confirmed`, `unknown`, `contradictory`; dados: `ordinary`, `unknown`, `dangerous`. `list()`, `get(id)` e `suggestions()` consultam pareceres. Cada revisão cria ID.

Sugestões exigem o parecer `site` mais recente favorável para a mesma URL e revalidação antes do uso. Pareceres `company` e `vacancy` não alteram essa lista. Avalie cada vaga como `vacancy` e cada destino de redirecionamento como `site`. Se um redirecionamento comprometer a fonte sugerida, registre também um novo parecer `site` para a URL original, com a evidência do redirecionamento; registrar somente a URL de destino não retira a original das sugestões. Não adicione fontes ao perfil: a pessoa escolhe e aprova. Consulte docs/EMPRESAS.md.
