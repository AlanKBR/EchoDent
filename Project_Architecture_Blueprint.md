# EchoDent Project Architecture Blueprint

*Generated: 2025-10-27*

---

## 1. Architecture Detection and Analysis

**Technology Stack:**
- **Backend:** Python (Flask)
- **Frontend:** HTMX (server-rendered HTML, hypermedia architecture)
- **Database:** SQLite (multi-bind, managed via SQLAlchemy)
- **ORM:** SQLAlchemy
- **PDF Generation:** WeasyPrint (Jinja templates)
- **3D Visualization:** Three.js (Odontograma Master)
- **Migrations:** Flask-Migrate (Alembic, multi-bind)
- **Testing:** pytest

**Architectural Pattern:**
- Layered (MVC-inspired, with clear separation: models, services, blueprints/controllers)
- Monolithic (single deployable, multi-DB)
- Domain-driven boundaries (patient, finance, clinical, timeline)
- Hypermedia-driven UI (HTMX)

**Folder Structure:**
- `app/models.py`: All SQLAlchemy models
- `app/services/`: Business logic (service layer)
- `app/blueprints/`: Flask blueprints (thin controllers)
- `app/static/`, `app/templates/`: Frontend assets and Jinja templates
- `utils/`: Shared utilities (sanitization, decorators, filters)
- `migrations/`: Alembic migration scripts

---

## 2. Architectural Overview

EchoDent is designed for clinical workflow robustness, offline-first operation, and legal/UX compliance. The architecture enforces strict separation between data models, business logic, and presentation. All business rules reside in the `services/` layer, with blueprints acting as thin controllers. The UI is rendered server-side, with HTMX enabling dynamic, hypermedia-driven interactions. Multi-DB (multi-bind) is used for legal separation of concerns (patients, users, history).

---

## 3. Architecture Visualization

**High-Level Overview:**
- **Frontend (HTMX + Jinja):** Renders UI, triggers backend actions via hypermedia requests
- **Blueprints (Controllers):** Route requests, invoke services, render templates
- **Services:** Contain all business logic, enforce workflow, handle DB transactions
- **Models:** SQLAlchemy models, one file for all entities
- **Databases:** Multiple SQLite DBs (patients, users, history)

**Component Interactions:**
- UI → Blueprint → Service → Model/DB
- Service → Timeline/Event Logging (history DB)
- Service → PDF Generation (WeasyPrint)

**Data Flow:**
- User action (HTMX) → Flask route → Service method → DB update → Response (HTML fragment)

---

## 4. Core Architectural Components

### Blueprints (`app/blueprints/`)
- **Purpose:** Route HTTP requests, invoke services, render templates
- **Structure:** One blueprint per domain (e.g., paciente, financeiro)
- **Interaction:** Call service methods, pass data to templates
- **Evolution:** Add new blueprints for new domains; keep controllers thin

### Services (`app/services/`)
- **Purpose:** All business logic, workflow enforcement, DB transactions
- **Structure:** One service per domain (e.g., paciente_service.py)
- **Interaction:** Called by blueprints, interact with models, utilities
- **Evolution:** Add new services for new business domains; extend via new methods

### Models (`app/models.py`)
- **Purpose:** Define all DB entities (SQLAlchemy)
- **Structure:** Single file, all models
- **Interaction:** Used by services for data access
- **Evolution:** Add new models as needed; avoid cross-DB foreign keys

### Utilities (`app/utils/`)
- **Purpose:** Shared helpers (sanitization, decorators, filters)
- **Structure:** Modular utility files
- **Interaction:** Used by services and blueprints
- **Evolution:** Add new utility modules as needed

---

## 5. Architectural Layers and Dependencies

- **Presentation:** Jinja templates, HTMX, static assets
- **Controller:** Flask blueprints (thin)
- **Service:** Business logic, transaction management
- **Data:** SQLAlchemy models, multi-DB

**Dependency Rules:**
- Blueprints depend on services
- Services depend on models and utils
- Models are independent
- No direct blueprint-to-model access

**Abstraction Mechanisms:**
- Service layer abstracts business logic
- Utilities abstract cross-cutting concerns

---

## 6. Data Architecture

- **Domain Model:** All entities in `models.py`, e.g., Paciente, PlanoTratamento, AchadoClinico
- **Entity Relationships:** Managed in-model (no cross-DB foreign keys)
- **Data Access:** Via SQLAlchemy ORM, session per service method
- **Data Validation:** `utils.sanitizar_input()` for all free-text fields
- **Snapshots:** Odontograma initial state stored as JSON in Paciente
- **Caching:** Not implemented (offline-first, local DB)

---

## 7. Cross-Cutting Concerns Implementation

### Authentication & Authorization
- User model, session-based auth
- Soft-delete for offboarding
- Permission checks in services

### Error Handling & Resilience
- Try/commit/rollback in all service DB writes
- Graceful error messages in UI

### Logging & Monitoring
- Audit log in `history.db` (auto via SQLAlchemy events)
- Timeline events for UX (written by services)

### Validation
- Input sanitization in services
- Business rule validation in service layer

### Configuration Management
- `config.py` for environment settings
- No secrets in code; use environment variables

---

## 8. Service Communication Patterns

- **Internal:** Function calls between blueprints, services, and models
- **External:** None (monolithic, no microservices)
- **PDF Generation:** Service calls WeasyPrint (lazy import)

---

## 9. Technology-Specific Architectural Patterns

### Python/Flask
- Modular app structure
- Blueprints for routing
- Service layer for business logic
- SQLAlchemy ORM, multi-bind
- Flask-Migrate for migrations

### HTMX
- Hypermedia-driven UI
- Server-rendered HTML fragments
- No client-side SPA framework

### WeasyPrint
- PDF generation from Jinja templates
- PDFs saved on disk at first generation

---

## 10. Implementation Patterns

### Interface Design
- Service interfaces defined by function signatures
- Utilities abstracted in `utils/`

### Service Implementation
- One service per domain
- All DB writes wrapped in transactions
- Input sanitization before DB write

### Repository Pattern
- Not used; ORM access via service methods

### Controller/API Pattern
- Blueprints route to service methods
- HTMX endpoints return HTML fragments

### Domain Model
- Entities in `models.py`, with denormalized fields as needed

---

## 11. Testing Architecture

- **Unit Tests:** For services and utilities (`tests/`)
- **Integration Tests:** For blueprints and end-to-end flows
- **Test Data:** Seed scripts in `scripts/`
- **Tools:** pytest

---

## 12. Deployment Architecture

- **Topology:** Monolithic Flask app, local SQLite DBs
- **Environments:** Configurable via `config.py` and env vars
- **Migrations:** Alembic/Flask-Migrate
- **Media:** Saved in `instance/media_storage/`
- **PDFs:** Saved on disk, served statically

---

## 13. Extension and Evolution Patterns

### Feature Addition
- Add new service and blueprint for new domain
- Extend models in `models.py`
- Add templates and static assets as needed

### Modification
- Modify service methods for business rule changes
- Use soft-delete for deprecation

### Integration
- Add adapters in services for external systems (future-proof)

---

## 14. Architectural Pattern Examples

### Layer Separation Example
```python
# app/blueprints/paciente_bp.py
@paciente_bp.route('/paciente/<int:id>')
def view_paciente(id):
    paciente = paciente_service.get_paciente(id)
    return render_template('pacientes/view.html', paciente=paciente)
```

```python
# app/services/paciente_service.py
def get_paciente(id):
    paciente = db.session.query(Paciente).get(id)
    return paciente
```

### Service Transaction Example
```python
def update_paciente(id, data):
    try:
        paciente = db.session.query(Paciente).get(id)
        paciente.nome = sanitizar_input(data['nome'])
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
```

### Timeline Event Logging
```python
# app/services/timeline_service.py
def log_event(user_id, paciente_id, evento):
    evento = TimelineEvento(user_id=user_id, paciente_id=paciente_id, evento=evento)
    db.session.add(evento)
    db.session.commit()
```

---

## 15. Architectural Decision Records

### Architectural Style
- **Decision:** Layered, monolithic, service-oriented
- **Rationale:** Simplicity, maintainability, legal/UX requirements
- **Alternatives:** Microservices (rejected for complexity)

### Technology Selection
- **Flask:** Lightweight, flexible, Pythonic
- **SQLAlchemy:** Multi-DB support, ORM
- **HTMX:** Hypermedia, no SPA complexity
- **WeasyPrint:** High-fidelity PDF, Jinja integration

### Implementation Approaches
- **Service Layer:** All business logic, transaction management
- **Audit Logging:** SQLAlchemy events, separate DB
- **Soft-Delete:** Legal compliance, historical integrity

---

## 16. Architecture Governance

- **Consistency:** Enforced by AGENTS.MD rules
- **Automated Checks:** Pre-commit hooks, pytest
- **Review:** Manual code review, adherence to architecture doc
- **Documentation:** AGENTS.MD, this blueprint

---

## 17. Blueprint for New Development

### Workflow
- Start with service and blueprint for new feature
- Add/extend models in `models.py`
- Create templates and static assets
- Write tests in `tests/`

### Templates
- Service: `app/services/<feature>_service.py`
- Blueprint: `app/blueprints/<feature>_bp.py`
- Model: Add to `models.py`
- Template: `templates/<feature>/`

### Pitfalls
- Avoid direct DB access in blueprints
- Do not bypass service layer
- No cross-DB foreign keys
- Always sanitize input
- Use soft-delete, never hard-delete

---

*This blueprint was generated on 2025-10-27. Update after major architectural or workflow changes.*
