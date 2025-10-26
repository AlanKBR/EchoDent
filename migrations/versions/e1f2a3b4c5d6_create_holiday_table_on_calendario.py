"""Create holiday table on calendario bind

Revision ID: e1f2a3b4c5d6
Revises: c1d2e3f4a5b6
Create Date: 2025-10-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'c1d2e3f4a5b6'
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
        'holiday',
        sa.Column('date', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('level', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=10), nullable=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column(
            'source', sa.String(length=50), nullable=False,
            server_default=sa.text("'invertexto'"),
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('date'),
    )


def downgrade():
    if not _on_calendario_db():
        return
    op.drop_table('holiday')
