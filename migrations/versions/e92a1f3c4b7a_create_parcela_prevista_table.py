"""create parcela_prevista table

Revision ID: e92a1f3c4b7a
Revises: cb912c57c696
Create Date: 2025-10-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e92a1f3c4b7a'
down_revision: Union[str, None] = 'f3a7b6c1d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'parcela_prevista' not in insp.get_table_names():
        op.create_table(
            'parcela_prevista',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('plano_id', sa.Integer(), sa.ForeignKey('planos_tratamento.id'), nullable=False),
            sa.Column('data_vencimento', sa.Date(), nullable=False),
            sa.Column('valor_previsto', sa.Numeric(10, 2), nullable=False),
            sa.Column('observacao', sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('parcela_prevista')
