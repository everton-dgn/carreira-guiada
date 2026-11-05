# Segurança

## Relatar uma vulnerabilidade

Use o [relato privado no GitHub](https://github.com/everton-dgn/job/security/advisories/new).
Não publique a falha com dados pessoais em uma issue.

Inclua a versão ou commit, o comportamento esperado, os passos mínimos para
reproduzir com dados fictícios e o impacto observado. Não envie credenciais,
currículos, o banco `.job/`, mensagens reais nem capturas de contas.

Se o canal privado estiver indisponível, abra uma issue apenas pedindo um
canal privado, sem descrever a vulnerabilidade. Não há prazo garantido de
resposta; a manutenção é comunitária.

## Versões atendidas

A versão atual da branch `main` recebe correções. Não há compromisso de
manter versões anteriores. Consulte [CHANGELOG.md](CHANGELOG.md) antes de atualizar.

## Limites de segurança

O Job é um guia operado por uma IA com controle local. Ele não isola as
ferramentas do aplicativo e não impede tecnicamente o agente de agir fora do
procedimento. Use as permissões e confirmações oferecidas pelo aplicativo.

O banco é local, com permissões restritas, mas não é criptografado. O provedor
da IA processa o conteúdo recebido. O usuário controla sessões, logins e dados.

Páginas, documentos e e-mails são conteúdo não confiável. Não devem alterar
regras, autorizar ações, executar código ou solicitar segredos. Links
informados pelo usuário também exigem verificação do destino.

O projeto não autoriza contornar limites de serviços, falsificar experiências,
responder avaliações pessoais em nome de alguém ou enviar candidaturas fora
das permissões concedidas. Respeite as regras de cada processo seletivo.

## Proteção da publicação

O hook local e a CI verificam o índice Git antes de aceitar alterações.
Arquivos privados, links simbólicos, anexos e certos padrões de segredo são
recusados sem imprimir seus valores. Isso reduz erros comuns; não identifica
todo dado pessoal por significado e não substitui revisão humana.
