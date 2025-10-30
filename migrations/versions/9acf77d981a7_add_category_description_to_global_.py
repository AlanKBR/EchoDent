"""add_category_description_to_global_setting

Revision ID: 9acf77d981a7
Revises: add_idx_devlog_timestamp
Create Date: 2025-10-30 21:58:31.092700

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9acf77d981a7'
down_revision = 'add_idx_devlog_timestamp'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to global_setting table
    with op.batch_alter_table('global_setting', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.String(length=50), nullable=True, server_default='geral'))
        batch_op.add_column(sa.Column('description', sa.String(length=255), nullable=True))


def downgrade():
    # Remove the new columns
    with op.batch_alter_table('global_setting', schema=None) as batch_op:
        batch_op.drop_column('description')
        batch_op.drop_column('category')
