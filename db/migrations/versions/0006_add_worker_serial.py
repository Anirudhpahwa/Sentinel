"""add worker_serial column to workers

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workers", sa.Column("worker_serial", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("workers", "worker_serial")
