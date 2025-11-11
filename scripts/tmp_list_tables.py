import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ.get("DATABASE_URL")
print("URL:", url)
engine = create_engine(url)
for schema in ["public", "tenant_default"]:
    with engine.connect() as conn:
        res = conn.execute(
            text(
                "SELECT table_schema, table_name "
                "FROM information_schema.tables "
                "WHERE table_schema=:s ORDER BY table_name"
            ),
            {"s": schema},
        ).all()
        print(f"Tables in {schema}:")
        for row in res:
            print(f"- {row.table_schema}.{row.table_name}")
    with engine.connect() as conn:
        try:
            conn.execute(text(f"SET search_path TO {schema}, public"))
            ver = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).all()
            print(f"alembic_version in {schema}: {ver}")
        except Exception as e:
            print(f"alembic_version in {schema}: ERROR {e}")
