"""Health score snapshots — hourly error-budget samples per active user.

Feeds the monitoring page's score trend. Retained 90 days; the beat task
prunes older rows each run.
"""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n019"
down_revision = "p9g3n018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_score_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column(
            "factors",
            sa.Text(),
            nullable=True,
            comment="JSON array of {key, score, weight}",
        ),
        sa.Column("window_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_health_score_snapshots_created_at",
        "health_score_snapshots",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("health_score_snapshots")
