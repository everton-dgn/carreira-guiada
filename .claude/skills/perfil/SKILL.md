---
name: perfil
description: Preencher, revisar, corrigir ou aprovar o perfil da pessoa, uma pergunta por vez, a partir das perguntas devolvidas por profile status. Usar quando a pessoa quer montar o perfil, mudar preferências, permissões, limites ou contas. Não usar para buscar vagas ou enviar candidaturas.
---

# Perfil guiado

Leia "Perfil, consentimento e permissões" em [AGENTS.md](../../../AGENTS.md)
e o esquema em `templates/profile.json` e `scripts/job/profile.py`. A pessoa
lê [docs/ONBOARDING.md](../../../docs/ONBOARDING.md) se quiser; você não
precisa mandá-la ler nada.

## Ciclo por pergunta

1. Chame `./job profile status --json`. Use `next_section`, `missing` e
   `questions`. Apresente somente a primeira pergunta pendente, com o exemplo
   devolvido. Não invente perguntas, ordem ou valores padrão.
2. Aceite "não sei" quando a pergunta permitir ausência. Explique em uma linha
   o efeito ("sem piso, vagas sem salário seguem conforme sua escolha de
   informação ausente").
3. Grave uma resposta com `./job profile answer <seção>`, recebendo por stdin
   `field` e `value`. O comando preserva os demais campos automaticamente,
   inclusive respostas dentro de `salary`. Para permissão `allow`, acrescente
   `confirmed: true` somente quando a pessoa tiver autorizado aquela ação.
   Nunca mostre JSON à pessoa. `profile save` fica reservado à substituição
   deliberada de uma seção completa, como "pergunte antes para tudo".
4. Passe à próxima pergunta, confirmando de forma breve correções e valores
   importantes. Avise no início que o progresso fica salvo e que pode voltar
   com `iniciar`; não repita o mesmo aviso a cada resposta.
5. Quando `missing` ficar vazio, mostre um resumo legível por seção, sem
   expor contatos além do necessário, e pergunte "está tudo certo?".
6. Só com "sim" explícito chame `./job profile approve --version <n>` com a
   versão exibida no resumo. Se a versão mudou, releia e mostre de novo.

Antes de fazer uma pergunta, confira os fatos do currículo e as respostas já
confirmadas no chat. Se a resposta já estiver lá, registre-a e siga. Informação
extraída de anexo precisa ser conferida pela pessoa antes desse reaproveitamento.
Para quem não entende níveis ou tipos de contrato, explique uma opção por vez
com o efeito prático e confirme a interpretação. Não confunda "não sei o que
significa" com "não tenho preferência".

Se uma dica de [ONBOARDING.md](../../../docs/ONBOARDING.md#dicas-durante-o-preparo)
ajudar a decisão atual, explique-a antes da pergunta, em uma frase. Diferencie
preferência de exigência, mínimo privado de pretensão pública e autorização
da rodada de confirmação por vaga. Não transforme a dica em resposta da pessoa.

## Traduzir as respostas para o sistema

Campos como `salary.floors` identificam uma pergunta dentro do objeto `salary`.
Use o campo exatamente como veio, por exemplo `salary.floors`, com
`profile answer`. Pode salvar o salário parcialmente; a aprovação exige
completar as perguntas restantes. Sem piso definido, não pergunte sobre uma
faixa que cruza o piso; o controle mantém confirmação como proteção futura.
Traduza respostas naturais para os códigos do esquema. Não apresente códigos,
listas vazias nem níveis numéricos como instruções à pessoa. Ao ouvir "qualquer
modalidade", registre remoto, híbrido e presencial com os mesmos nomes usados
na extração das vagas. Os títulos de cargos podem ter sinônimos: confirme com a
pessoa as variações aceitas e registre-as, sem alterar o cargo do anúncio.

## Fontes da busca

Peça os links escolhidos pela pessoa e ajude a copiar o endereço no navegador.
Registre em `sources.urls`; "deixe para depois" corresponde a `[]`. Não
mostre esse código à pessoa. Explique que o currículo pode continuar e a busca
espera pelos links e pela aprovação. Não sugira um catálogo próprio.
Se a pessoa pedir ou aceitar ajuda para encontrar fontes, siga
[fontes](../fontes/SKILL.md): pesquise opções públicas, verifique antes de
sugerir e registre a escolha. Não acrescente sugestões automaticamente.
Para acrescentar ou remover uma fonte, confirme a lista completa.

## Permissões

Explique cada ação em uma frase antes de perguntar e registre a resposta
literal como `allow`, `ask` ou `deny`:

- `research`: procurar vagas nos portais.
- `register`: cadastrar a pessoa em um portal novo.
- `fill`: preencher formulários de candidatura.
- `apply`: clicar em enviar.
- `email_read`: ler e-mails das contas informadas.
- `email_reply`: responder e-mails com rascunho aprovado.
- `email_trash`: mover mensagens individuais para a lixeira.
- `schedule`: aceitar horário de entrevista.
- `assessment`: ajudar em testes quando as regras do teste permitirem.

"Pergunte sempre antes" é `ask`. "Pode fazer" é `allow`. "Nunca" é `deny`.
Sem resposta, fica `ask`. Nenhuma permissão é inferida de outra.
Ao registrar `allow`, inclua também o nome da ação em `confirmed`. Se a pessoa
preferir "pergunte antes para tudo", salve todos os padrões `ask` de uma vez.
Caso contrário, conduza cada ação pendente antes da aprovação do perfil; salvar
uma primeira permissão não significa que as demais foram discutidas.

## Regras

- Piso salarial: pergunte em linguagem simples por regime; não sugira valor.
  Separe o mínimo privado da pretensão que pode ser publicada.
- Contas: provedor, apelido e endereço. Nunca peça senha, token ou cookie.
- A pessoa informa somente o e-mail ou escolhe deixar para depois. Reuse o
  endereço de contato quando ela pedir; o agente escolhe o apelido interno.
  Se o serviço não puder ser identificado, pergunte se ela usa Gmail, Outlook
  ou outro, explicando que é o aplicativo onde costuma ler as mensagens.
  O controle de e-mail atual aceita Gmail e Outlook. Se for outro provedor,
  explique essa limitação antes da aprovação e ofereça deixar o acompanhamento
  para depois, mantendo o endereço de contato. Não prometa uma conexão que
  `capability` não suporta nem troque a conta por conta própria.
- Sessões de navegador são observadas com `capability`, usando um apelido
  interno, sem pedir endereço de e-mail nem acrescentar uma conta ao perfil.
  Reutilize a sessão verificada; peça login só quando o portal exigir. O alias
  `public` pode representar um formulário que dispensa login. Isso não dispensa
  autorização da ação, verificação da vaga ou conferência do destino.
- O modo chat é automático. Não pergunte por executor, duração, ciclos ou
  intervalo. Se a leitura de e-mail foi recusada e não há conta registrada,
  a etapa de conexão é dispensada.
- Mudança material depois da aprovação invalida a aprovação; avise e repita o
  resumo antes de aprovar de novo.
- Esta skill não busca, não envia, não lê e-mail.
