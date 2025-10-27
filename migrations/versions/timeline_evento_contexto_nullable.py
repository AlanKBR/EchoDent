"""
Alembic migration for TimelineEvento: paciente_id nullable, evento_contexto enum.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'timeline_evento_contexto_nullable'
down_revision = 'b1a2c3d4e5f7'
branch_labels = None
depends_on = None

def upgrade():
    # SQLite workaround: create new table with paciente_id nullable and evento_contexto enum
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [col['name'] for col in insp.get_columns('timeline_evento')]
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('timeline_evento', recreate='always') as batch_op:
            batch_op.alter_column('paciente_id', nullable=True)
        timeline_contexto_enum = sa.Enum('PACIENTE', 'SISTEMA', name='timeline_contexto_enum')
        timeline_contexto_enum.create(bind, checkfirst=True)
        if 'evento_contexto' not in columns:
            op.add_column('timeline_evento', sa.Column('evento_contexto', timeline_contexto_enum, nullable=False, server_default='PACIENTE'))
    else:
        # 1. Alter paciente_id to nullable
        op.alter_column('timeline_evento', 'paciente_id', existing_type=sa.Integer(), nullable=True)
        # 2. Add evento_contexto enum column
        timeline_contexto_enum = sa.Enum('PACIENTE', 'SISTEMA', name='timeline_contexto_enum')
        timeline_contexto_enum.create(op.get_bind(), checkfirst=True)
        op.add_column('timeline_evento', sa.Column('evento_contexto', timeline_contexto_enum, nullable=False, server_default='PACIENTE'))


def downgrade():
    op.drop_column('timeline_evento', 'evento_contexto')
    op.alter_column('timeline_evento', 'paciente_id', existing_type=sa.Integer(), nullable=False)
    sa.Enum(name='timeline_contexto_enum').drop(op.get_bind(), checkfirst=True)
