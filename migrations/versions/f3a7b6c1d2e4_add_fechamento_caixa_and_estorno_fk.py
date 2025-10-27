"""add fechamento_caixa and estorno fk

Revision ID: f3a7b6c1d2e4
Revises: e92a1f3c4b7a
Create Date: 2025-10-26 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a7b6c1d2e4'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'fechamento_caixa' not in insp.get_table_names():
        op.create_table(
            'fechamento_caixa',
            sa.Column('data_fechamento', sa.Date(), nullable=False),
            sa.Column(
                'status',
                sa.Enum('ABERTO', 'FECHADO', name='caixa_status_enum'),
                nullable=False,
                server_default='ABERTO',
            ),
            sa.Column('saldo_apurado', sa.Numeric(10, 2), nullable=True),
            sa.PrimaryKeyConstraint('data_fechamento')
        )

    columns = [col['name'] for col in insp.get_columns('lancamentos_financeiros')]
    if 'lancamento_estornado_id' not in columns:
        op.add_column(
            'lancamentos_financeiros',
            sa.Column('lancamento_estornado_id', sa.Integer(), nullable=True),
        )
    op.create_index(
        'ix_lancamentos_fin_estornado_id',
        'lancamentos_financeiros',
        ['lancamento_estornado_id'],
    )
    # SQLite não suporta add_foreign_key em migração. Validação manual na camada de serviço.


def downgrade() -> None:
    # SQLite não suporta drop_constraint em migração. Nenhuma ação necessária.
    op.drop_index(
        'ix_lancamentos_fin_estornado_id',
        table_name='lancamentos_financeiros',
    )
    op.drop_column('lancamentos_financeiros', 'lancamento_estornado_id')
    op.drop_table('fechamento_caixa')
