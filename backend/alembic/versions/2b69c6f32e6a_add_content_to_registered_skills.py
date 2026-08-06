"""add content column to registered_skills

Revision ID: 2b69c6f32e6a
Revises: b590d3515bc9
Create Date: 2026-07-09 01:01:38.972860

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "2b69c6f32e6a"
down_revision: Union[str, Sequence[str], None] = "b590d3515bc9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "registered_skills",
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("registered_skills", "content")
