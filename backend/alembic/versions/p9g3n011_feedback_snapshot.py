"""Feedback snapshot columns — capture query/answer/RAG sources at rating time for auditability."""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n011"
down_revision = "p9g3n010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("feedback_logs", sa.Column("query", sa.Text(), nullable=True))
    op.add_column("feedback_logs", sa.Column("answer", sa.Text(), nullable=True))
    op.add_column(
        "feedback_logs",
        sa.Column(
            "sources",
            sa.Text(),
            nullable=True,
            comment="JSON array of RAG citation sources at rating time",
        ),
    )


def downgrade() -> None:
    op.drop_column("feedback_logs", "sources")
    op.drop_column("feedback_logs", "answer")
    op.drop_column("feedback_logs", "query")
