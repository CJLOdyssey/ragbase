"""Append-only retrieval activity log — OWASP LLM08 forensics + quality data."""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n014"
down_revision = "p9g3n013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("rerank", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_score", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "sources",
            sa.Text(),
            nullable=True,
            comment="JSON array of {asset_id, asset_name, similarity}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retrieval_logs_user_id", "retrieval_logs", ["user_id"])
    op.create_index("ix_retrieval_logs_session_id", "retrieval_logs", ["session_id"])
    op.create_index("ix_retrieval_logs_created_at", "retrieval_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("retrieval_logs")
