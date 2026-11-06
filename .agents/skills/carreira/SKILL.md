---
name: carreira
description: Ajudar a pessoa a escolher um foco profissional, comparar caminhos e planejar um experimento curto, com progresso privado e retomada. Usar quando ela não souber que trabalho procurar ou pedir orientação de carreira. Não exige currículo nem autoriza candidaturas.
---

# Guia de carreira

Leia [AGENTS.md](../../../AGENTS.md), o [guia para a pessoa](../../../docs/CARREIRA.md)
e os [contratos locais](../../../docs/INVESTIGACAO-AGENTE.md). Conduza a conversa
em linguagem comum. A pessoa não precisa ver comandos, IDs ou versões.

1. Consulte `career status`. Se não houver sessão e o pedido for iniciar o guia,
   use `career start` com objeto vazio. Leitura de `start --focus career` não
   cria sessão. Para retomar, use o registro salvo; não comece outra sessão.
2. Faça a pergunta retornada, uma por vez: objetivo, prioridades, experiências,
   restrições e tempo disponível. Reaproveite respostas que a pessoa já deu.
   "Não sei" ou escolha de pular usa `null`; não converta ausência em habilidade
   ou preferência. Não peça diagnóstico, trauma ou detalhes íntimos.
3. Salve com `career answer`, na versão atual. Ao corrigir uma resposta,
   confira o estado retornado: propostas dependentes deixam de valer. Preserve
   a trajetória anterior e explique só o que precisa ser reconsiderado.
4. Apresente uma a três alternativas com ganhos, custos, lacunas e base nas
   respostas atuais. Diferencie interesse, experiência demonstrada e hipótese.
   Não invente competências, salário, demanda ou probabilidade de contratação.
5. Se informação de mercado ajudar, combine a pergunta e os endereços públicos,
   registre `research-scope` para esta sessão e confira antes de cada consulta.
   Não use dados pessoais em consultas. Registre fonte, data, limitações e alcance
   da amostra. Algumas vagas não representam todo o mercado. Sem pesquisa, a
   conversa continua com o material fornecido e a limitação explícita.
6. Use `career propose` para salvar as alternativas. Só grave `choose` após
   a escolha explícita. Se a pessoa quiser adiar, preserve a sessão com `pause`;
   não invente escolha nem recusa. Ao retomar, `resume` preserva a etapa.
7. Combine um exercício pequeno, orçamento de tempo e critério de aprendizado.
   Grave `experiment` com a confirmação da pessoa. Use dados fictícios quando
   houver clientes ou documentos. Curso pago, contato e publicação exigem
   autorização própria; não fazem parte da escolha do exercício.
8. Depois, pergunte o que fez e aprendeu. `reflect` registra se quer continuar,
   mudar ou adiar. Dificuldade no exercício não é diagnóstico de incapacidade.
   Ajude a escolher um próximo passo concreto, sem julgamento pessoal.

Salve `checkpoint` com fase `career`, progresso e próxima ação após mudanças
relevantes. Uma pausa do guia não remove a parada global nem inicia campanha.
Respeite a pausa, a revogação de pesquisa e a prioridade de um pedido de busca.

Quando a pessoa quiser procurar vagas no foco escolhido, siga a skill
[perfil](../perfil/SKILL.md), apresente os filtros e obtenha a aprovação.
O guia não altera perfil, currículo, permissões ou fontes de candidatura.
O histórico fica na área privada; não escreva dados da pessoa nos documentos
do projeto.
