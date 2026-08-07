"""Drop content-generation leftovers: compose_templates table and project_runs generation columns.

Revision ID: p9g3n002
Revises: p9g3n001
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p9g3n002"
down_revision: str | Sequence[str] | None = "p9g3n001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GENERATION_COLUMNS = ["content_type", "generation_mode", "topic", "result_json", "template_id"]


def upgrade() -> None:
    op.drop_table("compose_templates")
    with op.batch_alter_table("project_runs") as batch_op:
        for col in _GENERATION_COLUMNS:
            batch_op.drop_column(col)


def downgrade() -> None:
    with op.batch_alter_table("project_runs") as batch_op:
        batch_op.add_column(sa.Column("content_type", sa.String(32), server_default="generic", nullable=False))
        batch_op.add_column(sa.Column("generation_mode", sa.String(32), server_default="generate", nullable=False))
        batch_op.add_column(sa.Column("topic", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("result_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("template_id", sa.String(36), nullable=True))
    op.create_table(
        "compose_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("layout_json", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
