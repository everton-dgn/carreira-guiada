# Comparar propostas de trabalho

![Compare o pacote. Negocie com clareza. Salário, benefícios e custos na mesma conta.](assets/propostas-trabalho.png)

Esta comparação usa valores que você informa ou confirma. Ela ajuda a organizar
as diferenças entre CLT, PJ, MEI, cooperado e trabalho internacional. Não é
assessoria tributária ou jurídica, nem escolhe uma proposta por você. Antes de
uma decisão, confira impostos, contrato e condições com profissional habilitado
quando necessário. O agente verifica regras do regime, atividade e visto em
fontes oficiais adequadas ao caso, fora da calculadora.

O agente pergunta um dado por vez, em linguagem natural. Você pode dizer que
não sabe. Um valor desconhecido fica pendente; zero significa que você afirmou
que o valor é zero. Identifique estimativas e sua origem nas premissas. Não
peça para a calculadora inventar imposto, limite de faturamento ou câmbio.
Guardar um cenário não aceita proposta, muda seu piso pessoal nem autoriza
mensagem a uma empresa.

Para MEI, confira a ocupação permitida e os limites atuais no
[Portal do Empreendedor](https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/quero-ser-mei/servicos-para-mei).
A ocupação e o enquadramento precisam de conferência para o caso concreto. A
página oficial do Ministério do Trabalho explica o
[13º salário](https://www.gov.br/trabalho-e-emprego/pt-br/noticias-e-conteudo/2025/novembro/decimo-terceiro-salario-entenda-o-direito-regras-e-prazos-de-pagamento).
Os valores do exemplo abaixo são fictícios e não representam cálculo tributário.

## Exemplo anual

| Dado informado | CLT fictícia | PJ fictícia |
| --- | ---: | ---: |
| Moeda | BRL | BRL |
| Bruto mensal | 10.000 | 12.000 |
| Meses pagos | 12 | 11 |
| Extras garantidos anuais | 10.000 | 0 |
| Variável anual possível | 5.000 | 0 |
| Benefícios anuais | 12.000 | 0 |
| Fundos restritos anuais | 8.000 | 0 |
| Impostos anuais informados | 26.000 | 12.000 |
| Custos anuais informados | 1.000 | 8.000 |
| Reserva anual informada | 3.000 | 2.000 |
| Horas por semana | 40 | 40 |
| Semanas por ano | 50 | 48 |

Neste exemplo, o bruto garantido é 130.000 na CLT e 132.000 na PJ. Após
impostos e custos informados, são 103.000 e 112.000. Após as reservas,
100.000 e 110.000, respectivamente. Somando benefícios, os totais
comparáveis são 112.000 e 110.000. Os valores disponíveis correspondem a
médias mensais de 8.333,33 e 9.166,67 quando divididos por 12. Essas médias
não prometem pagamentos iguais em todos os meses. O 13º do exemplo é um extra
informado, não uma fórmula de cálculo legal.
As médias mensal e por hora são arredondadas a 0,01 unidade da moeda, com
empate para o número par.

Bônus variável pode não acontecer. FGTS ou outro fundo restrito não é dinheiro
mensal disponível: ambos aparecem separados e não entram no total comparável.
Benefícios também podem ter restrições de uso ou valor pessoal diferente do
valor declarado. Compare custos anuais já agregados, inclusive contabilidade,
plano de saúde, equipamento e internet quando pagos por você. Não subtraia o
mesmo custo duas vezes.

Se a base CLT contém 12 meses pagos, o mês de férias pago já está nessa base.
Informe como extra somente o adicional que não esteja incluído. Se a PJ prevê
11 meses de receita, a pausa sem receita já aparece no mês não pago. Não
reserve novamente o mesmo valor para a mesma pausa; outra reserva explícita,
como a de emergência, pode ser necessária. Confirme cada hipótese com a pessoa.

Para moedas diferentes, informe a taxa, data e fonte pública HTTPS. A taxa é
quantas unidades da moeda base correspondem a uma unidade da moeda original.
Sem taxa, os resultados ficam em suas moedas, sem equivalência. Cotação muda;
taxas bancárias e custos de conversão devem ser informados quando relevantes.
A calculadora não busca cotações. Para obter o bruto mensal equivalente, ela
mantém fixos impostos, custos, reserva, benefícios, extras e meses do cenário
alvo. É uma estimativa: impostos podem mudar com o novo valor e precisam ser
recalculados. O bruto mensal equivalente é arredondado para cima em 0,01 unidade
da moeda. O resultado não determina alíquota nem garante equivalência real.

Para perguntar "quanto precisaria receber na outra proposta?", o salário
mensal do cenário alvo pode ficar desconhecido. A equivalência usa os outros
componentes necessários e mostra quais campos fora do cálculo continuam
pendentes. Bônus e fundos restritos desconhecidos não são tratados como zero
nem incluídos no valor garantido.

Considere também autonomia, estabilidade, jornada, riscos, dias de descanso,
rescisão, prazo e demais termos do contrato. Maior valor líquido não decide
sozinho qual proposta é melhor. Para trabalho internacional, verifique moeda
de pagamento, local de trabalho e regras de imigração aplicáveis.

## Contrato técnico

Na CLI, use `offers save` com o cenário, `offers get` com `offer_id`, `offers
compare` com `ids` ou `offers equivalent` com `base_id` e `target_id`. As duas
comparações aceitam `base_currency` e `rates`. `offers list` e `offers status`
são consultas sem payload. Todos os dados vão por JSON na entrada padrão,
nunca como argumentos com valores pessoais. A pessoa conversa naturalmente.
Salve checkpoint com `phase: offers`, a próxima premissa e a dúvida pendente
para retomar sem exigir o onboarding de candidaturas.

`Offers(root)` usa `Profile._db` e armazena JSON privado aditivo. Leituras não
criam `.job`. `save(data)` cria sempre um cenário novo com ID; não há edição
que sobrescreva cenário. Retorna `{offer, calculation}`. `list()` devolve a
lista de cenários; `get(id)` devolve `{offer, calculation}`; `status()` traz
contagem e faltas. `compare(ids, base_currency=None, rates=None)` devolve
`offers`, `base_currency`, `rates`, `missing_rates`, `comparable` e `ranking`
(sempre null). `equivalent(base_id, target_id, base_currency=None, rates=None)`
retorna fórmula, premissas e estimativa de bruto mensal do cenário alvo.

O objeto de entrada exige `label`, `regime` (`CLT`, `PJ`, `MEI`, `cooperado`,
`internacional`), `currency` (três letras maiúsculas), `gross_monthly`,
`paid_months`, `guaranteed_extra_annual`, `variable_annual`, `benefits_annual`,
`restricted_funds_annual`, `taxes_annual`, `costs_annual` e `reserve_annual`.
Os componentes materiais podem ser `null` para desconhecido; meses conhecidos
são inteiros de 1 a 12. `hours_week`, `weeks_year`, `notes`, `assumptions` e `estimated_fields` são
opcionais. `estimated_fields` lista os nomes dos campos numéricos informados
que são estimativas; a marcação aparece no cálculo. Valores numéricos conhecidos
são não negativos, finitos, com até 19 dígitos inteiros e 12 casas decimais.
Horas e semanas, quando fornecidas, são maiores que zero, com no máximo 168 horas
por semana e 53 semanas por ano; valores fracionários são aceitos. A saída usa
strings decimais e `null` para cálculos indisponíveis. Registre em `assumptions`
quais dados são estimativas e sua origem.

`rates` associa cada moeda de origem a `{rate, date, source}`: taxa positiva,
data ISO `AAAA-MM-DD` e URL pública HTTPS sem credenciais, parâmetros ou
fragmento. A moeda base tem fator 1. Em moedas diferentes, informe a base e
uma taxa por moeda diferente dela. Taxa ausente impede equivalência; registro
incompleto ou inválido gera `ValueError`. A validação é sintática e não verifica
se a fonte está acessível ou se a taxa é correta. Cabe ao agente confirmar a
fonte pública e a taxa fora do módulo. O módulo não lê o piso do perfil.
