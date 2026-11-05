# Instruções do projeto

@AGENTS.md

O procedimento do agente está no arquivo importado. As skills canônicas ficam
em `.agents/skills/`; cópias em `.claude/skills/` (por exemplo `/inicio`) têm
o mesmo conteúdo. A linguagem natural também funciona: `iniciar`
entra pela skill `inicio`. Os agentes em `.claude/agents/` são especializações
opcionais; o principal executa todas as etapas sem eles.
