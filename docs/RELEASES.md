# Preparar e publicar versões

Este guia é para quem mantém o projeto. Quem procura emprego usa o
[guia de início](GUIA.md) e não precisa executar estes comandos.

O fluxo calcula a próxima versão pelos commits, prepara arquivos revisáveis
em uma branch e publica a release após a CI da main. As regras de
versionamento foram adaptadas do fluxo do boilerplate SolidJS para Python.
Não há dependência de Bun, Vite ou serviços de deploy.

## Como a versão é calculada

O ponto de partida é a maior tag `vX.Y.Z` alcançável pelo histórico atual.
Ela deve corresponder à versão do projeto. O cálculo ignora merge commits e
usa a mudança de maior impacto desde essa tag:

| Commit | Resultado a partir de 1.2.3 |
|---|---|
| `feat: add feature` | 1.3.0 |
| `docs: improve onboarding` | 1.3.0, pois o guia faz parte do produto |
| `fix: repair behavior`, `perf:` ou `revert:` | 1.2.4 |
| `chore(deps): update parser` ou `build(deps-dev): update tools` | 1.2.4 |
| `feat!: change contract` ou rodapé `BREAKING CHANGE:` | 2.0.0 |
| `refactor:`, `style:`, `test:`, `ci:`, `build:` e `chore:` | 1.2.4 |
| `chore(release): prepare v1.2.4` | Sem novo incremento |

Um exemplo de `BREAKING CHANGE:` dentro de um bloco de código não altera a
versão. Essa mesma regra de incremento vale antes de 1.0.0.

Prefira `feat:` para melhorias nos guias e nas instruções do agente, e `fix:`
para correções. O suporte a `docs:` mantém essas mudanças no cálculo quando
esse tipo já tiver sido usado. Toda alteração com um dos tipos aceitos gera
versão, exceto o preparo da própria release. Merge commits também ficam fora
do cálculo para não contar novamente os commits integrados.

## Preparar a alteração

Use uma branch de trabalho e deixe a árvore limpa. Não prepare na main.
Primeiro busque as tags e confira o plano, que não altera arquivos:

Confira também se a branch inclui a main atual. Se houver commits novos,
integre-os por merge normal, revise o resultado e valide antes de preparar a
versão. Se a main avançar novamente depois do preparo, confira o cálculo no
resultado integrado; uma versão preparada na branch pode ficar insuficiente.

```sh
git fetch origin --tags
uv run --locked python -m scripts.maintainers.release plan
```

Depois prepare a versão:

```sh
uv run --locked python -m scripts.maintainers.release prepare
git diff -- pyproject.toml uv.lock CHANGELOG.md
```

O comando altera somente a versão em `pyproject.toml`, o pacote local em
`uv.lock` e a seção correspondente de `CHANGELOG.md`. Não atualiza dependências.
A seção `## Unreleased` precisa existir uma única vez. Se contiver notas
revisadas, elas são preservadas; caso contrário, os commits geram as notas.
O resultado fica numa seção datada, e `Unreleased` continua disponível.

Confira as notas, execute os testes e o verificador de publicação descritos
em [CONTRIBUTING.md](../CONTRIBUTING.md), faça o commit dos três arquivos e
abra um pull request. O commit de preparação pode seguir o formato
`chore(release): prepare v0.2.0`, usando a versão calculada.

## Publicação após a integração

O pull request passa pela CI completa. A integração usa merge commit.
Antes de integrar, confira o nome público e o e-mail de privacidade escolhidos
para o autor e o responsável pelo commit. Um merge feito no site do GitHub
usa a identidade da conta; o `git config` do computador não a substitui.
Se precisar preservar outra identidade pública, prepare o merge normal no
checkout local com essa identidade e confira a árvore, os dois pais e os
metadados antes do push autorizado. Preserve as proteções da main e os checks;
se o servidor recusar, investigue o motivo sem contornar a regra.

Mudar a identidade dos commits futuros não remove metadados já publicados.
Corrigir o histórico exige um plano separado, cópia de recuperação, validação
das referências afetadas e autorização para a substituição. Commits e tags
reescritos mudam de identificação e perdem as assinaturas anteriores; cópias,
referências de PRs e caches podem continuar acessíveis. Consulte as
[limitações de remoção de dados no GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

Após o workflow `Checks` de um push na main terminar com sucesso, o workflow
`Release` confere novamente o resultado e publica a versão preparada.

Antes de escrever no GitHub, ele verifica:

- Origem do repositório, evento `push`, branch main, workflow esperado e
  resultado aprovado do job `quality`.
- Presença do commit testado e do código de publicação no histórico da main.
- Correspondência entre versão do projeto, lock, changelog e commits.
- Tag existente e conteúdo de release, para preservar publicações anteriores.

A automação cria uma tag anotada no commit testado e uma release com as notas
revisadas. Não altera a main, não cria aprovações ou checks e não integra PRs.
Ela usa Python da biblioteca padrão, Git e a CLI `gh` do runner. O token do
GitHub tem leitura de Actions e escrita de conteúdo somente no job de publicação.

O campo `[tool.carreira-release] prerelease = false` publica releases normais,
elegíveis para aparecer como a versão mais recente na página do repositório.
O projeto continua em desenvolvimento na série 0.x, conforme o README.
Uma release normal não é uma promessa de estabilidade ou de contratação.
Use `prerelease = true` somente quando quiser publicar explicitamente um
pré-lançamento, que fica fora da seleção de release principal do GitHub.
O valor não é deduzido do número da versão.

## Se uma publicação falhar

Leia o erro na aba Actions antes de repetir. Se a tag já foi criada no commit
correto e a criação da release falhou, uma nova execução reutiliza a tag.
Se a release já corresponder ao conteúdo validado, nada é recriado.
Tags divergentes e notas conflitantes são preservadas e interrompem a publicação.

Se o erro for "Prepare a versão calculada" e ainda não houver tag para a
versão preparada, a main pode ter recebido commits de impacto maior depois
do preparo. Reexecutar o workflow com os mesmos arquivos não corrige isso.
Abra uma branch de correção a partir da main atual e confira a última tag
publicada antes de alterar os metadados:

1. Reponha somente a versão do projeto em `pyproject.toml` e a do pacote local
   em `uv.lock` para a versão dessa tag. Preserve dependências e outras alterações.
2. Mova as notas da versão ainda não publicada para `Unreleased`, mantendo uma
   única seção com esse nome. Preserve todas as seções de versões publicadas.
3. Faça o commit dessa correção de preparo para deixar a árvore limpa. Rode
   `plan` e `prepare` novamente sobre os commits integrados, confira o diff e
   faça o commit dos três arquivos de versão.
4. Envie o PR, espere os checks e integre por merge normal. A CI da nova main
   passa a ser a origem da publicação. Não mova tags nem reescreva o histórico.

Se a tag da versão já existir, este procedimento não se aplica. Preserve-a
e investigue a divergência informada antes de qualquer nova publicação.

Para retomar, abra o workflow `Release` na aba Actions, escolha a main e
informe o ID da execução aprovada de `Checks` para um push na main. O ID é o
número ao final do endereço da execução. O script valida essa origem de novo.
Não informe um ID de teste de PR nem apague ou mova uma tag para contornar erro.

Os testes de publicação usam um repositório temporário e uma API fictícia.
Eles não criam tags ou releases em contas reais.
