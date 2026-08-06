"""Add generation columns, assets and compose_templates tables.

Revision ID: p9g3n001
Revises: c0nt3nt01drop
Create Date: 2026-08-06
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "p9g3n001"
down_revision: str | Sequence[str] | None = "c0nt3nt01drop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TEMPLATES = [
    {
        "id": "xiaohongshu",
        "name": "xiaohongshu",
        "is_default": True,
        "layout_json": {
            "canvas": {"width": 1080, "height": 1440, "ratio": "3:4"},
            "blocks": ["cover_image", "title", "summary", "footer"],
        },
    },
    {
        "id": "wechat",
        "name": "wechat",
        "is_default": False,
        "layout_json": {
            "canvas": {"width": 1280, "height": 720, "ratio": "16:9"},
            "blocks": ["title", "summary", "cover_image"],
        },
    },
    {
        "id": "square",
        "name": "square",
        "is_default": False,
        "layout_json": {
            "canvas": {"width": 1024, "height": 1024, "ratio": "1:1"},
            "blocks": ["title", "summary", "cover_image", "footer"],
        },
    },
]


def upgrade() -> None:
    with op.batch_alter_table("project_runs") as batch_op:
        batch_op.add_column(
            sa.Column("content_type", sa.String(32), server_default="generic", nullable=False)
        )
        batch_op.add_column(
            sa.Column("generation_mode", sa.String(32), server_default="generate", nullable=False)
        )
        batch_op.add_column(sa.Column("topic", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("result_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("template_id", sa.String(36), nullable=True))

    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("asset_type", sa.String(32), server_default="document", nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("indexed", sa.Boolean(), server_default="f", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "compose_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("layout_json", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="f", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    conn = op.get_bind()
    for t in _TEMPLATES:
        conn.execute(
            sa.text(
                "INSERT INTO compose_templates (id, name, layout_json, is_default, created_at) "
                "VALUES (:id, :name, CAST(:layout AS JSON), :is_default, :created)"
            ),
            {
                "id": t["id"],
                "name": t["name"],
                "layout": json.dumps(t["layout_json"]),
                "is_default": t["is_default"],
                "created": datetime.now(UTC),
            },
        )


def downgrade() -> None:
    op.drop_table("compose_templates")
    op.drop_table("assets")
    with op.batch_alter_table("project_runs") as batch_op:
        batch_op.drop_column("template_id")
        batch_op.drop_column("result_json")
        batch_op.drop_column("topic")
        batch_op.drop_column("generation_mode")
        batch_op.drop_column("content_type")
