"""Verificar schema da tabela ClinicaInfo.

Evita o acesso direto a ``__table__`` para manter compatibilidade com
analisadores estáticos, usando a API de inspeção do SQLAlchemy.
"""

from sqlalchemy import inspect as sa_inspect

from app import create_app
from app.models import ClinicaInfo

app = create_app()

with app.app_context():
    mapper = sa_inspect(ClinicaInfo)
    table = (
        getattr(mapper, "local_table", None)
        or getattr(mapper, "mapped_table", None)
        or getattr(mapper, "persist_selectable", None)
    )
    if table is None:
        print("Tabela não mapeada para um objeto Table.")
    else:
        print("Table fullname:", table.fullname)
        schema_attr = getattr(table, "schema", None) or "None (default)"
        print("Schema:", schema_attr)
