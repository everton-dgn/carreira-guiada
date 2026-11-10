# Benchmark de onboarding, currículo e carreira

Este ensaio compara o que o modelo decide e entrega em seis situações
fictícias de preparação. Cada configuração recebe os mesmos recortes de uma
conversa, com fatos suficientes para responder. Não há navegador, e-mail,
arquivos pessoais ou envio de candidatura. A resposta precisa conter o texto
que seria mostrado ao candidato, além das decisões estruturadas.

O ensaio complementa os testes de CLI e os laboratórios de navegador e
segurança. Ele não percorre uma conversa inteira, não prova que o modelo
salvou dados e não mede um currículo exportado em PDF ou lido por um ATS.

## O que é pedido

| Etapa | Situações | O que conferir na resposta |
|---|---|---|
| Onboarding | Pessoa sem currículo e sem foco; busca retomada com qualquer modalidade | Oferecer caminhos sem escolher pela pessoa; reaproveitar a resposta e preservar a campanha parada. |
| Currículo | Duas experiências simultâneas; correção de uma afirmação de liderança | Produzir um trecho utilizável, conservar datas e fatos, corrigir sem inventar conquistas nem sobrescrever a versão aprovada. |
| Carreira | Comparar até três caminhos com duas horas semanais; retomar um exercício | Respeitar o tempo disponível, manter salário desconhecido e propor uma prática local que a pessoa consiga realizar. |

A fixture em [preparation-benchmark.json](../tests/fixtures/preparation-benchmark.json)
contém os contextos, tipos e critérios de correção. O comando `prompt` exporta
os contextos e o vocabulário dos campos, sem revelar as respostas esperadas
nem os rótulos de falha crítica. Todos os modelos recebem o mesmo protocolo.
O piloto serve para conferir a coleta; depois de congelado o conjunto, seus
resultados só podem ser comparados com execuções do mesmo hash.

## Critérios de avaliação

A correção automática verifica todos os campos, seus tipos, respostas ausentes,
casos extras e violações factuais ou de autorização explicitamente declaradas.
Uma decisão que diz "não inventei" não comprova a fidelidade do texto livre.
Por isso o relatório separa a pontuação mecânica da revisão do conteúdo.

A revisão de conteúdo examina cada caso por estes critérios:

- Fundamentação: experiências, datas, disponibilidade e resultados precisam vir
  do contexto. Exemplos inventados devem ser reconhecíveis como exercícios.
- Utilidade: o currículo contém um trecho aproveitável; a comparação distingue
  atividades; o exercício tem uma ação concreta. Só prometer ajuda é insuficiente.
- Clareza: a pessoa entende o próximo passo, sem comandos técnicos ou um
  questionário desnecessário. O início oferece escolha sem impor uma carreira.
- Apresentação do currículo: títulos simples e datas legíveis, sem alegar
  aprovação em ATS. Meses, métricas e atribuições desconhecidos ficam ausentes.

Cada ressalva cita o caso e o trecho correspondente. A revisão identifica seu
responsável como humano ou modelo. Revisão feita por uma IA não é validação
com usuários reais nem opinião independente do mantenedor que conduziu a coleta.
Não calculamos uma nota estética nem escolhemos vencedor pela extensão do texto.

## Reproduzir ou contribuir com outro provedor

Esses comandos são para mantenedores. O candidato não precisa executá-los.

```sh
uv run --locked python scripts/maintainers/preparation_benchmark.py prompt
uv run --locked python scripts/maintainers/preparation_benchmark.py score --response resposta.json
uv run --locked python scripts/maintainers/preparation_benchmark.py verify --report docs/benchmarks/2026-11-09-followup-preparation.json
```

Envie a saída do primeiro comando a uma sessão nova do modelo, sem acesso a
arquivos pessoais ou ferramentas reais. A campanha ampliada usa os
[adaptadores restritos](BENCHMARK-ADVERSARIAL.md#clientes-da-campanha-ampliada)
com `laboratory_kind: preparation`. O cliente recebe a instrução de responder
diretamente; qualquer chamada à ferramenta fictícia também deixa a medição
inelegível, mesmo com JSON correto. Confirme o estado efetivo do cliente antes
de entregar o prompt. Uma instrução textual, sozinha, não comprova isolamento.

Guarde a resposta original, modelo, provedor, esforço, data, versão e hash da
fixture, hash do prompt, estado final da sessão e evidência de chamadas.
Não corrija o texto do modelo antes de pontuar. Falta de resposta, limite de
uso ou falha no cliente ficam inconclusivos, sem atribuir nota zero ao modelo.
Nunca publique identificadores privados, caminhos da máquina ou credenciais.

`verify` confere os hashes das respostas e dos registros de ferramentas,
recalcula as decisões e verifica as etapas e os trechos citados na revisão.
Ressalvas exigem uma nota explicativa. O estado da sessão e a contagem de
ferramentas têm tipos validados; o registro conhecido de ausência de chamadas
precisa corresponder à contagem zero. O hash preserva a integridade do registro.
Nas novas execuções, `client_evidence_path` também permite conferir a
inicialização restrita, modelo, esforço, resposta final e chamadas observadas
pelo cliente. As nove medições anteriores permanecem identificadas como
reaproveitadas; não recebem retroativamente essa prova adicional.
O comando preserva falhas de formato
registradas e não refaz a avaliação qualitativa.

A CLI rejeita chaves JSON duplicadas e casos duplicados. Pontuação perfeita
continua com `qualitative.status: not_reviewed`: acrescente a revisão de texto
como evidência separada no relatório, sem alterar a resposta original. Os
[limites e resultados](BENCHMARKS.md) precisam acompanhar qualquer recomendação.
