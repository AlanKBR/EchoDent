"""add odontograma_inicial_data to pacientes

Revision ID: d5a1c2b3e4f6
Revises: cb912c57c696
Create Date: 2025-10-26 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd5a1c2b3e4f6'
down_revision = '57e34a28f09b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable timestamp column for snapshot UX (timezone-aware UTC)
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [col['name'] for col in insp.get_columns('pacientes')]
    if 'odontograma_inicial_data' not in columns:
        with op.batch_alter_table('pacientes') as batch_op:
            batch_op.add_column(
                sa.Column(
                    'odontograma_inicial_data',
                    sa.DateTime(timezone=True),
                    nullable=True,
                )
            )


def downgrade() -> None:
    with op.batch_alter_table('pacientes') as batch_op:
        batch_op.drop_column('odontograma_inicial_data')
