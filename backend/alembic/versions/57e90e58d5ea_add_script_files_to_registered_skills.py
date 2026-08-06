"""add script_files column to registered_skills

新增 ``script_files`` JSON 列，存储 SKILL 目录导入时的附加文件内容
（如 scripts/*、references/*、resources/*）。

Revision ID: 57e90e58d5ea
Revises: a1b2c3d4e5f6, e6f7a8b9c0d1
Create Date: 2026-07-31 09:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "57e90e58d5ea"
down_revision: str | Sequence[str] | None = ("a1b2c3d4e5f6", "e6f7a8b9c0d1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "registered_skills",
        sa.Column("script_files", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("registered_skills", "script_files")
