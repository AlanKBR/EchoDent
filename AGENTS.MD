# EchoDent - Manifesto de Roteamento e Arquitetura (v1)
1. Manifesto de Delegação (Roteamento)
Sua função primária, Orquestrador, é decompor a missão e usar #runSubagent para delegar a especialistas. Este é seu mapa de roteamento.

TAREFAS FINANCEIRAS

Keywords: 'PlanoTratamento', 'Orçamento', 'Pagamento', 'Estorno', 'Saldo Devedor', 'Carnê', 'ParcelaPrevista', 'Trava de Caixa', 'AJUSTE', 'Financeiro', 'boleto', 'pix', 'cartão', 'juros', 'desconto', 'parcelamento'.

Agente: #runSubagent('finance-rules', { task: '...' })

TAREFAS DE BANCO DE DADOS / SCHEMA

Keywords: 'Schema-per-Tenant', 'PostgreSQL', 'Alembic', 'Migração', 'public', 'tenant_default', 'dev-sync-db', 'ForeignKey', 'Banco de Dados', 'Modelo SQLAlchemy', 'index', 'constraint', 'unique', 'sequence', 'trigger'.

Agente: #runSubagent('db-schema', { task: '...' })

TAREFAS DE UI / UX / ROBUSTEZ

Keywords: 'HTMX', 'UX', 'Clique Duplo', 'Saída Suja', 'isFormDirty', '@media print', 'CSS Escopado', 'global.css', 'window.print', 'Frontend', 'spinner', 'loading', 'modal', 'tooltip', 'validação de formulário'.

Agente: #runSubagent('ui-robustness', { task: '...' })

PESQUISA FORENSE (Genérica)

Agente: #runSubagent('forensic-searcher', { query: '...' })

ANÁLISE DE CÓDIGO (Genérica)

Agente: #runSubagent('code-analyzer', { file: '...', query: '...' })

TESTE DE UI (MCP)

Agente: #runSubagent('mcp-tester', { objective: '...' })

TAREFAS MULTIDISCIPLINARES

- DB + Financeiro: primeiro #runSubagent('db-schema', { task }) e depois #runSubagent('finance-rules', { task, artefatos_db }).
- DB + UI: primeiro 'db-schema' depois #runSubagent('ui-robustness', { task, artefatos_db }).
- Financeiro + UI: primeiro 'finance-rules' depois 'ui-robustness'.
- DB + Financeiro + UI: sequência recomendada → db-schema → finance-rules → ui-robustness → opcionalmente mcp-tester para validação de fluxo.

Sempre que múltiplos domínios forem detectados, o Orquestrador deve decompor o objetivo em subtarefas textuais e encadear os agentes na ordem acima, passando os artefatos relevantes (diffs, arquivos) como contexto explícito.

ECO-SISTEMA DE DEV / IDE (VS CODE)

- dev-env: especialista em ambiente de desenvolvimento (Python, venv, pacotes, pytest/linters/formatters, extensões VS Code e features experimentais).
	- Keywords: "Python", "venv", "virtualenv", "pacote", "dependência", "pytest", "ruff", "mypy", "lint", "format", "extensão", "extension", "plugin", "VS Code", "settings.json", "launch.json".
	- Sempre que o objetivo envolver ajustar ambiente, instalar libs, configurar testes ou mexer em extensões/flags do VS Code, o orquestrador deve delegar ao dev-env.

- github-specialist: especialista em GitHub (issues, PRs, revisão de código, mensagens de commit, integração com fluxo Git remoto).
	- Keywords: "GitHub", "PR", "pull request", "issue", "commit", "branch", "merge", "review".
	- Usar quando o objetivo for abrir/ajustar PR, revisar mudanças com contexto do repositório remoto, ou sugerir sequência de comandos git + mensagens de commit.

ORQUESTRADOR (Chamada Principal)

Use: #runSubagent('echo-bot', { objective: 'Descreva aqui a missão completa' }).
O orquestrador é a porta de entrada padrão; o agente 'generalist' é usado como fallback interno quando o roteamento não encontra domínios claros.

GOVERNANÇA / AUTONOMIA

- Estado de missão persistido: `instance/agent_runtime/mission_state.json`.
- Log delegações: `instance/agent_runtime/delegations.log` (JSON lines).
- Sincronização de regras de domínio: `python scripts/sync_domain_rules.py <domain>`.
- Contrato de resposta padronizado: cada agente retorna `summary`, `actions`, `confidence`, `coverage`, `gaps`.
