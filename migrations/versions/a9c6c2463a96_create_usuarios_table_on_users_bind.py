"""Create usuarios table on users bind

Revision ID: a9c6c2463a96
Revises: 4db091019238
Create Date: 2025-10-23 19:54:15.118005

"""
from alembic import op
import sqlalchemy as sa


def _on_users_db() -> bool:
    try:
        bind = op.get_bind()
        url = str(getattr(bind.engine, "url", ""))
        return "users.db" in url
    except Exception:
        return False


# revision identifiers, used by Alembic.
revision = 'a9c6c2463a96'
down_revision = '4db091019238'
branch_labels = None
depends_on = None


def upgrade():
    if not _on_users_db():
        return
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column(
            'role',
            sa.Enum('ADMIN', 'DENTISTA', 'SECRETARIA', name='role_enum'),
            nullable=False,
        ),
        sa.Column(
            'is_active', sa.Boolean(), server_default=sa.text('1'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )


def downgrade():
    if not _on_users_db():
        return
    op.drop_table('usuarios')
