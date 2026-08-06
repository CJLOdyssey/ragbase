"""add content column to registered_skills

Revision ID: 2b69c6f32e6a
Revises: b590d3515bc9
Create Date: 2026-07-09 01:01:38.972860

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2b69c6f32e6a"
down_revision: str | Sequence[str] | None = "b590d3515bc9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "registered_skills",
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("registered_skills", "content")
