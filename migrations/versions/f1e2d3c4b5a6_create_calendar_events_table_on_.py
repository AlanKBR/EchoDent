"""Create calendar_events table on calendario bind

Revision ID: f1e2d3c4b5a6
Revises: dc840828265a
Create Date: 2025-10-24 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1e2d3c4b5a6'
down_revision = 'dc840828265a'
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
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'title', sa.String(length=500),
            server_default=sa.text("''"), nullable=False,
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'all_day', sa.Boolean(),
            server_default=sa.text('0'), nullable=False,
        ),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('profissional_id', sa.Integer(), nullable=True),
        sa.Column('paciente_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    if not _on_calendario_db():
        return
    op.drop_table('calendar_events')
