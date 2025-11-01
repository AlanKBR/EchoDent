# EchoDent – Diretrizes de Arquitetura (v3, PostgreSQL Schema-per-Tenant)

Esta versão substitui a antiga Seção 6 (Multi-Bind SQLite) e estabelece a base para PostgreSQL com multi-tenant por schema.

## 6. Banco de Dados (PostgreSQL – Multi-tenant por Schema)

- Arquitetura
  - Banco: PostgreSQL único.
  - Modelo multi-tenant: schema-per-tenant.
  - Isolamento: cada clínica em seu próprio schema (por exemplo, `tenant_default`, `tenant_alpha`). Dados globais e de governança residem no schema `public`.
  - Resolução de schema: a aplicação define o `search_path` por requisição/sessão para `<schema_tenant>, public`. Os modelos permanecem majoritariamente agnósticos de schema; somente tabelas globais declaram `schema="public"`.

- Schemas
  - `public`:
    - Tabelas globais de governança (ex.: `tenants`, configurações globais).
    - Infra/observabilidade quando apropriado (ex.: `DeveloperLog`).
    - Catálogos compartilháveis (ex.: feriados nacionais) quando não sensíveis.
  - `tenant_*`:
    - Todas as entidades específicas da clínica (Pacientes, Planos, Financeiro, Agenda, Timeline, Auditoria, Usuários da clínica etc.).
    - Restrições referenciais completas (Foreign Keys) entre tabelas do mesmo schema.

- Foreign Keys
  - Regra antiga (sem FKs cross-bind) é revogada. No modelo por schema, FKs são mandatórias dentro do schema `tenant`.
  - Regras:
    - Converter IDs “lógicos” existentes (ex.: `dentista_id`) em `db.ForeignKey` reais quando a tabela alvo estiver no mesmo schema.
    - Evitar dependências entre `tenant` e `public`. Quando inevitável, justificar explicitamente e considerar denormalização/replicação para manter isolamento.

- Concorrência e Operação
  - Sai o `PRAGMA journal_mode=WAL` (SQLite). Entra o MVCC do PostgreSQL.
  - Padrões operacionais:
    - Timezone do servidor: UTC. Em ORM: `DateTime(timezone=True)` em todos os carimbos de data/hora.
    - Nível de isolamento: `READ COMMITTED` (padrão do Postgres).
    - Engine options: `pool_pre_ping=True`.
    - Definição do schema por requisição: `SET LOCAL search_path TO <tenant>, public`.

- Migrações (Alembic)
  - Uma única árvore de migrações.
  - `env.py` customizado para dois passes:
    1) `public`: migrações globais (tabelas com `schema="public"` ou marcadas como globais).
    2) cada `tenant`: migrações de tabelas do domínio da clínica (agnósticas de schema), usando `search_path` para direcionar a criação.
  - Versionamento por schema: usar `version_table_schema` distinto para `public` e para cada `tenant`.
  - Marcação dos modelos:
    - Globais: `__table_args__ = {"schema": "public"}` ou `info={"schema_role": "public"}`.
    - Tenant: padrão (sem `schema`) ou `info={"schema_role": "tenant"}`.

- Workflow DEV (ECHODENTAL_DEV_SYNC=True)
  - Fluxo rápido/destrutivo: `DROP SCHEMA ... CASCADE`, recriação dos schemas `public` e `tenant_default`, `flask db upgrade` por schema, seed de dados.
  - Implementação via comando CLI (ex.: `flask dev-sync-db`). Nunca executar no startup do app em produção.

- Robustez/Legal/UX (mantidas)
  - Atomicidade por serviço (`try/commit/rollback`).
  - Sanitização de entradas em campos livres antes de persistência.
  - Auditoria legal por clínica (tabelas no schema `tenant`).
  - Timeline de UX por clínica.
  - Datas timezone-aware (UTC) em todas as colunas `DateTime`.

- Mídia/PDF
  - Manter mídia/PDFs em disco (`instance/media_storage/`). Tabelas de metadados de mídia ficam no schema `tenant`. Não usar BLOBs.

- Segurança e Offboarding
  - Soft-delete para `Usuario` e catálogos mestres da clínica (no schema `tenant`).
  - Governança/admin global residindo no `public` quando necessário, sem misturar dados clínicos com tenants.
