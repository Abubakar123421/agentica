"""Add multi-agent run metadata.

Revision ID: 20261016_0002
Revises: 20261016_0001
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "20261016_0002"
down_revision = "20261016_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.add_column(
            sa.Column("agent_type", sa.String(30), nullable=False, server_default="traceability")
        )
        batch_op.create_index("ix_agent_runs_agent_type", ["agent_type"], unique=False)
        batch_op.alter_column(
            "created_by_user_id", existing_type=sa.String(36), nullable=True
        )
        batch_op.alter_column("agent_type", server_default=None)


def downgrade() -> None:
    op.execute("DELETE FROM agent_runs WHERE created_by_user_id IS NULL")
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.alter_column(
            "created_by_user_id", existing_type=sa.String(36), nullable=False
        )
        batch_op.drop_index("ix_agent_runs_agent_type")
        batch_op.drop_column("agent_type")
