"""Add color column to usuarios on users bind

Revision ID: e1a2b3c4d5e6
Revises: a9c6c2463a96
Create Date: 2025-10-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5e6'
down_revision = 'a9c6c2463a96'
branch_labels = None
depends_on = None


def _on_users_db() -> bool:
    try:
        bind = op.get_bind()
        url = str(getattr(bind.engine, "url", ""))
        return "users.db" in url
    except Exception:
        return False


def upgrade():
    if not _on_users_db():
        return
    op.add_column(
        'usuarios',
        sa.Column('color', sa.String(length=20), nullable=True),
    )


def downgrade():
    if not _on_users_db():
        return
    op.drop_column('usuarios', 'color')
