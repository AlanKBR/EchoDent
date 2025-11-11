import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
from app import create_app, db
from app.models import LogAuditoria


def main() -> None:
    app = create_app()
    with app.app_context():
        table = getattr(LogAuditoria, "__table__", None)
        print("LogAuditoria table info:", getattr(table, "info", None))
        print(
            "LogAuditoria table metadata id:",
            id(getattr(table, "metadata", None)),
        )
        print("db.metadata id:", id(db.metadata))
        print("All tables and their bind_key info:")
        for name, table in db.metadata.tables.items():
            print("-", name, table.info.get("bind_key"))


if __name__ == "__main__":
    main()
