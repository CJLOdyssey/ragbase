"""Attachments decoupled from sessions: user_id column, session_id nullable.

Pre-session uploads (first message carries files before any session exists)
are owned by the uploader; session_id is bound later by run creation.
"""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n008"
down_revision = "p9g3n007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attachments",
        sa.Column("user_id", sa.String(length=128), nullable=True),
    )
    with op.batch_alter_table("attachments") as batch_op:
        batch_op.alter_column(
            "session_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )
    op.create_index("ix_attachments_user_id", "attachments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_attachments_user_id", table_name="attachments")
    with op.batch_alter_table("attachments") as batch_op:
        batch_op.alter_column(
            "session_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
    op.drop_column("attachments", "user_id")
