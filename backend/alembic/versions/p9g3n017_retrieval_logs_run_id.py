"""Add run_id to retrieval_logs — links each retrieval to its chat run."""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n017"
down_revision = "be83b3bbb10a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "retrieval_logs",
        sa.Column(
            "run_id",
            sa.String(36),
            nullable=True,
            comment="project_runs.id — enables log-to-conversation replay",
        ),
    )
    op.create_index("ix_retrieval_logs_run_id", "retrieval_logs", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_retrieval_logs_run_id", table_name="retrieval_logs")
    op.drop_column("retrieval_logs", "run_id")
