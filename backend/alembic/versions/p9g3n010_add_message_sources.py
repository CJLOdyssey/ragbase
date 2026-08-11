"""Chat message sources column — structured RAG citations for message UI (auditability)."""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n010"
down_revision = "p9g3n009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column(
            "sources",
            sa.Text(),
            nullable=True,
            comment="JSON array of RAG citation sources [{asset_id, asset_name, text, similarity}]",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "sources")
