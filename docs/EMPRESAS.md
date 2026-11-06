# Pesquisa de empresas e vagas

Peça à IA: "analise esta empresa antes de eu me candidatar". Ela pesquisa
fontes públicas e explica o que encontrou, com data e endereço. Confira
presença oficial, vínculo do anunciante e domínio de cada redirecionamento.
Um portal conhecido não valida a vaga ou o recrutador. A
[FTC](https://consumer.ftc.gov/articles/job-scams) informa que anúncios
fraudulentos também aparecem em sites e redes legítimos.

Compare relatos recentes de empregados e candidatos, com quantidade, datas e divergências. Diferencie opinião de fato e preferência pessoal de sinal de fraude. Investigue jornada, rotatividade, mudanças de requisito e restrição de equipamento. Pressão, pagamento e pedidos indevidos de dados são sinais a registrar. Um relato isolado não prova crime nem bloqueia toda a empresa.

Exemplo fictício: a empresa Aurora existe e publica vagas em seu canal oficial. Um anúncio atribuído a ela usa um recrutador que pede pagamento e não aparece nesse canal. Resultado: não seguir este anúncio; verificar no canal oficial. A empresa não é acusada. Dois relatos recentes descrevem jornadas diferentes; são opiniões atribuídas, não prova. Na entrevista, pergunte como as horas extras são registradas.

Salário fictício observado: R$ 8.000 a R$ 10.000 por mês, CLT, para desenvolvedor pleno em Salvador, amostra desconhecida. A faixa não garante oferta. Compare cargo, local, senioridade, contrato, moeda e período; calcule estatística somente quando equivalência e amostra forem comprovadas. Não misture categorias agregadas ou dados incompatíveis.

O campo opcional `salary_observations` aceita itens com `url`, `checked_at`, `role`, `location`, `seniority`, `contract`, `currency`, `period`, `minimum`, `maximum` e `sample_size` (inteiro conhecido ou null). O módulo registra dados, sem calcular médias ou pesquisar na rede. Cada parecer é privado e imutável. Uma análise registrada exige revalidação antes do uso.

Para o agente: `research save` recebe `kind` (`site`, `company` ou `vacancy`),
`subject`, `url`, `checked_at` com fuso, `identity` e `official_origin`
(`confirmed`, `unknown` ou `contradictory`), `data_requests` (`ordinary`,
`unknown` ou `dangerous`), `red_flags`, `uncertainties` e `evidence`.
`red_flags` e `uncertainties` são listas de textos; evidências têm `url`, `observation` e `kind`
(`official`, `independent` ou `report`). URLs são públicas, HTTPS, sem parâmetros.
`red_flags` registra riscos que justificam não recomendar; relatos isolados
ou conflitos ainda em investigação ficam como evidências e incertezas.

O resultado é `avoid`, `pending` ou `consider`. Este último exige identidade
e origem confirmadas, dados comuns, evidências oficial e independente e nenhuma
incerteza ou sinal impeditivo. Ele não substitui a segurança da candidatura,
aprova fontes, nem concede `alta_confianca` automaticamente. `research list`,
`get` com `record_id` e `suggestions` consultam os registros. Sugestões de sites
usam a verificação mais recente por URL; uma revisão antiga importada depois
não reabilita um site. A pessoa escolhe e aprova os links antes da busca de vagas.
