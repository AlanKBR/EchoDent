"""manual: Criar tabela developer_log no bind 'logs'

Revision ID: manual_create_developer_log_logs
Revises: 8f5ab18d8435
Create Date: 2025-10-28 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'manual_create_developer_log_logs'
down_revision = '8f5ab18d8435'
branch_labels = None
depends_on = None


def upgrade():
    # Criação manual da tabela developer_log apenas no bind 'logs'
    from sqlalchemy import Table, MetaData, Column, Integer, DateTime, String, Text
    from flask import current_app
    metadata = MetaData()
    developer_log = Table(
        'developer_log', metadata,
        Column('id', Integer, primary_key=True),
        Column('timestamp', DateTime(timezone=True), nullable=False),
        Column('error_type', String(100), nullable=False),
        Column('traceback', Text, nullable=False),
        Column('request_url', String(500), nullable=True),
        Column('request_method', String(10), nullable=True),
        Column('user_id', Integer, nullable=True),
    )
    # Obter engine do bind 'logs' via Flask app
    engine = current_app.extensions['migrate'].db.get_engine(bind='logs')
    metadata.create_all(bind=engine)

def downgrade():
    # Remover a tabela apenas do logs.db
    from sqlalchemy import MetaData
    from flask import current_app
    engine = current_app.extensions['migrate'].db.get_engine(bind='logs')
    metadata = MetaData()
    metadata.reflect(bind=engine)
    if 'developer_log' in metadata.tables:
        metadata.tables['developer_log'].drop(bind=engine)
