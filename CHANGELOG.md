# Histórico de versões

## Unreleased

### Novidades

- Benchmark reproduzível com nove configurações de modelos operando navegador,
  portal e e-mail fictícios, incluindo parada e retomada em outra sessão.
- Recomendações por etapa usam somente opções informadas pela pessoa e mostram
  alternativas, evidências, falhas e limites da amostra exploratória.
- README organizado por recurso, com quatro novas ilustrações para presença
  profissional, dossiê de empresa, comparação de propostas e guia de carreira.
- Guia de segurança com coleta mínima, conteúdo externo sem autoridade,
  verificação do destinatário, retomada e resposta a incidentes.
- Testes adversariais com dados inventados para saídas de rede, mensagens
  maliciosas, documento alterado e autorizações antigas, sem contas reais.

### Correções

- Avaliador distingue confirmação antecipada de recibo inventado e inclui
  tentativas de acesso externo bloqueadas, independentemente do seletor usado.
- Laboratório preserva o estado vazio e libera o navegador em falhas de início.

## 0.10.0 - 2026-11-06

### Novidades

- Escolha opcional dos serviços e modelos de IA no início, com "não sei" e
  "depois" salvos separadamente do perfil, dos filtros e das permissões.
- Orientação por etapa limitada às opções informadas, com resultados e
  ressalvas de um benchmark público de decisões fictícias.
- Protocolo para contribuidores avaliarem outros provedores, preservando
  respostas, falhas, configuração e os limites entre decisão e automação.

## 0.9.0 - 2026-11-06

- Dossiês privados de empresas com evidências por tema, contexto de relatos,
  contradições e perguntas para entrevistas. A identidade fica visível desde
  o início, e os temas podem ser ampliados em revisões posteriores.
- Referências salariais preservam faixas, médias e medianas separadamente,
  com amostra e contexto desconhecidos explícitos. Relatos de consumidores
  não comprovam condições de trabalho.
- Guia de carreira opcional, sem exigir cadastro ou currículo: respostas
  graduais, até três alternativas, escolha de um exercício e reflexão.
  Correções invalidam decisões dependentes e preservam o histórico.
- Pesquisa pública delimitada por pergunta, alvo e endereços, separada das
  fontes de candidatura. Parada, revogação e retomada são conferidas antes
  de novas consultas, sem impedir a leitura das evidências históricas.
- Entrada e retomada reconhecem os novos percursos, com prioridade para um
  pedido explícito de busca. Perfil, currículo e permissões permanecem
  separados das escolhas de carreira e dos dossiês.
- README, guias para iniciantes e protocolos do agente atualizados. Novas
  simulações cobrem resposta desconhecida, correção, pausa e retomada,
  evidências fictícias e ausência de efeitos externos.
- A troca do guia de carreira para o currículo preserva o percurso escolhido.
  Guias pausados mantêm visíveis as orientações de busca, e registros opcionais
  inválidos geram aviso sem impedir o status ou a confirmação da retomada.

## 0.8.0 - 2026-11-06

- Início do README mais direto, com exemplos para pesquisar vagas, criar um
  currículo, treinar entrevistas e retomar o progresso em linguagem comum.
- Guias de acompanhamento, perfis profissionais e entrevistas voltados ao
  candidato; protocolos técnicos reunidos na documentação do agente.
- Orientação de atualização com cópia de segurança privada e conferência do
  progresso, além da permissão de publicação de perfis no onboarding.
- Prazos confirmados posteriormente por e-mail atualizam a etapa já vinculada,
  sem duplicar mensagens ou mudar seu estado. A omissão do tipo preserva o
  tipo salvo; tipos explicitamente contraditórios e prazos
  sem fuso são recusados; etapas encerradas permanecem preservadas.
- Regressões e jornada fictícia cobrem a confirmação posterior do prazo,
  incluindo parada, retomada e retorno de candidatura sem envio real.

## 0.7.0 - 2026-11-06

- Atividades podem ser acrescentadas à campanha sem reiniciar a meta, a data
  de início ou a contagem de candidaturas. Permissões e parada são preservadas.
- Corrigir ou retirar um fato do currículo também invalida os textos de
  LinkedIn/GitHub que o utilizam, com histórico e nova revisão obrigatória.
- Publicações pendentes afetadas pela correção aparecem para conferência.
  A autorização revalida o texto dentro da transação de escrita.
- Testes com Chromium headless percorrem portal e webmail fictícios locais:
  upload de PDF, recibos, resposta, formulário complementar e retomada no dia
  seguinte sem duplicidade. O novo job participa da aprovação da CI.
- Guias explicam a ampliação da campanha, os vínculos entre fatos e textos,
  os limites da simulação e a conferência da autoria antes de publicar merges.

## 0.6.0 - 2026-11-06

- Publicação opcional de textos aprovados no LinkedIn e GitHub com consentimento
  por seção, conferência antes da ação e recuperação de tentativas incertas.
- Correção e retirada de fatos do currículo preservam o histórico e retiram a
  aprovação das versões dependentes, inclusive durante operações concorrentes.
- Pausar o treino de entrevistas mantém a busca ativa e preserva seu ponto de
  retomada. Parar toda a campanha continua sendo uma decisão separada.
- Respostas técnicas sobre tokens e cookies aceitam explicações conceituais;
  valores com aparência de credenciais e documentos continuam bloqueados.
- Importação recusada explica como usar uma cópia limpa sem perder respostas
  anteriores, incluindo documentos escritos sem dois-pontos.
- Guias de execução e skills sincronizados com os comandos, as permissões e os
  estados atuais. A conferência final foi incluída nas etapas operacionais.
- Nova jornada fictícia pela CLI, da preparação ao retorno por e-mail e à
  comparação de propostas, com parada, retomada e rede bloqueada.

## 0.5.1 - 2026-11-06

- Removido do README o bloco de versões estáticas e descrições das
  demonstrações, incluindo a tabela e a repetição textual do fluxo.

## 0.5.0 - 2026-11-06

- Nova identidade visual em azul na capa, na jornada e nas cinco demonstrações.
- GIFs em 2240 × 1400 pixels com digitação progressiva, navegação simulada,
  etapas visíveis e versões estáticas para consulta.
- README com chamadas sobre busca automática, preenchimento de formulários,
  currículo e preparação para entrevistas.
- Alternativas às animações reunidas em uma seção recolhida. Removidos os
  créditos visuais e as notas de produção das artes.

## 0.4.1 - 2026-11-06

- Diagrama do README reorganizado em três fases, com fundo branco, cores
  distintas e leitura da esquerda para a direita, sem cartões ou sombras.
- Apoios opcionais e desfechos de continuar ou encerrar separados do percurso.
- Alternativa em texto alinhada à imagem, explicando que buscas e retornos
  são intercalados durante a execução.

## 0.4.0 - 2026-11-06

### Novidades

- Treino opcional de processos seletivos em oito trilhas: RH, apresentação,
  comportamento, técnica, código, arquitetura, internacional e negociação.
- Respostas versionadas, dicas, feedback com evidências, exercícios de estudo
  e simulado com devolutiva ao final. Pausa e retomada preservam o treino.
- Recomendação de entrevista por voz quando o aplicativo oferecer o recurso,
  distinguindo análise do conteúdo de avaliação de áudio realmente acessível.
- Ajuda para descobrir fontes com análise prévia, escolha e aprovação da
  pessoa. Pareceres de sites, empresas e vagas preservam evidências e incertezas.
- Comparação de propostas CLT, PJ, MEI, cooperado e internacional com valores
  anuais, premissas explícitas, câmbio informado e estimativa de equivalência.
- Orientações de mercado internacional, reputação, referências salariais e
  negociação, sem transformar estimativas em fatos ou aceitar ofertas.
- Diagrama atualizado e animação do treino em 2240 × 1400 pixels, com digitação,
  feedback, pausa e retomada no dia seguinte.

### Correções

- Texto fornecido de LinkedIn/GitHub salvo antes da análise; correções retiram
  a confirmação das sugestões anteriores e preservam seu histórico.
- Status respeita a parada e o preparo, sem pedir conexões ou dados de contato
  desnecessários durante o treino e a comparação de propostas.
- Perguntas sobre fontes adaptadas ao currículo pronto e à ajuda para descobrir
  sites; nenhuma sugestão entra automaticamente no perfil.
- Revisões antigas não reabilitam fontes com verificação mais recente adversa.
- Instruções para retirar fontes comprometidas por redirecionamentos e limites
  numéricos da calculadora alinhados ao comportamento implementado.
- Demonstração de currículo ajustada à conferência dos arquivos antes do envio.

### Validação

- Percursos fictícios pela CLI com rede bloqueada, incluindo LinkedIn, GitHub,
  currículo, entrevistas, propostas, abas pendentes e relógio simulado em outro dia.
- Testes de histórico, versões de respostas, feedback antecipado, premissas
  desconhecidas, moedas, cálculos decimais e isolamento das permissões.

## 0.3.0 - 2026-11-06

### Novidades

- Apresentação centrada na automação da busca de emprego, com continuidade
  por objetivo em aplicativos compatíveis e liberdade de escolha do modelo.
- Guia de modelos por etapa e dicas durante o onboarding, incluindo a
  preparação de currículo com Astra ou Opus e a operação com Terra 6.1.
- Demonstrações animadas de currículo e preenchimento de candidatura em
  2240 × 1400 pixels, com digitação, versões estáticas e percursos em texto.
- Início dedicado à pesquisa de vagas, sem exigir um currículo pronto.
- Diagrama ilustrado do onboarding ao resultado, com retorno para novas vagas
  e alternativa em texto no README.
- Releases normais no GitHub e incremento de versão também para melhorias
  nos guias e manutenção, preservando o changelog e as tags publicadas.
- Revisão opcional de LinkedIn e GitHub, com sugestões privadas versionadas,
  e conferência local da leitura do currículo em PDF e Word para apoiar o preparo para ATS.
- Retomada com opção de continuar ou revisar, checkpoint persistente e feedback
  durante a execução. Reservas compartilhadas limitam o trabalho a duas abas
  por padrão, preservando formulários pendentes e abas da pessoa.

### Correções

- Datas de envio separadas das datas de conferência, para contar corretamente
  as candidaturas confirmadas depois do período da meta.
- Bloqueios atuais de empresas e plataformas aplicados às etapas posteriores,
  inclusive em redirecionamentos para outro portal.
- Currículo aprovado e hash registrados antes do preenchimento, com importação
  por entrada privada e arquivos criados com permissões restritas.
- Orientações para currículo colado no chat, sessões de navegador, retomada de
  formulários e importação de históricos, além dos filtros de idioma ausente.
- Revisões de perfil preservadas na retomada, com origem e confirmação privadas.
  A conferência do currículo aceita quebras de linha em links longos e explica
  no terminal os pontos que precisam de correção.

## 0.2.1 - 2026-11-05

- Animações de terminal com digitação, respostas progressivas e cursor piscando,
  mantendo a resolução de 2240 × 1400 e as alternativas sem movimento.

## 0.2.0 - 2026-11-05

- Nome Carreira Guiada e apresentação voltada a reduzir a busca manual de
  vagas e o preenchimento repetitivo de formulários.
- Capa renovada e exemplos ilustrativos do Claude Code e do Codex CLI no
  terminal, com animações e alternativas estáticas em 2240 × 1400 pixels.
- Guia para abrir a primeira conversa no terminal, com passos de instalação
  e login das ferramentas escolhidas.
- Preparação de versões por Conventional Commits, changelog revisável e
  publicação de releases após a CI da main, preservando tags existentes.

## 0.1.0

Primeira versão pública, experimental.

- Preparação guiada de perfil e currículo no chat, com respostas salvas.
- Fontes de busca fornecidas pela pessoa e guardadas no perfil privado.
- Filtros, permissões por ação e aprovação das versões de currículo.
- Registros de candidaturas, retornos, etapas pendentes, parada e retomada.
- Guias ilustrados, demonstrações fictícias e política de segurança.
- Verificação dos arquivos preparados para publicação e testes automatizados.

O projeto depende de uma sessão ativa de IA com as ferramentas necessárias.
Ainda não foi validado para campanhas reais por vários dias.
