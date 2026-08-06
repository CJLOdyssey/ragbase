"""drop prompt_id column from registered_skills

移除 ``registered_skills`` 表的死字段 ``prompt_id``（无运行时使用）。

Revision ID: 80f4e5044d27
Revises: 57e90e58d5ea
Create Date: 2026-07-31 22:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "80f4e5044d27"
down_revision: Union[str, Sequence[str], None] = "57e90e58d5ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("registered_skills", "prompt_id")


def downgrade() -> None:
    op.add_column(
        "registered_skills",
        sa.Column("prompt_id", sa.String(length=36), nullable=True),
    )
