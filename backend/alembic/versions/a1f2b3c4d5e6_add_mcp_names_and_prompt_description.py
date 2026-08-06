"""add mcp_names to registered_skills and description to prompts

为 ``registered_skills`` 表添加 ``mcp_names`` JSON 列（工具/MCP 拆分），
为 ``prompts`` 表添加 ``description`` TEXT 列（提示词描述字段）。

Revision ID: a1f2b3c4d5e6
Revises: 80f4e5044d27
Create Date: 2026-08-01 20:45:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f2b3c4d5e6"
down_revision: str | Sequence[str] | None = "80f4e5044d27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add mcp_names (JSON) to registered_skills and description (TEXT) to prompts."""
    op.add_column(
        "registered_skills",
        sa.Column("mcp_names", sa.JSON(), nullable=True),
    )
    op.add_column(
        "prompts",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Drop the added columns."""
    op.drop_column("prompts", "description")
    op.drop_column("registered_skills", "mcp_names")
