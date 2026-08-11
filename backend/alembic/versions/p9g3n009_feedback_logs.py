"""RAG quality feedback table — online eval loop intake (feedback_logs)."""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n009"
down_revision = "p9g3n008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("rating", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feedback_logs_run_id", "feedback_logs", ["run_id"])
    op.create_index("ix_feedback_logs_user_id", "feedback_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_logs_user_id", table_name="feedback_logs")
    op.drop_index("ix_feedback_logs_run_id", table_name="feedback_logs")
    op.drop_table("feedback_logs")
