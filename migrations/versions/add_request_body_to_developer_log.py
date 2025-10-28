"""Add request_body to DeveloperLog (logs bind)

Revision ID: add_request_body_to_developer_log
Revises: manual_create_developer_log_logs
Create Date: 2025-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_request_body_to_developer_log'
down_revision = 'manual_create_developer_log_logs'
branch_labels = None
depends_on = None

def upgrade():
    # Adiciona a coluna request_body ao developer_log no bind 'logs'
    # de forma idempotente (não falha se já existir)
    from flask import current_app
    engine = current_app.extensions['migrate'].db.get_engine(bind='logs')
    with engine.connect() as conn:
        # Verifica se a coluna já existe para evitar erro em upgrades repetidos
        pragma_stmt = sa.text("PRAGMA table_info(developer_log)")
        result = conn.execute(pragma_stmt).fetchall()
        existing_cols = {row[1] for row in result}  # row[1] é o nome da coluna
        if 'request_body' not in existing_cols:
            alter_stmt = sa.text(
                'ALTER TABLE developer_log '
                'ADD COLUMN request_body TEXT'
            )
            conn.execute(alter_stmt)


def downgrade():
    # Remove a coluna request_body do developer_log no bind 'logs'
    # Observação: nenhuma ação é executada aqui porque o SQLite não
    # suporta DROP COLUMN diretamente; uma migração manual seria
    # necessária para recriar a tabela sem a coluna.
    # SQLite não suporta DROP COLUMN diretamente; operação manual pode
    # ser necessária em uma migração dedicada, se realmente preciso.
    pass
