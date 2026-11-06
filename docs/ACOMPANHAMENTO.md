# Acompanhar, parar e voltar depois

Você deve conseguir entender o que a IA está fazendo durante o trabalho.
No terminal ou no aplicativo, ela avisa quando passa da busca para a triagem,
o preenchimento, o envio ou a leitura dos retornos. Um clique em enviar só
vira candidatura confirmada depois da conferência do resultado.

## Feedback durante a execução

O agente informa progresso real a cada mudança de etapa e, em trabalho
demorado, em intervalos de até 60 segundos quando a ferramenta permitir.
Use operações e esperas curtas para conseguir atualizar a conversa. Uma
chamada que bloqueia o chat pode impedir mensagens durante sua execução;
nesse caso, avise antes e atualize assim que a ferramenta devolver controle.

Cada aviso usa poucas frases e responde ao que for relevante naquele momento:
o que está acontecendo, o que já foi confirmado, qual o próximo passo e se
algo depende da pessoa. Exemplos com dados fictícios:

| Situação | Exemplo de aviso |
|---|---|
| Busca | "Estou conferindo as vagas da fonte escolhida. Três foram avaliadas; uma combina com seu perfil." |
| Preenchimento | "Estou preenchendo a vaga da Empresa Exemplo com os dados e o currículo aprovados." |
| Envio incerto | "O site não confirmou o recebimento. Vou conferir essa tentativa antes de enviar de novo; as outras vagas podem seguir." |
| Login necessário | "Esta vaga precisa de login. A aba está preservada; entre nela e me avise quando terminar." |
| Fonte indisponível | "Essa fonte apresentou erro duas vezes. Registrei a pendência e vou continuar nas outras fontes aprovadas." |
| Retomada | "Encontrei o progresso de ontem. Há um envio para conferir e uma etapa aguardando sua resposta." |

Não invente contagens, previsão de conclusão ou trabalho em andamento. Na
espera por resposta da pessoa, mostre a ação exata uma vez e siga frentes
independentes. Não repita a mesma cobrança a cada minuto.

## Progresso salvo

Cada resposta do onboarding, versão de currículo e resultado operacional é
salvo na área privada. Além desses registros, `checkpoint save` guarda a etapa,
o progresso comprovado e a próxima ação. Salve após uma mudança importante,
antes de esperar uma intervenção e ao parar. Nunca use essa nota para substituir
o registro de uma autorização, candidatura, mensagem ou resultado incerto.

O checkpoint tem `phase`, `summary`, `next_action` e `needs_user`; o controle
acrescenta `saved_at`. `status` mostra o último ponto salvo, com sua data.
As fases aceitas são `onboarding`, `resume`, `presence`, `practice`, `offers`,
`research`, `fill`, `email`, `followup`, `waiting` e `stopped`. Traduza esses valores na conversa;
nunca peça que a pessoa escolha um identificador técnico.
Esse registro não comprova que um executor está ativo nem mantém o computador
ou o aplicativo funcionando.

Ao voltar em outro dia, escreva `iniciar`. A IA oferece continuar de onde parou
ou revisar a preparação. Se já disser `continuar`, ela aproveita essa escolha.
Revisar mostra as respostas existentes, uma seção por vez, sem apagar tudo.
Só as correções confirmadas são salvas, e mudanças materiais pedem a aprovação
da nova versão. Uma autorização anterior não libera uma ação diferente.

## Poucas abas, com controle compartilhado

O padrão é de duas abas de trabalho para a campanha inteira, incluindo abas
aguardando login e todos os agentes que participarem. O perfil pode reduzir
para uma ou autorizar até cinco; nunca aumente por conta própria. Se o
computador estiver lento, pare de abrir abas e proponha usar uma de cada vez.

Antes de abrir ou assumir uma aba, consulte `tabs status` e faça `tabs reserve`.
A reserva consome uma vaga imediatamente. Depois da abertura, registre o ID
real, com prefixo do navegador, em `tabs update`. Uma reserva começa protegida;
só use `protected: false` após conferir que não há formulário não salvo,
login, envio incerto ou outra pendência dependente da aba.

- Reutilize uma aba segura antes de abrir outra. Preserve as abas da pessoa.
- Feche abas próprias sem utilidade após salvar o resultado. Confirme o
  fechamento na ferramenta antes de `tabs release` com `outcome: closed`.
- Abas da pessoa nunca são fechadas; ao terminar a interação, use
  `returned_to_user`. Abas próprias pendentes continuam no limite.
- Se a criação comprovadamente não ocorreu, use `not_created`. Se uma aba
  identificada já não existe após reiniciar o navegador, confira o inventário
  e use `already_absent`. Isso não resolve um possível envio incerto.

Se as duas abas tiverem pendências, não abra uma terceira nem feche o formulário
para liberar espaço. Continue tarefas sem navegador ou explique qual ação
permite avançar. Na retomada, reconcilie reservas e abas observadas antes de
abrir outras. Tempo passado não prova que uma aba desapareceu.

O controle local recusa reservas acima do limite; a abertura e o fechamento
reais são feitos pela ferramenta do aplicativo. Nunca redimensione, maximize,
minimize ou mova a janela compartilhada do navegador. Não encerre processos
da pessoa, não execute buscas sem limite e respeite os limites do serviço.
