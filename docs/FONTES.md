# Onde você quer procurar vagas?

O Carreira Guiada não traz portais pré-selecionados. Você pode informar os
endereços ou pedir ajuda para encontrar opções. A escolha aprovada fica no
seu perfil privado.

## Como enviar um link

1. Abra a página onde você quer procurar vagas, no seu navegador.
2. Clique na barra de endereço, no alto da janela, e copie o endereço.
3. Cole na conversa da ferramenta de IA em que você abriu o projeto.
   Pode enviar um de cada vez.
4. A IA confere o endereço e inclui os sites no resumo que você aprova.

Se precisar, diga "me ajude a copiar o link". A IA explica o próximo passo
com base na tela que conseguir observar. Você não precisa editar arquivo,
preencher uma configuração ou escolher um nome técnico para o site.

![As fontes fazem parte das escolhas confirmadas no início.](assets/inicio-guiado.png)

## Ainda não tenho os links

Diga "me ajude a encontrar sites de vagas". A IA usa seu cargo e mercado
pretendidos, sem enviar seus contatos ou currículo, e pesquisa opções públicas.
Antes de sugerir, confere identidade, domínio, origem oficial, evidência
independente e pedidos de dados. Mostra o que verificou, quando e o que ainda
não conseguiu confirmar. Você escolhe quais links quer usar e aprova a lista.

Popularidade e HTTPS sozinhos não comprovam segurança. A IA não recomenda
um site com identidade contraditória, pagamento suspeito ou risco não resolvido.
Uma análise favorável também não garante cada anúncio: vagas e recrutadores
são avaliados separadamente. Veja [pesquisa de empresas e vagas](EMPRESAS.md).

Se preferir, diga "deixe para depois". O currículo e as outras respostas podem
continuar. A IA não usa uma lista escondida nem os sites de outra pessoa.

## Se o endereço não for aceito

Use a página pública de busca ou de carreiras, começando com `https://`.
Não envie link de recuperação de senha, convite de acesso, sessão autenticada
ou endereço com código secreto. A IA explica o que precisa ajustar sem repetir
esses valores e sem pedir credenciais.

O controle local aceita endereços públicos, com parâmetros simples de pesquisa.
Alguns links legítimos precisam ser substituídos por uma página mais simples.
A verificação é sintática: não comprova que o site é confiável. A identidade
da empresa ainda precisa ser conferida.

## Como mudar de ideia

Diga "quero acrescentar este site", "não use mais este endereço" ou "quero
trocar os links da busca". A IA mostra a nova lista e pede sua aprovação.
As pesquisas seguintes usam a lista aprovada; o histórico anterior é preservado.

Se um anúncio levar a outro domínio, a IA verifica o destino e explica a
mudança. Nova fonte de pesquisa exige aprovação. Login e consentimentos no
destino continuam sendo decisões suas.

## Procedimento do agente

Investigar uma empresa ou explorar opções de carreira usa um alcance próprio,
com pergunta, alvo e endereços combinados. Isso pode começar antes do perfil
e não muda a lista de portais de candidatura. Veja o
[protocolo de investigação](INVESTIGACAO-AGENTE.md).

- Leia `sources.urls` no perfil aprovado. Nunca salve links pessoais neste guia.
- Use `profile answer sources` com `field: "urls"` e a lista completa de
  endereços confirmada. "Deixe para depois" corresponde a uma lista vazia.
- Antes da ação de busca de vagas `research`, informe `source_url` em `action authorize`. O controle
  exige uma fonte não vazia aprovada e domínio, porta e caminho compatíveis.
- A validação não resolve DNS nem verifica redirecionamentos. Confira cada
  destino observado, a identidade da empresa e as regras de uso do serviço.
- Descoberta de fontes após pedido ou aceite é pesquisa pública específica;
  siga a skill `fontes` e registre o parecer com `research save`. Esse comando
  só salva análise, não navega nem autoriza candidatura. Pesquisa de vagas
  permanece limitada a `sources.urls` aprovado. Não amplie essa lista sozinho.
- Permissão da pessoa não substitui permissão do serviço. Pare a ação afetada
  diante de restrição de automação, CAPTCHA ou bloqueio e explique o próximo passo.
- Registre consulta e cobertura por fonte. Busca parcial ou vazia não comprova
  que todas as vagas foram examinadas.
