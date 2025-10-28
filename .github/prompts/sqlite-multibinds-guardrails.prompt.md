---
mode: 'agent'
description: 'Auditar e fortalecer o uso de SQLite multi-binds com SQLAlchemy/Alembic no EchoDent: WAL, migrações por bind, sem FKs cross-DB, verificações de integridade na camada de services.'
tools: ['edit', 'search', 'runTasks', 'think', 'changes', 'todos']
---
# SQLite Multi-Binds Guardrails (EchoDent)

Implemente e verifique práticas obrigatórias para múltiplos bancos SQLite usando binds do SQLAlchemy.

## Objetivos
- Garantir `PRAGMA journal_mode=WAL` em TODOS os bancos via event listeners de engine
- Evitar `db.ForeignKey` entre bancos diferentes; substituir por colunas simples e checagens em `services/`
- Configurar Alembic multi-bind corretamente (migrar cada bind separadamente)
- Escrever testes de verificação (WAL ativo, migrações OK, integridade validada em `services`)

## Insumos que você deve levantar
- Quais binds existem (ex.: `pacientes.db`, `users.db`, `history.db`) e seu mapeamento em `SQLALCHEMY_BINDS`
- Onde ficam event listeners (ex.: `app/events.py` ou `app/__init__.py`) para aplicar WAL
- Estrutura atual de `migrations/env.py` para multi-bind
- Tabelas e colunas que referenciam entidades de outro bind

## Regras EchoDent (Obrigatórias)
- NUNCA usar `db.ForeignKey` entre binds distintos
- Integridade referencial é responsabilidade da camada `services/` (ex.: verificar existência do ID em outro bind antes de gravar)
- TODAS as escritas em `services/` são atômicas (try/commit/rollback)
- `history.db` recebe logs de auditoria automáticos (não misturar com dados de domínio)

## Ações do Agente
1. Validar e/ou implementar event listeners para `PRAGMA journal_mode=WAL` em cada bind
2. Revisar `migrations/env.py` e garantir suporte a multi-bind (migra cada bind sem conflitar metadados)
3. Auditar modelos em `app/models.py` e listar possíveis referências cross-DB; propor ajustes
4. Injetar/fortalecer checagens de integridade nos `services/` (ex.: `paciente_id` existente no bind correto)
5. Criar testes mínimos em `tests/` que:
   - Verificam `journal_mode=WAL` para cada engine
   - Parametrizam uma criação/atualização que precisa validar ID remoto (falha ao não existir)
   - Passam quando o ID é válido

## Esqueletos e Padrões
- Event Hook (conceito): ao criar engine para um bind, executar `PRAGMA journal_mode=WAL`
- Alembic multi-bind: `env.py` deve iterar pelos binds, setando `target_metadata` conforme o subset de modelos por bind
- Services: antes de inserir/atualizar com IDs que apontam para outro bind, consultar o outro banco (sem FK) e abortar com exceção clara se não existir

## Critérios de Aceite
- [ ] WAL ativo e verificado em todos os bancos (teste automatizado)
- [ ] Nenhum `ForeignKey` entre binds distintos em `models.py`
- [ ] Migrações executam por bind sem afetar os demais
- [ ] `services/` realizam validações de integridade cross-bind
- [ ] Testes de falha/sucesso cobrindo a integridade

## Dicas
- Prefira funções utilitárias de verificação em `services/` para reaproveitar as checagens
- Faça exceções específicas (ex.: `RelatedEntityNotFound`) para diferenciar erro de integridade de erro de validação
- Inclua mensagens legíveis para alimentar `TimelineEvento`
