# EchoDent — Copilot Instructions for AI Agents

These are project-specific rules and workflows to help AI coding agents be productive in this codebase. Favor what’s implemented here over generic Flask patterns.

## Architecture Overview
- Backend: `Flask` renders HTML (hypermedia), interactivity via `HTMX` partials. No SPA.
- DB: PostgreSQL with schema-per-tenant. Default tenant during dev is `tenant_default` with `search_path=tenant_default,public`.
- Printing/PDF: Client-side via `window.print()` on HTML with `@media print` CSS. No server-side PDF rendering.
- 3D: Planned Three.js for Odontograma Master; current persisted state uses `OdontogramaDenteEstado` JSON (see below).

## Database & Tenancy
- Config: `app/config.py` sets `SQLALCHEMY_DATABASE_URI` and `SQLALCHEMY_ENGINE_OPTIONS.connect_args.options=-c search_path=tenant_default,public`.
- Models in `public` must declare schema: e.g., `DeveloperLog`, `GlobalSetting`, `Tenant` use `__table_args__={"schema":"public"}` (see `app/models.py`). Tenant-scoped models omit schema and rely on `search_path`.
- Create/reset DB for dev with the CLI: `flask dev-sync-db` (drops/creates schemas `public` and `tenant_default`, runs `db.metadata.create_all`, and seeds). Implementation in `app/cli.py`.
- Migrations: Use Alembic for production (two-pass public→tenant). For daily dev, prefer `dev-sync-db` over migrate/upgrade.

## Code Organization & Conventions
- Single models file: All SQLAlchemy models live in `app/models.py`. Enums are defined near models for strong typing.
- Services layer: Business logic in `app/services/*`. Routes (blueprints) are thin controllers calling services and rendering templates (`app/blueprints/*`).
- Atomic writes: Any service that writes must use try/commit/rollback. See `financeiro_service.add_lancamento` and others.
- Input sanitization: Always run free-text fields through `app/utils/sanitization.py::sanitizar_input` before persisting.
- Timeline double-write: Services produce user-friendly history events in `TimelineEvento` via `app/services/timeline_service.py` (non-blocking best-effort after commit). Many services already call it.
- Auditing: Automatic audit logs via SQLAlchemy events in `app/events.py` write `LogAuditoria` entries on create/update/delete. Can be suppressed during seeding with `db.session.info["_audit_disabled"]=True`.
- Authentication: `flask-login` with `Usuario`; soft-delete via `Usuario.is_active`. `LoginManager.login_view = "auth_bp.login"`.

## HTMX UI Patterns
- No inline CSS/JS. Use `app/static/css/global.css` for tokens/components and scoped page styles.
- Blueprints return partials and use HTMX headers:
  - Redirect after POST with `HX-Redirect` (e.g., `paciente_bp.atualizar_ficha`).
  - Fire UI events with `HX-Trigger` after fragment updates.
- Prevent double-clicks via CSS `.htmx-request { pointer-events: none; }` and implement dirty-form guard in global JS (see AGENTS.MD §8; keep pages aligned with this rule).

## Financial Workflow (enforced in services)
- Source of truth: “Soma Burra” — saldo devedor is calculated, not stored: `valor_total + SUM(ajustes) - SUM(pagamentos)`.
- Plan lifecycle: `PROPOSTO` (editable) → `APROVADO` (sealed). Editing frozen fields is allowed only in `PROPOSTO` via `update_plano_proposto`.
- Price freezing: `ItemPlano.procedimento_nome_historico` and `valor_cobrado` are denormalized at creation and do not change with future price updates.
- Ajustes: Create `LancamentoFinanceiro` with `tipo_lancamento=AJUSTE` and mandatory `notas_motivo` (sanitized). Approved plans are never edited directly.
- Credit allowed: Negative saldo (overpayment) is valid and shown as credit in UI.
- Cashbox lock: Estornos are blocked when `FechamentoCaixa` for the day is `FECHADO`; instruct user to use an AJUSTE on the current day.
- Examples: See `app/services/financeiro_service.py` and tests in `tests/test_services_core.py`.

## Odontograma Rules
- Live state: `OdontogramaDenteEstado` stores per-tooth JSON state for the “Master” view.
- Initial snapshot: `Paciente.odontograma_inicial_json` + `odontograma_inicial_data` capture the first diagnosis; overwriting allowed only by ADMIN (see `odontograma_service.snapshot_odontograma_inicial`).
- Planning view: Finance screen uses plan-specific items; do not mix with Master state.

## Printing & Media
- Printing: Server renders HTML; browser does `window.print()` with `@media print`. Do not generate PDFs server-side. Persist emission metadata in `LogEmissao` and templates in `TemplateDocumento`.
- Media storage: Save relative paths under `instance/media_storage/`; serve with `send_from_directory` (see `paciente_bp.get_media_file`). Avoid blobs.

## Dev Workflows
- Install deps (Windows PowerShell):
  ```powershell
  python -m venv .venv
  . .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- Initialize/reset DB and seed (dev):
  ```powershell
  $env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/echodent"  # adjust as needed
  flask dev-sync-db
  ```
- Run the app:
  ```powershell
  $env:FLASK_APP="run.py"
  flask run
  ```
- Tests (DB should be initialized first):
  ```powershell
  flask dev-sync-db
  pytest
  ```
- Disable background scheduler for E2E or tests:
  ```powershell
  $env:DISABLE_SCHEDULER="1"
  ```

## Where to Look (examples)
- App factory and search_path: `app/__init__.py`.
- Models and enums: `app/models.py` (public vs tenant schema usage).
- Financial rules: `app/services/financeiro_service.py`.
- Audit hooks: `app/events.py`.
- Patient flows (5 tabs): `app/blueprints/paciente_bp.py` and `app/templates/pacientes/*`.
- Seeder: `app/seeder.py` (also shows default users: admin/dentista/secretaria with password `dev123`, dev-only).

If something here seems out of sync with code, prefer code. Ping to update this file.