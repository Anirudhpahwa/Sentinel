"""add retry tracking columns to job_executions

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_executions", sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "job_executions", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3")
    )
    op.add_column("job_executions", sa.Column("root_execution_id", sa.Uuid(), nullable=True))
    op.add_column("job_executions", sa.Column("abandoned_reason", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_job_executions_root_execution_id",
        "job_executions",
        "job_executions",
        ["root_execution_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_job_executions_worker_id", "job_executions", ["worker_id"])
    op.create_index("ix_job_executions_root_execution_id", "job_executions", ["root_execution_id"])


def downgrade() -> None:
    op.drop_index("ix_job_executions_root_execution_id", table_name="job_executions")
    op.drop_index("ix_job_executions_worker_id", table_name="job_executions")
    op.drop_constraint("fk_job_executions_root_execution_id", "job_executions", type_="foreignkey")
    op.drop_column("job_executions", "abandoned_reason")
    op.drop_column("job_executions", "root_execution_id")
    op.drop_column("job_executions", "max_attempts")
    op.drop_column("job_executions", "attempt_number")
