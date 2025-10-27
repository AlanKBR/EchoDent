"""add odontograma models and column

Revision ID: e9c1f2d3a4b5
Revises: cb912c57c696_add_created_at_to_planotratamento
Create Date: 2025-10-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e9c1f2d3a4b5'
down_revision = 'd5a1c2b3e4f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column to pacientes
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [col['name'] for col in insp.get_columns('pacientes')]
    if 'odontograma_inicial_json' not in columns:
        with op.batch_alter_table('pacientes') as batch_op:
            batch_op.add_column(
                sa.Column(
                    'odontograma_inicial_json', sa.JSON(), nullable=True
                )
            )

    # Create table odontograma_dente_estado
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'odontograma_dente_estado' not in insp.get_table_names():
        op.create_table(
            'odontograma_dente_estado',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'),
                nullable=False
            ),
            sa.Column('tooth_id', sa.String(length=3), nullable=False),
            sa.Column('estado_json', sa.JSON(), nullable=False),
            sa.UniqueConstraint(
                'paciente_id', 'tooth_id', name='uq_paciente_tooth_id'
            ),
        )
        op.create_index(
        'ix_ode_paciente_id', 'odontograma_dente_estado', ['paciente_id']
    )
    op.create_index(
        'ix_ode_tooth_id', 'odontograma_dente_estado', ['tooth_id']
    )


def downgrade() -> None:
    op.drop_index('ix_ode_tooth_id', table_name='odontograma_dente_estado')
    op.drop_index('ix_ode_paciente_id', table_name='odontograma_dente_estado')
    op.drop_table('odontograma_dente_estado')
    with op.batch_alter_table('pacientes') as batch_op:
        batch_op.drop_column('odontograma_inicial_json')
