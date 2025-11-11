# EchoDent – Comprehensive Project Architecture Blueprint

Generated to serve as the definitive reference for EchoDent’s hybrid architecture, aligned with EchoDent - Diretrizes de Arquitetura (v4 - Híbrida).

Generated on: 2025-10-31

Configuration snapshot
- Project type: Python (Flask, Jinja, HTMX)
- Architecture pattern: Layered monolith with MVC-ish thin controllers (Blueprints) and service layer; Hybrid HATEOAS/Hypermedia UI
- Diagram type: C4 (described textually)
- Detail level: Comprehensive, implementation-ready
- Includes: code examples, implementation patterns, decision records, extensibility focus

## 1. Architecture Detection and Analysis

Detected stacks and frameworks
- Backend: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, APScheduler
- ORM/DB: SQLAlchemy 2.x style via Flask-SQLAlchemy; PostgreSQL (psycopg[binary])
- Frontend: Server-rendered Jinja templates with HTMX for partial updates; Three.js planned for 3D odontogram (Tela 2)
- PDFs: HTML + @media print (client-side)
- Testing: pytest, pytest-flask, httpx

Detected architecture patterns
- Layered: models (domain/data) → services (business) → blueprints (thin controllers rendering Jinja/HTMX)
- Monolithic deployable with multi-tenant data separation via schema-per-tenant
- Hypermedia-first UI: backend renders HTML fragments; HTMX swaps (no heavy client SPA)
- Cross-cutting via events/listeners (audit) and a centralized error handler writing to DeveloperLog

Key boundaries and enforcement
- Blueprints never implement business rules; they call services in `app/services/`
- Services own transactions (try/commit/rollback) and input sanitization
- Models in a single module (`app/models.py`) with explicit enums and constraints; legal audit via `app/events.py`
- Tenant isolation using PostgreSQL schemas with `SET LOCAL search_path TO <tenant>, public` per request (`@app.before_request`)

Hybrid aspects and adaptations
- “Master (3D) vs Snapshot (2D)” odontogram: live truth in `OdontogramaDenteEstado` and immutable snapshot in `Paciente.odontograma_inicial_json`
- “Soma burra” finance: dynamic saldo derived from persisted totals and movements; UI derives statuses without extra status columns
- Shadow DB for Alembic autogenerate; two-pass migration execution (public → tenants)

## 2. Architectural Overview

Guiding principles
- Offline-first (local network), robustness, simplicity, workflow-first
- Strong data integrity within each tenant schema (FKs inside schema), and legal/audit traceability
- Deterministic time handling: all DateTime are timezone-aware (UTC)

High-level components
- Blueprints (controllers): `app/blueprints/*` – thin HTTP handlers mapping to service calls and template rendering
- Services (business): `app/services/*` – domain logic, validation, atomic transactions, timeline writes
- Models (data): `app/models.py` – all entities, enums, constraints; JSONB fields where appropriate
- Events/Audit: `app/events.py` – SQLAlchemy session listeners capturing create/update/delete diffs into `LogAuditoria`
- Error handling/logging: Global exception handler → `log_service.record_exception()` → `public.developer_log`
- Background tasks: APScheduler for housekeeping (e.g., purge dev logs)

Enforcement mechanisms
- Architectural rules codified in services: sanitization via `utils.sanitization.sanitizar_input`, required try/commit/rollback, finance constraints
- UI rules: HTMX request guardrails (e.g., disable double-click, confirm on dirty forms) implemented in global JS/CSS (see Diretrizes §8)

## 3. Architecture Visualization (C4 textual)

System context (C4 Level 1)
- Users: Admin, Dentista, Secretaria
- System: EchoDent (Flask app)
- External services: Brazil API (CEP), OS filesystem (media storage)

Container view (C4 Level 2)
- Web App (Flask): Blueprints handle requests, render Jinja/HTMX
- Database (PostgreSQL): Single cluster; schemas: public + tenant_xxx
  - public: governance (Tenant, GlobalSetting, DeveloperLog, Holiday)
  - tenant_default (and others): clinical and finance data

Component view (C4 Level 3)
- Controller layer: `paciente_bp`, `financeiro_bp`, `odontograma_bp`, `agenda_bp`, `admin_bp`, etc.
- Service layer: `paciente_service`, `financeiro_service`, `odontograma_service`, `timeline_service`, `log_service`, etc.
- Data layer: entities in `app/models.py` with JSONB, enums, constraints
- Cross-cutting: `events.py` (audit logs), global exception handler, APScheduler

Data flow
- Request → Blueprint → Service → DB transaction → TimelineEvento (double-write) → Render Jinja/HTMX partial
- Errors bubble to global error handler → write DeveloperLog; optional dev toast when `GlobalSetting('DEV_LOGS_ENABLED') == true`
- Before each request → set `search_path` to `tenant_default, public` (tenant routing hook)

## 4. Core Architectural Components

Blueprints (thin controllers)
- Purpose: routing, input collection, invoking services, rendering templates/partials
- Interaction: call service functions; return full pages or HTMX fragments
- Example: `financeiro_bp.editar_plano` reconstructs items_data, then delegates to `financeiro_service.update_plano_proposto`

Services (business logic)
- Responsibilities: validation, sanitization, transactions, domain rules, timeline events
- Patterns: function-oriented services; explicit commit/rollback per operation
- Examples:
  - Atomic create: `financeiro_service.create_plano()` builds items (freeze name/price), commits, posts timeline
  - Guard rails: `approve_plano()` disallows approving non-PROPOSTO; `add_lancamento_estorno()` enforces caixa lock

Models (domain/data)
- Centralized in `app/models.py`; Postgres-native features (JSONB, enums, constraints)
- Key entities: Usuario, Paciente, Anamnese, PlanoTratamento, ItemPlano, LancamentoFinanceiro, ParcelaPrevista, OdontogramaDenteEstado, TimelineEvento, FechamentoCaixa, CalendarEvent, Holiday, LogAuditoria, DeveloperLog, Tenant, GlobalSetting
- Boundaries: FK only within tenant schema (public models explicitly use `__table_args__ = {"schema": "public"}`)

Events/Audit
- SQLAlchemy listeners on session: before_flush (updates, deletes) and after_flush_postexec (creates)
- Captures diffs JSON and user_id; persists to `LogAuditoria` atomically

Background jobs
- APScheduler global: registered in app factory; daily job to purge old dev logs via `log_service.purge_old_logs`

## 5. Architectural Layers and Dependencies

Layer rules
- blueprints → services → models/db; blueprints must not access db directly for business rules
- services own transactions and are the only layer to write TimelineEvento (UX history)
- utils provide shared helpers (e.g., sanitization, template filters)

Dependency notes
- Enums and models are imported locally inside functions when needed to avoid import cycles
- No circular dependencies detected between services; cross-service calls are minimal (`financeiro_service` uses `timeline_service`)

## 6. Data Architecture

Domain modeling
- Finance workflow
  - Frozen prices: `ItemPlano.procedimento_nome_historico` and `valor_cobrado` are denormalized at creation
  - Plan states: StatusPlanoEnum { PROPOSTO, APROVADO, CONCLUIDO, CANCELADO }. Services enforce editability only in PROPOSTO
  - Saldo (dynamic): $saldo = valor\_total + \sum(ajustes) - \sum(pagamentos)$; negative saldo means credit
  - Carnê cosmético: `ParcelaPrevista` has no persisted status; UI derives Paid/Partial/Pending from cumulative sums
- Clinical workflow
  - Live master: `OdontogramaDenteEstado` (unique per (paciente_id, tooth_id)) with JSONB state
  - Snapshot: `Paciente.odontograma_inicial_json` and `odontograma_inicial_data` (admin-only overwrite)
- Audit/legal
  - `LogAuditoria` captures C/U/D with changes JSON and user_id
  - `TimelineEvento` is a readable UX history populated by services

Tenancy
- Single Postgres database, schema-per-tenant model
- `public` schema for governance (Tenant, GlobalSetting, DeveloperLog, Holiday)
- Tenant schemas (e.g., `tenant_default`) for all clinical/finance data
- App enforces tenant routing by setting `search_path` per request

Migrations
- Alembic configured for a Shadow DB (`SHADOW_DATABASE_URL`) to compute diffs accurately
- Two-pass migration execution:
  - Pass 1 (public): include only objects in `public`, `version_table_schema='public'`
  - Pass 2 (tenants): discover active schemas via `public.tenants` (fallback to `tenant_default`); run with `version_table_schema=tenant_schema`

## 7. Cross-Cutting Concerns Implementation

Authentication & Authorization
- Flask-Login for session auth; `Usuario.role` (RoleEnum) for roles
- `admin_required` decorator protects admin-only actions (e.g., force snapshot)

Error Handling & Resilience
- Global exception handler:
  - Rolls back session, records exception via `log_service.record_exception`
  - When `GlobalSetting('DEV_LOGS_ENABLED') == true`, returns an HTMX-friendly toast fragment with stack trace
  - Otherwise returns `500.html`
- Services catch and re-raise domain `ValueError` messages after rollback, keeping user-facing errors deterministic

Logging & Monitoring
- Developer logs persisted in `public.developer_log` with request metadata and truncated bodies (4KB max)
- APScheduler job purges logs older than N days (default 30)

Validation
- All free-text inputs sanitized via `utils.sanitization.sanitizar_input()` before persistence
- Date parsing helpers normalize BR/ISO formats; enums enforce domain constraints

Configuration Management
- `Config` loads from env: `DATABASE_URL`, `SECRET_KEY`, optional API tokens
- Asset version for cache busting exposed via context processor

## 8. Service Communication Patterns

Service boundaries
- Single-process monolith; intra-service calls in-process
- HTMX over HTTP for partial HTML updates; JSON endpoints limited to clinical state APIs

Protocols and formats
- HTML (Jinja) for main flows; JSON for odontogram state endpoints; HTML pages with @media print for printing (client-side)

Resilience patterns
- Atomic DB transactions per service call; non-blocking timeline writes guarded in try/except

## 9. Python-Specific Architectural Patterns

- Module organization: single `models.py`; services as cohesive modules; blueprints grouped per domain
- Dependency management: `requirements.txt` pinned to mainstream libs (Flask, SQLAlchemy, psycopg)
- OOP vs functional: models are OOP; services are function-oriented modules; limited inheritance
- Framework integration: Flask app factory pattern; Flask-Migrate/Alembic; context processors for global template helpers
- Async: not used; synchronous request handling

## 10. Implementation Patterns (concrete)

Interface design (lightweight)
- Prefer simple function signatures per use case; keep parameters typed and validated; return domain objects or DTO dicts

Service implementation
- Contract
  - Inputs: primitive/typed ids and sanitized strings/decimals
  - Behavior: validate → build/update entities → commit → side-effects (timeline)
  - Errors: raise `ValueError("...user-facing...")` after rollback
  - Success: return created/updated entity or lightweight dict
- Template
```python
def operation(...):
    try:
        # validate inputs (and sanitize strings)
        # query/build domain objects
        db.session.add(obj)
        db.session.commit()
        try:
            timeline_service.create_timeline_evento(...)
        except Exception:
            pass
        return obj
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ...: {exc}")
```

Repository/data access
- Prefer `db.session.get(Model, pk)`; use `joinedload` where beneficial; avoid N+1 in list views
- Use SQL functions (`func.sum`, `case`) for aggregate computations such as saldo

Controller/API patterns
- Thin controllers; reconstruct form payloads for services; return fragments suited for HTMX swaps; redirect/flash on full page flows
- Print flows render HTML pages with @media print (client-side); no server-side PDF engine

Domain model patterns
- Enums for state machines (plano, anamnese, agendamento, caixa)
- JSONB for flexible clinical state per tooth
- Denormalization for historical pricing in ItemPlano

## 11. Testing Architecture

Strategy
- Unit tests for services (financeiro, odontograma, paciente)
- Integration tests for blueprints and workflows; HTMX fragments asserted as HTML snippets
- E2E tests (select flows) under `tests/e2e*`

Boundaries and tools
- Pytest + pytest-flask; app factory supports `testing` mode with env-driven DB overrides (`ECHO_TEST_DEFAULT_DB`, etc.)
- Test data via `app/seeder.py` and focused builders in tests when needed

## 12. Deployment Architecture

Topology
- Single Flask app process (can scale horizontally behind a WSGI server)
- Single PostgreSQL database with multiple schemas (public + tenant_*)

Environment and configuration
- Required env: `DATABASE_URL`, `SECRET_KEY`
- Migrations: generate with Shadow DB (`SHADOW_DATABASE_URL`); apply using two-pass strategy controlled by `ECHODENT_RUN_PHASE` (public/tenants/both)

Media/Print handling
- Media stored on disk under `instance/media_storage/<paciente_id>/...`, DB stores relative paths only
- Printing handled client-side via HTML + @media print; server renders dedicated print routes without persisting PDFs

## 13. Extension and Evolution Patterns (extensibility-focused)

Feature addition patterns
- New domain feature
  - Add/extend models in `app/models.py` (respect tenant/public schemas)
  - Create a service module with atomic operations and sanitization
  - Expose routes via a new or existing blueprint; render Jinja/HTMX
  - Add timeline events for UX history where helpful

Modification patterns
- Evolve enums conservatively; migrate data via Alembic where needed
- Maintain backward-compatible template fragments (IDs/classes consumed by HTMX)
- Preserve frozen pricing semantics for finance; prefer adjustments over edits post-approval

Integration patterns
- External APIs (e.g., CEP lookup): wrap calls in a dedicated service; keep responses cached/validated; avoid tight coupling to views
- Anti-corruption: convert external payloads to internal DTOs and sanitize before persistence

## 14. Architectural Pattern Examples

Layer separation
```python
# Blueprint → Service → Template
@financeiro_bp.route("/plano/<int:plano_id>/editar", methods=["POST"])
def editar_plano(plano_id: int):
    items_data = ...  # build from form
    update_plano_proposto(plano_id=plano_id, items_data=items_data, usuario_id=current_user.id)
    return render_template("financeiro/_plano_card.html", plano=get_plano_by_id(plano_id))
```

Atomic service with rollback and timeline
```python
def add_lancamento(plano_id: int, valor: object, metodo_pagamento: str, usuario_id: int) -> LancamentoFinanceiro:
    try:
        # validations...
        lanc = LancamentoFinanceiro(...)
        db.session.add(lanc)
        db.session.commit()
        try:
            timeline_service.create_timeline_evento(...)
        except Exception:
            pass
        return lanc
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao registrar lançamento: {exc}")
```

Tenant routing hook
```python
@app.before_request
def set_tenant_search_path():
    tenant_schema = "tenant_default"
    db.session.execute(text(f"SET LOCAL search_path TO {tenant_schema}, public"))
```

Audit listeners (snippet)
```python
@event.listens_for(db.session, "before_flush")
def track_changes(session, *_):
    # collect updates/deletes diffs and queue creates for post-flush
```

## 15. Architectural Decision Records (ADRs)

ADR-001: Schema-per-tenant in PostgreSQL
- Context: Need for tenant isolation and per-tenant evolution with single DB ops model
- Alternatives: Separate databases per tenant; table-per-tenant; row-level tenancy
- Decision: Use schema-per-tenant with `search_path` switch and two-pass migrations
- Consequences: Strong isolation via schema; simpler connection mgmt; requires custom Alembic env for two-pass upgrades

ADR-002: Hypermedia UI with HTMX
- Context: Clinical workflows benefit from server-rendered simplicity and strong offline/local LAN operation
- Alternatives: SPA (React/Angular); server-only full page reloads
- Decision: Jinja-rendered fragments with HTMX swaps; keep JS light
- Consequences: Faster iteration, less client-state complexity; patterns for fragment IDs/classes must remain stable

ADR-003: Frozen pricing per item
- Context: Legal/financial requirement to preserve pricing at time of approval
- Alternatives: Join to live price table at render-time
- Decision: Denormalize `procedimento_nome_historico` and `valor_cobrado` on create
- Consequences: Historical correctness; requires edit constraints post-approval

ADR-004: Timeline via double-write in services
- Context: Need for readable, performant patient history without UNIONs
- Decision: Write `TimelineEvento` alongside domain transaction
- Consequences: Slight duplication; avoid as source of truth; ensure non-blocking writes

ADR-005: Global error logging and optional dev toasts
- Context: Improve DX and triage without exposing stack traces in prod
- Decision: Persist exceptions to `public.developer_log`; gate dev toasts via `GlobalSetting('DEV_LOGS_ENABLED')`
- Consequences: Centralized observability; configurable verbosity

## 16. Architecture Governance

Consistency maintenance
- Rules enforced in services (atomicity, sanitization) and via tests
- Migrations enforced through two-pass env; all models consolidated in `app/models.py`

Automated checks
- Pytest suite covers services and blueprints (see `tests/`)
- Optional pre-commit hooks (see `pre-commit-config.yaml`) can be enabled locally

Documentation practices
- This blueprint and `AGENTS.MD` govern architecture; update ADRs upon significant changes

## 17. Blueprint for New Development

Development workflow
- Start in models if data changes are needed; run migration generation against Shadow DB
- Implement service functions with sanitization and transactions
- Add blueprint routes rendering Jinja/HTMX; keep controllers thin
- Add tests: service unit tests + blueprint/integration where applicable

Implementation templates
- Services: follow the atomic template above; place in `app/services/<feature>_service.py`
- Blueprints: group by domain in `app/blueprints/`; use `@login_required` where necessary; lazy import heavy libs
- Templates: scope CSS to container; avoid inline JS/CSS; HTMX buttons disable on flight

Common pitfalls
- Editing approved plans: use AJUSTE entries instead
- Forgetting to sanitize inputs before commit
- Breaking tenant/public schema separation in models
- Skipping rollback on exceptions in services

—

Completion note
This blueprint reflects the current PostgreSQL multi-tenant implementation and hypermedia architecture in the repository. Keep it updated alongside schema or workflow changes.
