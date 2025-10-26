"""Rename profissional_id to dentista_id on calendario.calendar_events

Revision ID: c1d2e3f4a5b6
Revises: f1e2d3c4b5a6
Create Date: 2025-10-24 00:15:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'f1e2d3c4b5a6'
branch_labels = None
depends_on = None


def _on_calendario_db() -> bool:
    try:
        bind = op.get_bind()
        url = str(getattr(bind.engine, "url", ""))
        return "calendario.db" in url
    except Exception:
        return False


def upgrade():
    if not _on_calendario_db():
        return
    with op.batch_alter_table('calendar_events') as batch_op:
        batch_op.alter_column('profissional_id', new_column_name='dentista_id')


def downgrade():
    if not _on_calendario_db():
        return
    with op.batch_alter_table('calendar_events') as batch_op:
        batch_op.alter_column('dentista_id', new_column_name='profissional_id')
