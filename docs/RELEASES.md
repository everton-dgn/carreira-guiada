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
| `fix: repair behavior`, `perf:` ou `revert:` | 1.2.4 |
| `chore(deps): update parser` ou `build(deps-dev): update tools` | 1.2.4 |
| `feat!: change contract` ou rodapé `BREAKING CHANGE:` | 2.0.0 |
| `docs:`, `test:` e manutenção sem os casos acima | Sem nova versão |

Um exemplo de `BREAKING CHANGE:` dentro de um bloco de código não altera a
versão. Essa mesma regra de incremento vale antes de 1.0.0.

## Preparar a alteração

Use uma branch de trabalho e deixe a árvore limpa. Não prepare na main.
Primeiro busque as tags e confira o plano, que não altera arquivos:

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

O campo `[tool.carreira-release] prerelease = true` mantém as versões marcadas
como experimentais no GitHub. Altere esse campo por PR quando houver uma
decisão de estabilidade. O valor não é deduzido do número da versão.

## Se uma publicação falhar

Leia o erro na aba Actions antes de repetir. Se a tag já foi criada no commit
correto e a criação da release falhou, uma nova execução reutiliza a tag.
Se a release já corresponder ao conteúdo validado, nada é recriado.
Tags divergentes e notas conflitantes são preservadas e interrompem a publicação.

Para retomar, abra o workflow `Release` na aba Actions, escolha a main e
informe o ID da execução aprovada de `Checks` para um push na main. O ID é o
número ao final do endereço da execução. O script valida essa origem de novo.
Não informe um ID de teste de PR nem apague ou mova uma tag para contornar erro.

Os testes de publicação usam um repositório temporário e uma API fictícia.
Eles não criam tags ou releases em contas reais.
