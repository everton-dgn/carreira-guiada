![Carreira Guiada: menos busca manual, menos formulários repetidos.](docs/assets/carreira-guiada-cover.png)

# Carreira Guiada

Seu objetivo é conseguir um emprego. Você não precisa passar horas procurando
vagas manualmente e repetindo seus dados em formulários intermináveis.

Você conta o que procura e confirma seus dados. A IA ajuda a encontrar vagas
compatíveis, melhorar o currículo, preencher candidaturas e acompanhar os
retornos, conforme suas permissões e as ferramentas conectadas. Assim, você
dedica mais tempo às oportunidades que fazem sentido e à preparação para as
próximas etapas.

O projeto funciona dentro do **Claude Code ou Codex CLI, no terminal**, e
também em aplicativos de IA compatíveis. A conversa acontece na ferramenta
que você escolheu. O Carreira Guiada não tem uma interface gráfica própria.

[Começar](docs/GUIA.md) · [Privacidade](docs/PRIVACIDADE.md) ·
[Dúvidas comuns](docs/FAQ.md) · [Contribuir](CONTRIBUTING.md) · [Licença MIT](LICENSE)

**Versão experimental.** As ações dependem das ferramentas do aplicativo,
das permissões que você deu e das regras de cada serviço. O Carreira Guiada não garante
contratação nem execução contínua quando a sessão da IA termina.

## Comece com "iniciar"

1. Baixe o projeto e abra a pasta `carreira-guiada` no seu aplicativo de IA, como Codex
   ou Claude Code. Ele precisa conseguir ler a pasta e executar ferramentas
   locais. [Veja o passo a passo](docs/GUIA.md#primeira-vez).
2. Escreva **iniciar** no chat.
3. A IA pergunta uma coisa por vez. Anexe seu currículo ou diga que quer
   criar um. Se não souber responder, diga "não sei".

Depois de abrir a ferramenta, você conversa em linguagem comum. A IA conduz
os comandos locais. O guia explica como abrir uma sessão no terminal; se
faltar uma ferramenta, o assistente orienta a instalação autorizada.

![Simulação em terminal do Claude Code: iniciar, criar currículo, escolher fontes e aprovar o perfil.](docs/assets/inicio-guiado.gif)

*Exemplo ilustrativo no Claude Code, com dados fictícios. O visual real varia
conforme a versão e o tema do terminal.*
[Ver imagem sem animação](docs/assets/inicio-guiado.png) ·
[Ler o percurso em texto](docs/ONBOARDING.md)

## Você escolhe onde procurar

O projeto começa **sem lista de sites de vagas**. No onboarding, a IA pede
os links que você quer usar. Basta copiar o endereço da barra do navegador
e colar no chat. A escolha fica no seu perfil privado.

Não conhece nenhum site ainda? Diga "deixe para depois". Vocês podem preparar
o currículo e os filtros; a busca espera pelos links e pela sua aprovação.
A IA explica como copiar um endereço e não escolhe um portal por você.
[Como informar e alterar os links](docs/FONTES.md).

## O que acontece depois

| Etapa | O que você acompanha |
|---|---|
| Perfil | Tipo de trabalho, local, salário e suas permissões. |
| Currículo | Fatos confirmados, revisão e aprovação de cada versão. |
| Busca | Vagas nos endereços escolhidos, com motivos para seguir ou descartar. |
| Candidatura | Conferência da empresa, formulário, currículo e resultado do envio. |
| Retornos | Mensagens relacionadas às vagas, próximas etapas e prazos. |

![Simulação em terminal do Codex CLI: buscar vagas e preencher formulários com os dados já confirmados.](docs/assets/candidatura-guiada.gif)

*Exemplo ilustrativo no Codex CLI. Pressupõe perfil aprovado e ferramentas
conectadas; nenhuma candidatura é enviada pela demonstração.*
[Ver imagem sem animação](docs/assets/candidatura-guiada.png) ·
[Entender uma rodada de vagas](docs/GUIA.md#uma-rodada-de-vagas)

## Você continua no controle

- Diga **parar** para interromper novas ações. Diga **continuar** para retomar
  o progresso salvo durante uma sessão ativa.
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

## O que é necessário

| Item | Como funciona |
|---|---|
| Aplicativo de IA | Conta e sessão próprias, com acesso à pasta e a ferramentas locais. O Carreira Guiada não inclui assinatura de IA. |
| Sistema | macOS ou Linux. Windows nativo não é suportado; uso via WSL ainda precisa de validação. |
| Controle local | Python 3.11 ou superior e `uv`. A IA ajuda a preparar o ambiente. |
| Sites e e-mail | Ferramentas disponíveis e sessões autenticadas no aplicativo. Sem conexão, essas etapas ficam pendentes. |

Os testes usam cenários fictícios. Ainda não comprovam uma campanha real por
vários dias nem compatibilidade com todas as interfaces de recrutamento.
[O que foi e o que não foi validado](docs/VALIDACAO.md).

## Encontre o guia certo

| Quero... | Leia |
|---|---|
| Começar do zero | [Guia de início](docs/GUIA.md) |
| Entender as perguntas | [Onboarding](docs/ONBOARDING.md) |
| Escolher os links de busca | [Fontes escolhidas por você](docs/FONTES.md) |
| Criar ou revisar um currículo | [Currículos](docs/CURRICULOS.md) |
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

As imagens são descritas em [Créditos visuais](docs/VISUAIS.md).
