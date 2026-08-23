"""Feedback review queue — triage bad ratings into root-caused cases.

One review row per feedback (unique feedback_id). Status flow:
pending → resolved | dismissed. Root cause enum feeds the future
golden-set eval pipeline.
"""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n018"
down_revision = "p9g3n017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "feedback_id",
            sa.String(36),
            sa.ForeignKey("feedback_logs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "root_cause",
            sa.String(32),
            nullable=True,
            comment="retrieval_miss|wrong_answer|bad_format|other",
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
            comment="pending|resolved|dismissed",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_feedback_reviews_status", "feedback_reviews", ["status"]
    )


def downgrade() -> None:
    op.drop_table("feedback_reviews")
