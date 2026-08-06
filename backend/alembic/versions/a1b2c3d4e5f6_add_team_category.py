"""Add category column to teams table

Revision ID: a1b2c3d4e5f6
Revises: 17962fcb5c1d
Create Date: 2026-07-28 09:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "17962fcb5c1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "teams",
        sa.Column("category", sa.String(16), nullable=False, server_default="dev"),
    )


def downgrade() -> None:
    op.drop_column("teams", "category")
