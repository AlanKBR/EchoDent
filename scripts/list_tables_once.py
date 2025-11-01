import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.environ['DATABASE_URL']
engine = create_engine(url)
with engine.connect() as conn:
    for schema in ['public', 'tenant_default']:
        res = conn.execute(
            text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema=:s ORDER BY table_name"),
            {"s": schema},
        ).all()
        print(schema, [r[1] for r in res])
