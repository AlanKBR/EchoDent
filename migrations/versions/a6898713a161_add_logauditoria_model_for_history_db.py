"""Add LogAuditoria model for history db

Revision ID: a6898713a161
Revises: c81434728872
Create Date: 2025-10-23 20:38:04.594564

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a6898713a161'
down_revision = 'c81434728872'
branch_labels = None
depends_on = None


def _on_history_db() -> bool:
    try:
        bind = op.get_bind()
        url = str(getattr(bind.engine, "url", ""))
        return "history.db" in url
    except Exception:
        return False


def upgrade():
    if not _on_history_db():
        return
    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("changes_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    if not _on_history_db():
        return
    op.drop_table("log_auditoria")
