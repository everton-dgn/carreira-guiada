# Sua apresentação profissional

Depois de preparar o currículo, a IA oferece revisar o LinkedIn e, quando
fizer sentido para sua área, o GitHub. Você pode escolher um, os dois, deixar
para depois ou pular. Não precisa criar uma conta para procurar vagas.
Se quiser voltar a essa etapa, diga "vamos revisar meu LinkedIn" ou "quero
melhorar meu GitHub". A escolha e as sugestões ficam salvas no projeto privado.

## Começar pelo trabalho que você procura

A IA reaproveita os cargos, a experiência e os fatos já confirmados. Compara
sua apresentação com o tipo de vaga desejado e identifica o que está difícil
de encontrar ou entender. Se faltar uma evidência, pergunta por ela; não
transforma interesse em experiência nem inventa resultados.

Você recebe uma proposta de posicionamento: como se apresentar, quais
experiências destacar e quais projetos demonstram suas habilidades. A mesma
história profissional deve fazer sentido no currículo e nos perfis. Uma
mudança de público ou de área pede sua decisão antes de reescrever tudo.

## LinkedIn

Envie o link do seu perfil. Se ele não puder ser aberto, copie as seções no
chat; a IA continua pelo material recebido. Login é feito por você na página
oficial. Ela não pede sua senha nem lê mensagens ou contatos para essa revisão.

O trabalho inclui:

- Título profissional: uma versão recomendada, com o cargo pretendido e as
  especialidades que você realmente tem. Explique siglas que prejudiquem a leitura.
- Sobre: apresentação direta do que você faz, experiências que sustentam isso
  e o tipo de oportunidade procurada, sem promessas ou adjetivos vazios.
- Experiências, formação e habilidades: datas coerentes com o currículo,
  responsabilidades claras e resultados comprovados. Preserve trabalhos simultâneos.
- Destaques e imagem de apresentação: sugira projetos, portfólio e uma direção
  para a capa; use somente materiais e links que você autorizou tornar públicos.

A IA também ajuda a conferir localização, modalidades, cargos e disponibilidade.
As opções de visibilidade para recrutadores são uma decisão sua. O LinkedIn
informa que o modo restrito a recrutadores não garante sigilo completo em
relação ao empregador atual. A IA explica essa escolha antes de alterar a
configuração. [Visibilidade no LinkedIn](https://www.linkedin.com/help/linkedin/answer/a507508/making-your-profile-visible-or-hidden-from-recruiters).

## GitHub para quem trabalha com tecnologia

Envie o perfil e escolha quais repositórios podem ser analisados. Projetos
privados e código de empregadores ficam fora, salvo autorização específica.
Um repositório público de terceiros pode servir como evidência de uma
contribuição sua; isso não autoriza modificá-lo.

A IA prepara uma proposta concreta para:

- README do perfil: apresentação, especialidades demonstradas, projetos
  selecionados, contribuições e um contato público escolhido por você.
- Repositórios em destaque: seleção alinhada aos cargos, com explicação do
  problema resolvido e da sua participação real.
- Página inicial de cada projeto escolhido: descrição, demonstração disponível,
  instalação reproduzível, limitações e imagens sem dados privados.
- Consistência dos links e da apresentação: retire links quebrados da proposta,
  identifique conteúdo desatualizado e priorize as mudanças pelo efeito esperado.

O README, a biografia e os itens fixados são partes configuráveis do perfil,
conforme a [documentação do GitHub](https://docs.github.com/en/account-and-profile/concepts/personal-profile).
Não fabrique contribuições, estrelas, seguidores, avaliações ou atividade no
calendário. Não prometa que um perfil receberá determinada posição na busca.

## Conferir e aplicar

A IA apresenta o diagnóstico e os textos prontos, uma seção por vez. Você pode
pedir ajustes sem perder a versão anterior do seu perfil público. A revisão
local não publica nada. Antes de qualquer alteração pública, confira o texto
exato, a conta, o destino e a visibilidade e autorize aquela alteração.

Se você corrigir uma experiência ou retirar um fato do currículo, as sugestões
que usavam essa informação voltam para revisão. Seus textos e as versões
anteriores continuam salvos. A IA refaz o trecho afetado antes de pedir nova
aprovação; uma publicação anterior precisa ser conferida no próprio perfil.

Com ferramenta conectada e ação permitida pelo serviço, a IA pode conduzir a
aplicação aprovada. Sem essa capacidade, ela abre o destino e guia você para
colar o conteúdo, uma seção por vez. Depois confere o resultado observado ou
registra que ainda falta conferência. Não declare uma publicação por ter
preparado o rascunho ou clicado em salvar.

Se disser "deixe para depois", seus textos continuam salvos e você pode seguir
com o currículo ou a busca. Uma publicação interrompida é conferida no destino
antes de qualquer nova tentativa, inclusive ao voltar em outro dia.

## Contrato de publicação

A revisão local pode acontecer antes do onboarding. Para a aplicação pela IA,
o perfil precisa estar aprovado e o objetivo ativo deve incluir `profile_publish`.
Inclua essa ação ao criar o objetivo, quando a pessoa pedir publicação.
Se a campanha ativa não a incluir, confirme que a pessoa quer acrescentar essa
atividade e use `goal-extend`. A campanha mantém a data de início, a meta e
as candidaturas contadas. Isso não concede permissões nem autoriza publicar
um texto; cada alteração pública ainda exige a confirmação específica abaixo.
Não use `replace_version` apenas para acrescentar uma atividade.

Prepare uma seção por vez. Guarde o diagnóstico em uma nota privada e salve
em `presence draft.content` somente o texto exato a publicar naquela seção.
Inclua em `fact_ids` os IDs dos fatos ativos e confirmados usados no texto.
Use uma lista vazia somente quando a seção não depender de fatos do currículo.
Mostre o texto, o link, a conta autenticada, a seção e a visibilidade observada.
Confirme que a conta pertence à pessoa e preserve o conteúdo anterior fora do
registro operacional, em `.job/presence-notes/`, com arquivo exclusivo por
versão, diretório com modo `0700` e arquivos com modo `0600`, sem seguir links
simbólicos nem sobrescrever notas existentes. Separe diagnóstico e cópia do conteúdo anterior
do texto fornecido pela pessoa. Não use `presence source` para essas notas:
alterar a fonte invalida o rascunho. `presence finish` registra a revisão;
a autorização de publicação é uma confirmação separada para aquele conteúdo.

Use `action authorize` com `action: profile_publish`, `owner`, `generation`,
`channel: {provider, account}` da sessão observada, `user_confirmation` e
`publication` com todos os campos abaixo. A permissão `deny` bloqueia;
`ask`, inclusive quando omitida no perfil, exige confirmação. `allow`
também exige confirmação por publicação.

| Campo de `publication` | Conteúdo |
|---|---|
| `topic` | `linkedin` ou `github`. |
| `version` | Número da versão atual, já conferida com `presence finish`. |
| `section` | LinkedIn: `headline`, `about`, `experience`, `education`, `skills` ou `featured`. GitHub: `bio`, `profile_readme`, `pinned_repositories` ou `repository_readme`. |
| `destination` | Link HTTPS exato salvo na revisão, sem rastreadores, credenciais ou fragmentos. Para um repositório, use a revisão daquele endereço. |
| `visibility` | Público (`public`), conexões (`connections`) ou privado (`private`), conforme a opção realmente disponível e aprovada no serviço. Não altere configurações de privacidade por inferência. |
| `content_sha256` | SHA-256 dos bytes UTF-8 de `presence show.reviews[topic].content`, sem acrescentar espaços ou quebras de linha. |

Imediatamente antes de alterar o serviço, use `action check <id>` com `owner`
e `generation`. A resposta devolve o vínculo conferido em `publication`.
Mudança de texto, fonte, versão, perfil, objetivo, sessão ou parada impede usar
uma autorização antiga. Confira também a página e a conta na ferramenta.
O controle local não detecta uma troca de conta feita dentro do navegador.
Se a conta observada divergir da conta aprovada, suspenda somente a publicação.
Esses comandos registram e validam o protocolo; não publicam conteúdo sozinhos.

Depois da ação, confira a página final e use `action complete <id>`. Para
`confirmed`, envie `evidence_source: destination_page`, `evidence_url` igual
ao destino autorizado, `publication_sha256` do texto observado, `checked_at`
e evidência curta sem dados pessoais. Clique sem confirmação usa `uncertain`.
Para resolver `not_received`, confira no destino que a mudança não ocorreu e
informe a mesma página autorizada com `evidence_source: destination_page`;
não informe `publication_sha256`. Uma versão nova não libera repetição enquanto
houver autorização aberta ou resultado incerto para a mesma seção e destino.
Na retomada, leia `action show <id>` para recuperar conta, destino, seção,
visibilidade e hash daquela tentativa. Essa leitura funciona mesmo durante
parada ou com autorização expirada e não permite executar a ação novamente.
Confira o texto no histórico de `presence show` pela versão e pelo hash salvos.
Se o serviço salvar conteúdo diferente, mantenha `uncertain` e mostre a
diferença à pessoa. Não declare `not_received` nem altere o hash aprovado para
liberar outro envio. Confira limites do campo antes de pedir a aprovação.

## Ajustar a estratégia com evidências

Ao revisar uma rodada, compare vagas compatíveis, candidaturas confirmadas e
retornos recebidos. Se houver pouco retorno, examine uma hipótese por vez:
aderência dos cargos, clareza do currículo, projetos demonstrados ou filtros
estreitos. Mostre a proposta e seu motivo antes de mudar o perfil. Não reduza
salário, altere disponibilidade ou afrouxe restrições por conta própria.

A preparação ajuda a apresentar fatos relevantes. Ela não garante entrevistas
ou contratação e não exige publicar conteúdo diariamente nem enviar mensagens
em massa a recrutadores.
