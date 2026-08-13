"""Shadow retrieval log (O4) — variant-config comparison, append-only.

Mirrors retrieval_logs plus a variant label; kept separate so shadow
replays never pollute the online monitoring metrics.
"""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n015"
down_revision = "p9g3n014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shadow_retrieval_logs",
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
        sa.Column("variant", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shadow_retrieval_logs_user_id", "shadow_retrieval_logs", ["user_id"])
    op.create_index("ix_shadow_retrieval_logs_session_id", "shadow_retrieval_logs", ["session_id"])
    op.create_index("ix_shadow_retrieval_logs_created_at", "shadow_retrieval_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("shadow_retrieval_logs")
