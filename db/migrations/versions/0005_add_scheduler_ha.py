"""add scheduler high-availability tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduler_leadership",
        sa.Column("lock_name", sa.String(length=50), nullable=False),
        sa.Column("leader_id", sa.String(length=255), nullable=True),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("acquired_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_renewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("lock_name"),
    )
    # Seed the single lock row: bootstrap state is "unheld", letting the
    # first scheduler to tick acquire it via the normal conditional UPDATE.
    op.execute("INSERT INTO scheduler_leadership (lock_name, term) VALUES ('scheduler', 0)")

    op.create_table(
        "schedulers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scheduler_name", sa.String(length=255), nullable=False),
        sa.Column("is_leader", sa.Boolean(), nullable=False),
        sa.Column("failed_election_attempts", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scheduler_name", name="uq_schedulers_scheduler_name"),
    )

    op.create_table(
        "scheduler_elections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("leader_id", sa.String(length=255), nullable=False),
        sa.Column("elected_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduler_elections_elected_at", "scheduler_elections", ["elected_at"])


def downgrade() -> None:
    op.drop_index("ix_scheduler_elections_elected_at", table_name="scheduler_elections")
    op.drop_table("scheduler_elections")
    op.drop_table("schedulers")
    op.drop_table("scheduler_leadership")
