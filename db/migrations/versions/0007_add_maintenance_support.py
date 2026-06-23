"""add soft-delete/archive columns and admin_actions audit table

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_index("ix_jobs_deleted_at", "jobs", ["deleted_at"])

    op.add_column("workers", sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_index("ix_workers_archived_at", "workers", ["archived_at"])

    op.add_column("schedulers", sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_index("ix_schedulers_archived_at", "schedulers", ["archived_at"])

    op.create_table(
        "admin_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("performed_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_actions_performed_at", "admin_actions", ["performed_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_actions_performed_at", table_name="admin_actions")
    op.drop_table("admin_actions")

    op.drop_index("ix_schedulers_archived_at", table_name="schedulers")
    op.drop_column("schedulers", "archived_at")

    op.drop_index("ix_workers_archived_at", table_name="workers")
    op.drop_column("workers", "archived_at")

    op.drop_index("ix_jobs_deleted_at", table_name="jobs")
    op.drop_column("jobs", "deleted_at")
