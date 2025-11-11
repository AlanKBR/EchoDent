import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text

# Ensure app package import works when running directly
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import RoleEnum, Usuario  # noqa: E402


def main():
    """Seed or reset the ADMIN user in the current tenant schema.

    Updated for the new single-DB, schema-per-tenant architecture:
    - Uses the default SQLAlchemy engine/URI (DATABASE_URL)
    - Ensures tenant schema (tenant_default) exists
    - Sets search_path to tenant_default, public for this session
    - Ensures the Usuario table exists (create if missing)
    - Creates or resets the 'admin' user with password 'admin123'
    """
    # Load .env to pick up DATABASE_URL and other settings
    try:
        load_dotenv()
    except Exception:
        pass

    app = create_app("default")
    with app.app_context():
        # Resolve tenant schema (default for now); allow override via env
        tenant_schema = os.environ.get("ECHO_TENANT_SCHEMA", "tenant_default")

        # Ensure schema exists and set search_path for this session
        try:
            db.session.execute(
                text(f"CREATE SCHEMA IF NOT EXISTS {tenant_schema}")
            )
            db.session.execute(
                text(f"SET search_path TO {tenant_schema}, public")
            )
        except Exception as exc:
            print(f"[warn] Could not prepare schema/search_path: {exc}")

        # Ensure the usuarios table exists on the default engine
        try:
            table = getattr(Usuario, "__table__", None)
            if table is not None:
                table.create(bind=db.engine, checkfirst=True)
        except Exception as exc:
            print(f"[warn] Could not ensure usuarios table: {exc}")

        # Upsert-like behavior for the admin user
        u = (
            db.session.query(Usuario)
            .filter(Usuario.username == "admin")
            .one_or_none()
        )
        if not u:
            u = Usuario()
            u.username = "admin"
            u.role = RoleEnum.ADMIN
            u.nome_completo = "Administrador"
            print("created admin user: admin/admin123")
        else:
            print("admin user already exists, resetting password to admin123")

        u.password_hash = generate_password_hash("admin123")
        db.session.add(u)
        db.session.commit()
        print("admin password set to admin123")


if __name__ == "__main__":
    main()
