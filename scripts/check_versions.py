import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ.get("DATABASE_URL")
engine = create_engine(url)

with engine.connect() as conn:
    for schema in ["public", "tenant_default"]:
        conn.execute(text(f"SET search_path TO {schema}, public"))
        try:
            ver = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
            print(schema, "alembic_version:", ver)
        except Exception as e:
            print(schema, "alembic_version: ERROR", e)
        res = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=:s ORDER BY table_name"
            ),
            {"s": schema},
        ).all()
        print("tables in", schema, ":", [r[0] for r in res])
