"""Add index on DeveloperLog.timestamp for logs bind

Revision ID: add_idx_devlog_timestamp
Revises: add_request_body_to_developer_log
Create Date: 2025-10-28 12:00:00.000000

"""
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_idx_devlog_timestamp'
down_revision = 'add_request_body_to_developer_log'
branch_labels = None
depends_on = None


def upgrade():
    # Criar índice no bind 'logs'
    from flask import current_app
    engine = current_app.extensions['migrate'].db.get_engine(bind='logs')
    with engine.connect() as conn:
        conn.execute(
            sa.text(
                'CREATE INDEX IF NOT EXISTS idx_devlog_timestamp '
                'ON developer_log (timestamp)'
            )
        )


def downgrade():
    # Remover índice do bind 'logs'
    from flask import current_app
    engine = current_app.extensions['migrate'].db.get_engine(bind='logs')
    with engine.connect() as conn:
        # SQLite supports DROP INDEX IF EXISTS from 3.8.0+
        conn.execute(
            sa.text('DROP INDEX IF EXISTS idx_devlog_timestamp')
        )
