"""add job_executions.updated_at and metrics-supporting indexes

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_executions",
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_job_executions_status", "job_executions", ["status"])
    op.create_index("ix_job_executions_completed_at", "job_executions", ["completed_at"])
    op.create_index("ix_job_executions_queued_at", "job_executions", ["queued_at"])


def downgrade() -> None:
    op.drop_index("ix_job_executions_queued_at", table_name="job_executions")
    op.drop_index("ix_job_executions_completed_at", table_name="job_executions")
    op.drop_index("ix_job_executions_status", table_name="job_executions")
    op.drop_column("job_executions", "updated_at")
