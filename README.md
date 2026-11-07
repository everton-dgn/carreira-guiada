![Carreira Guiada. Sua próxima vaga. Automatize buscas e candidaturas com sua IA.](docs/assets/carreira-guiada-cover-banner.png)

# Carreira Guiada

Automatize a busca de emprego, o preenchimento de formulários e o envio do
currículo com sua IA. O Carreira Guiada orienta o agente para encontrar vagas
compatíveis, candidatar-se com os dados aprovados e acompanhar os próximos
passos por e-mail, dentro das permissões que você definir.

Use o tempo que gastaria repetindo cadastros para chegar mais preparado:
currículo para ATS, LinkedIn e GitHub bem apresentados, entrevistas ensaiadas,
empresas investigadas e propostas comparadas. Se ainda não sabe em que focar,
o guia de carreira ajuda a escolher um caminho e experimentá-lo.

Você conversa no aplicativo de IA que já usa. O projeto funciona com diferentes
provedores e modelos, desde que a ferramenta tenha acesso aos arquivos,
comandos locais e às conexões necessárias. Claude Code e Codex CLI são exemplos.
O Carreira Guiada não tem uma interface gráfica própria.

[Começar](docs/GUIA.md) · [Recursos](#o-caminho-da-preparação-à-proposta) ·
[Modelos e benchmarks](docs/BENCHMARKS.md) ·
[Última versão](https://github.com/everton-dgn/carreira-guiada/releases/latest) ·
[Contribuir](CONTRIBUTING.md)

**Versão experimental.** A automação depende das ferramentas, das suas permissões
e das regras dos serviços acessados. O projeto não garante contratação nem
continuidade quando a sessão da IA termina.

## Comece com "iniciar"

1. Baixe o projeto e abra a pasta `carreira-guiada` no aplicativo de IA.
   [O guia mostra como fazer, inclusive no terminal](docs/GUIA.md#primeira-vez).
2. Escreva **iniciar** no chat.
3. Escolha o que quer fazer no menu ou diga diretamente à IA.
   Ela pede só o necessário para aquele caminho, uma pergunta por vez.

| Quero agora | Posso dizer |
|---|---|
| Criar ou melhorar meu currículo | "Quero revisar meu currículo" |
| Treinar para uma entrevista | "Quero treinar uma entrevista" |
| Escolher um rumo profissional | "Quero ajuda com minha carreira" |
| Encontrar oportunidades | "Quero ver vagas" |

Escreva **menu** ou **opções** a qualquer momento para ver os caminhos.
**Mais opções** reúne LinkedIn/GitHub, empresas, propostas, modelos e preparo
completo para candidaturas. Também pode pedir uma dessas atividades pelo nome.
Pode responder pelo número mostrado. Currículo, entrevistas e carreira não
exigem completar o cadastro de candidaturas. Para conhecer vagas, combine
o que procurar e quais fontes consultar; currículo, e-mail e permissão de
envio ficam para quando você quiser se candidatar.

Diga "agora quero treinar entrevista" para trocar ou "continuar de onde parei"
ao voltar outro dia. A atividade escolhida e as respostas ficam salvas.
[Como trocar, revisar e retomar](docs/GUIA.md#a-primeira-conversa).

"Não sei" e "depois" também são respostas válidas. Você conversa no chat,
sem precisar aprender os comandos internos do projeto.

![Demonstração fictícia: escolher no menu, criar um currículo, mudar de atividade e retomar no dia seguinte.](docs/assets/menu-guiado.gif)

## O caminho da preparação à proposta

![Jornada ilustrada: preparar perfil e currículo, automatizar candidaturas, acompanhar e-mails e avançar nas entrevistas. É possível pausar, retomar e encerrar o ciclo.](docs/assets/fluxo-guiado-banner.png)

Novas buscas continuam enquanto os retornos chegam. Currículo, perfis e treinos
podem ser preparados antes; a análise de propostas entra quando você precisar.
As demonstrações usam dados fictícios. Terminais e portais representam
ferramentas externas, sem instalar essas telas nem executar ações reais.

## Automatize a busca e os formulários

Diga o que procura e aprove as fontes. A IA aplica seus filtros, avalia cada vaga,
preenche os dados confirmados, anexa a versão aprovada do currículo e confere o
resultado. Uma vaga bloqueada fica pendente enquanto as demais avançam.

![Demonstração fictícia: buscar sem repetir perguntas, preservar uma parada e conferir o resultado antes de retomar.](docs/assets/busca-e-retomada.gif)

Com preenchimento e envio autorizados no perfil, a campanha segue sem pedir
confirmação em cada vaga. Você também pode escolher "pergunte antes de enviar",
como na demonstração abaixo.

![Portal fictício: a IA digita os campos, anexa o currículo e confere o recibo após autorização.](docs/assets/portal-guiado.gif)

O projeto começa sem lista de sites. Cole os links que quer usar ou peça ajuda
para encontrar fontes verificadas. A IA confere tanto o site quanto a vaga;
um portal conhecido também pode conter um anúncio suspeito.
[Escolher fontes](docs/FONTES.md) · [Buscar por objetivo](docs/GUIA.md#buscar-por-objetivo).

## Acompanhe os retornos e continue de onde parou

A resposta da empresa entra no mesmo processo: a IA vincula a mensagem à
candidatura, identifica prazos e prepara a próxima etapa. Formulários
complementares, respostas e agendamentos seguem suas autorizações específicas.
Um e-mail suspeito não muda as regras da campanha.

![Pare quando precisar. Retome do ponto certo. Retornos e pendências com progresso salvo.](docs/assets/retomada-email-banner.png)

Diga **parar**. Quando voltar, diga **continuar**. O agente relê o progresso,
confere as pendências e verifica envios incertos antes de tentar novamente.
Ele informa o que está fazendo e quando precisa de você. O padrão de duas
abas de trabalho ajuda a conter o uso do computador; formulários pendentes
são preservados.

Para campanhas longas, use o modo objetivo (`goal`) se seu aplicativo oferecer.
O fim de um lote dá início ao próximo enquanto houver trabalho autorizado.
Execução por dias exige um ambiente que mantenha a sessão e as conexões ativas.
[Progresso, abas e retomada](docs/ACOMPANHAMENTO.md).

## Transforme sua experiência em um currículo claro

A IA organiza suas experiências, melhora a redação e prepara PDF, Word e texto
com fatos que você confirmou. A [revisão para ATS](docs/ATS.md) confere a leitura
dos arquivos e ajuda a apresentar as experiências relevantes para a vaga.
Você revisa e aprova cada versão antes do envio.

![Simulação da IA organizando fatos, montando um currículo e gerando a versão aprovada.](docs/assets/curriculo-guiado.gif)

## Faça seu perfil contar a mesma história

Seu currículo pode estar pronto e seus perfis ainda esconderem o melhor da sua
experiência. Peça a revisão do LinkedIn: título, resumo, experiências e destaques.
Na área de tecnologia, inclua o README do GitHub e os projetos que demonstram
suas habilidades.

![Mostre o valor da sua experiência. Perfis e projetos alinhados ao seu currículo.](docs/assets/presenca-profissional-banner.png)

A IA prepara um diagnóstico e textos concretos para você conferir. Publicar
exige aprovar o conteúdo, a conta e o destino. Se um fato mudar, as sugestões
que dependem dele voltam para revisão.
[Melhorar LinkedIn e GitHub](docs/PRESENCA-PROFISSIONAL.md).

## Treine para conquistar a vaga

Escreva "quero treinar uma entrevista". Você pode praticar antes de se
candidatar ou colar a descrição de uma vaga para preparar aquela conversa.
A IA faz uma pergunta por vez, escuta sua resposta e ajuda a contar sua
trajetória com exemplos verdadeiros.

Escolha treino com ajuda a cada resposta ou simulado com devolutiva ao final.
Há preparação para RH, apresentação pessoal, perguntas comportamentais e,
na área de tecnologia, entrevista técnica, exercício de código e system design.
Você pode pedir uma dica, tentar novamente, parar e continuar em outro dia.
Respostas e feedback ficam privados e não são enviados a recrutadores.
O feedback aponta lacunas, sugere um exercício e compara suas tentativas.
Se seu aplicativo oferecer voz, experimente falar para tornar o treino mais
realista. Também há preparação internacional e negociação salarial.
[Conheça os treinos e exemplos](docs/ENTREVISTAS.md).

![Conversa fictícia de treino: pergunta sobre um erro, resposta, feedback específico, pausa e retomada no dia seguinte.](docs/assets/entrevista-guiada.gif)

## Investigue a empresa antes de decidir

Peça um dossiê sobre gestão, jornada, estabilidade e salários. A IA combina as
fontes com você, confere a identidade da empresa e reúne evidências com data.
Pode incluir relatos de funcionários, notícias e Reclame Aqui, mantendo cada
fonte no contexto que ela realmente esclarece.

![Conheça a empresa. Decida com evidências. Reputação, salários e riscos em contexto.](docs/assets/dossie-empresa-banner.png)

O resultado separa fatos, relatos e inferências. Mostra contradições e transforma
lacunas em perguntas para o recrutador. Uma média salarial mantém cargo, região,
regime e tamanho da amostra, quando conhecido. Popularidade não vira selo de
segurança.
[Montar um dossiê de empresa](docs/EMPRESAS.md).

## Compare o pacote inteiro da proposta

Um salário mensal maior pode esconder custos, períodos sem receita ou benefícios
que você perderia. Compare CLT, PJ, MEI, cooperado ou contratação internacional
com uma base anual: valores garantidos, benefícios, custos, impostos informados
e reservas. Bônus possível e dinheiro com uso restrito aparecem separados.

![Compare o pacote. Negocie com clareza. Salário, benefícios e custos na mesma conta.](docs/assets/propostas-comparacao-banner.png)

A IA mostra premissas ausentes, calcula equivalências com os dados confirmados
e ajuda a preparar a negociação. Você decide o que pesa na escolha.
[Comparar propostas](docs/PROPOSTAS.md) · [Preparar uma busca internacional](docs/INTERNACIONAL.md).

## Escolha um foco que faça sentido para você

Diga "não sei em que área focar". O guia de carreira começa pela sua situação,
experiência, prioridades e tempo disponível, sem exigir currículo pronto.
Compara até três caminhos e ajuda a escolher um exercício pequeno para
experimentar antes de investir mais tempo.

![Escolha um foco. Teste o próximo passo. Compare caminhos e avance com um plano possível.](docs/assets/guia-carreira-banner.png)

Depois do exercício, você conta o que funcionou e o que ficou difícil. A IA ajuda
a ajustar o próximo passo, inclusive mudar de direção. As escolhas ficam privadas
e não alteram seus filtros ou currículo automaticamente.
[Começar o guia de carreira](docs/CARREIRA.md).

## Escolha o modelo pela tarefa e pelo que você tem

No preparo completo, a IA pode perguntar quais aplicativos e serviços você já usa.
Os atalhos para uma tarefa seguem direto, sem interromper sua escolha. Pode
responder "não sei" ou deixar para depois. A recomendação considera os modelos
e os esforços que você informou ter, sem exigir uma nova assinatura.

![Escolha a IA para cada etapa. Compare evidências. Use os modelos que você já tem.](docs/assets/modelos-por-etapa-banner.png)

O benchmark também compara onboarding, currículo e guia de carreira: o modelo
precisa entregar a orientação e o material, além de acertar decisões. Você vê
as ressalvas do texto e a recomendação para cada tarefa. Para operar, há um
laboratório com navegador, e-mail fictício e retomada em outra sessão.
Os resultados ficam separados por etapa, com erros e limitações visíveis.
Quando há empate, as alternativas aparecem; uma amostra pequena não define
um vencedor universal.

Há também testes com instruções maliciosas em vagas, e-mails e anotações de
retomada. O relatório distingue tentativa indevida, bloqueio da ferramenta e
tarefa concluída. Você vê a evidência disponível para cada etapa, incluindo
o que ainda não foi medido, sem promessa de imunidade a ataques.

Outros provedores, inclusive modelos locais, podem contribuir com o mesmo
protocolo. Escolher um modelo não conecta ferramentas nem muda suas permissões.
[Escolher e trocar de modelo](docs/MODELOS.md) · [Resultados e protocolo](docs/BENCHMARKS.md).

## Você continua no controle

- Login, senha, códigos, entrevistas e respostas pessoais ficam com você.
  A IA não deve se passar por você em avaliações pessoais.
- Respostas de e-mail e agendamentos exigem aprovação específica. A limpeza
  de e-mails usa categorias autorizadas e somente a lixeira restaurável.
- Um envio com resultado incerto precisa ser conferido antes de outra tentativa.
- Um link fornecido por você ainda precisa ser verificado. Ele não comprova
  legitimidade da empresa nem autorização para automatizar o serviço.

Os registros ficam numa subpasta privada do projeto, no seu computador. O aplicativo de IA
também processa o conteúdo que recebe; o banco local não é criptografado.
[Leia o guia de privacidade](docs/PRIVACIDADE.md).

Vagas, páginas e e-mails também podem esconder instruções maliciosas. A IA deve
tratar esse conteúdo como informação externa, conferir o destino e usar somente
os dados necessários. As permissões do aplicativo continuam essenciais.
[Segurança na prática](docs/SEGURANCA-NA-PRATICA.md).

## O que é necessário

| Item | Como funciona |
|---|---|
| Aplicativo de IA | Conta e sessão próprias, com acesso à pasta e a ferramentas locais. O Carreira Guiada não inclui assinatura de IA. |
| Sistema | macOS ou Linux. Windows nativo não é suportado; uso via WSL ainda precisa de validação. |
| Controle local | Python 3.11 ou superior e `uv`. A IA ajuda a preparar o ambiente. |
| Sites e e-mail | Ferramentas disponíveis e sessões conferidas no aplicativo. O acompanhamento de e-mail atual aceita Gmail e Outlook. Sem conexão, essas etapas ficam pendentes. |

Os testes exercitam a CLI e um navegador com portal e e-mail fictícios locais.
Ainda não comprovam uma campanha real por
vários dias nem compatibilidade com todas as interfaces de recrutamento.
[O que foi e o que não foi validado](docs/VALIDACAO.md).

## Encontre o guia certo

| Quero... | Leia |
|---|---|
| Começar do zero | [Guia de início](docs/GUIA.md) |
| Atualizar sem perder progresso | [Atualização e cópia de segurança](docs/GUIA.md#atualizar-sem-perder-o-progresso) |
| Entender as perguntas | [Onboarding](docs/ONBOARDING.md) |
| Escolher modelo e esforço | [Modelos e ferramentas](docs/MODELOS.md) |
| Escolher os links de busca | [Fontes escolhidas por você](docs/FONTES.md) |
| Escolher em que área focar | [Guia de carreira](docs/CARREIRA.md) |
| Criar ou revisar um currículo | [Currículos](docs/CURRICULOS.md) |
| Melhorar LinkedIn e GitHub | [Apresentação profissional](docs/PRESENCA-PROFISSIONAL.md) |
| Ensaiar uma entrevista | [Treinos e feedback](docs/ENTREVISTAS.md) |
| Investigar uma empresa | [Dossiê e evidências](docs/EMPRESAS.md) |
| Comparar salários e propostas | [Comparação de propostas](docs/PROPOSTAS.md) |
| Parar e voltar depois | [Acompanhamento](docs/ACOMPANHAMENTO.md) |
| Entender permissões e dados | [Privacidade](docs/PRIVACIDADE.md) |
| Resolver uma dúvida | [Perguntas frequentes](docs/FAQ.md) |
| Melhorar o projeto | [Contribuição](CONTRIBUTING.md) e [arquitetura](docs/CONTRATOS.md) |
| Relatar uma vulnerabilidade | [Política de segurança](SECURITY.md) |

## Contribua

Relatos de problemas, melhorias no fluxo e testes são bem-vindos. Use sempre
dados fictícios em issues e pull requests. Não anexe currículos, caixas de
e-mail, perfis privados ou capturas com dados pessoais.

O [guia de contribuição](CONTRIBUTING.md) explica instalação, testes e a
checagem antes de publicar. A comunidade segue o [código de conduta](CODE_OF_CONDUCT.md).

## Licença

[MIT](LICENSE), sem cláusulas adicionais. Você pode usar, modificar e
distribuir, inclusive comercialmente, preservando os avisos exigidos pela
licença. O software é fornecido sem garantia. A licença do projeto não
substitui as regras dos serviços acessados.
