# Como contribuir

Comece por uma issue com o problema que quer resolver. Use exemplos inventados
e diga o resultado esperado. Para mudanças amplas, combine o escopo antes de
implementar. Vulnerabilidades seguem [SECURITY.md](SECURITY.md).

## Preparar o ambiente

Use macOS ou Linux, Git, Python 3.11 ou superior e
[uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone https://github.com/everton-dgn/carreira-guiada.git
cd carreira-guiada
uv sync --locked
git config --local core.hooksPath .githooks
git switch -c fix/descricao-curta
```

O hook pertence a este checkout. Leia [.githooks/pre-commit](.githooks/pre-commit)
antes de ativá-lo. Não use currículos ou contas reais para desenvolver.

## Fazer uma alteração

1. Localize a regra em [AGENTS.md](AGENTS.md) e o contrato em
   [docs/CONTRATOS.md](docs/CONTRATOS.md).
2. Faça a menor mudança que resolve o problema. Cubra mudanças de comportamento
   com um teste que falhe antes da correção.
3. Atualize o guia afetado. Skills em `.agents/skills/` e `.claude/skills/`
   devem permanecer iguais.
4. Execute os testes e confira os arquivos preparados para commit.

```sh
uv run --locked python -m unittest discover -s tests -p 'test_*.py'
git add README.md
uv run --locked python scripts/check_publication.py --staged
git diff --cached
```

`git add README.md` é só um exemplo. Adicione explicitamente os arquivos da
sua alteração. A checagem lê os blobs do índice, inclusive quando o arquivo
da pasta já foi corrigido depois de um `git add`. Se ela bloquear, confira
localmente `git diff --cached --name-only` e corrija o item indicado. Não
publique valores privados em logs para pedir ajuda.

Mudanças no fluxo externo também passam pela [suíte de navegador](docs/VALIDACAO.md#navegador-e-e-mail-fictício).
Ela usa Chromium headless e serviços fictícios locais. As dependências do grupo
`browser` são opcionais para quem usa o projeto e necessárias para essa suíte.

Configure sua identidade Git com um e-mail de privacidade do GitHub se não
quiser expor o endereço pessoal. Nome e e-mail dos commits são públicos.
Confira também a identidade usada pela ferramenta que fará o merge. A
configuração local não controla um merge criado pela interface do GitHub.
Para manter uma identidade pública específica, prepare o merge localmente e
confira seus metadados antes de publicá-lo, conforme o [guia de releases](docs/RELEASES.md).

## Abrir o pull request

Explique o problema, o resultado da mudança e como verificou. Use branches
como `fix/descricao-curta`, `feat/descricao-curta` ou `docs/descricao-curta`.
Commits seguem Conventional Commits, por exemplo
`fix: preserve pending application state`.

Os guias e as instruções de conversa fazem parte do produto. Use `feat:` ao
adicionar uma orientação, um percurso ou uma capacidade; use `fix:` ao corrigir
um comportamento ou uma instrução incorreta. O versionador também aceita
commits `docs:` como novidade para que uma mudança no guia não fique sem versão.
Outros tipos de manutenção geram patch; `chore(release):` apenas prepara os
metadados da versão e não inicia outro incremento.

A CI verifica privacidade, testes e links locais da documentação. Integrações
usam merge commit, preservando o histórico. Não há merge automático de bots.

## Documentação e imagens

Use frases curtas, dados fictícios e passos que alguém sem experiência técnica
consiga acompanhar. Identifique ilustrações e simulações como tais. Inclua
texto alternativo e uma versão estática para animações importantes.

```sh
uv run --locked --group docs python scripts/maintainers/render_docs.py
uv run --locked --group docs python scripts/maintainers/render_journeys.py
```

O gerador usa uma fonte de texto (DejaVu Sans ou Arial) e uma monoespaçada
(DejaVu Sans Mono, Menlo ou Consolas) disponíveis no sistema. Confira acentos
e legibilidade antes de publicar. Não copie fontes de terceiros para o projeto.

## Licença das contribuições

Envie somente material que você tem direito de distribuir sob a
[licença MIT](LICENSE). Preserve avisos obrigatórios de terceiros. As
dependências mantêm suas próprias licenças; não copie o código delas sem
verificar as condições. O projeto não exige cessão exclusiva de direitos.

## Preparar uma versão

O [guia de releases](docs/RELEASES.md) explica o cálculo da versão, a preparação
dos arquivos e a publicação após a CI. A automação usa Python, Git e a CLI do
GitHub; o uso do projeto por candidatos não depende dessas ferramentas de release.
