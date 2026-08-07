"""Add is_pinned to sessions for sidebar pin-to-top.

Revision ID: p9g3n003
Revises: p9g3n002
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p9g3n003"
down_revision: str | Sequence[str] | None = "p9g3n002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(
            sa.Column("is_pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("is_pinned")
