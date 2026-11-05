# Validação

O Carreira Guiada usa testes com dados fictícios e pastas temporárias. A suíte não envia
candidaturas, cria contas, responde mensagens nem opera seleções reais.

## Como executar

```sh
uv run --locked python -m unittest discover -s tests -p 'test_*.py'
```

## Cenários cobertos

- Onboarding: primeiro emprego sem currículo, importação de Word, PDF ilegível,
  correção de dados, resposta "não sei", tópicos pulados, parada e retomada,
  permissões individuais e conexão de e-mail adiada ou recusada.
- Currículos: extração, fatos confirmados, versões por especialidade, geração
  de PDF e Word, aprovação, integridade e preservação dos arquivos originais.
- Busca e candidatura: filtros de salário e contrato, informação ausente,
  decisão restrita a uma vaga, duplicidade, cadastro, preenchimento, correção
  e confirmação de envio.
- Retornos: vínculo de e-mail, lembretes repetidos, formulário complementar,
  questionário pessoal, rascunho aprovado, agendamento e resposta negativa.
- Interrupções: sessão expirada, resultado incerto, parada, retomada,
  autorização antiga e consulta parcial da caixa postal.
- Privacidade: recusa de dados sensíveis nos registros operacionais e
  separação dos dados pessoais na área privada.
- Pacote: links entre documentos e igualdade das skills dos aplicativos.
- Fontes: início sem sites, links adiados durante o currículo, aprovação dos
  endereços, mudança de perfil e bloqueio de pesquisas fora do escopo aprovado.
- Publicação: leitura do conteúdo preparado no Git, bloqueio de arquivos
  privados, links simbólicos, credenciais e metadados inesperados nas imagens.
- Versionamento: cálculo por commits, preservação das notas revisadas,
  preparação limitada aos arquivos de versão e publicação com API simulada,
  incluindo falhas de CI, conflito de tag e retomada de publicação parcial.

`tests/test_job_journey.py` exercita conversas de preparação pela CLI real.
`tests/test_job_process_journey.py` exercita busca, candidatura e retorno com
portal e caixa postal simulados. Os processos desses percursos bloqueiam
conexões de rede e abertura de subprocessos para impedir efeitos externos.
As conversas são roteiros de teste, não um estudo com pessoas reais.
As imagens do Claude Code e do Codex CLI também são ilustrações. Não comprovam
uma integração executada nesses aplicativos ou um envio para um portal real.

A automação do GitHub executa a suíte em Linux com Python 3.11 e 3.13 e
em macOS com Python 3.13. O resultado de cada execução fica na aba
[Actions do projeto](https://github.com/everton-dgn/carreira-guiada/actions).

Antes de um commit, confira os arquivos preparados para publicação:

```sh
uv run --locked python scripts/check_publication.py --staged
```

Essa checagem reconhece padrões conhecidos, não todo dado pessoal possível.
Ela complementa a revisão humana e não comprova ausência absoluta de segredos.

Para guardar os diálogos e currículos fictícios, informe um diretório externo
novo em `JOB_JOURNEY_REPORT` ou `JOB_PROCESS_REPORT`, respectivamente. Esses
relatórios são opcionais e não devem entrar na cópia distribuída.

## Alcance e limites

Os testes verificam o controle local e as orientações previstas nos roteiros.
Não comprovam autenticação em portais, funcionamento de cada interface externa,
instalação em todos os sistemas operacionais ou uma campanha por vários dias.
O comportamento do modelo diante de páginas e mensagens reais também exige
verificação durante o uso. A IA precisa de ferramentas autenticadas para
navegar e consultar e-mails.

Dados salvos permitem retomar; não mantêm a IA trabalhando depois que sua
execução termina. Antes de compartilhar a pasta após usar ou alterar o
projeto, confira que dados privados, anexos, backups e relatórios ficaram
fora dela.
