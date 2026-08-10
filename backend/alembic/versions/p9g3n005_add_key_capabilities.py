"""Add user_api_keys.capabilities (JSONB array), drop usage_type.

Legacy mapping: chat->[llm] vector->[embedding] general->[llm,embedding]
                image->[tool] tool->[tool] audio->[]
"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "p9g3n005"
down_revision = "p9g3n004"
branch_labels = None
depends_on = None

LEGACY = {
    "chat": ["llm"],
    "vector": ["embedding"],
    "general": ["llm", "embedding"],
    "image": ["tool"],
    "tool": ["tool"],
    "audio": [],
}


def upgrade() -> None:
    op.add_column(
        "user_api_keys",
        sa.Column(
            "capabilities",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, usage_type FROM user_api_keys")).fetchall()
    for key_id, usage in rows:
        caps = LEGACY.get(usage, [])
        conn.execute(
            sa.text(
                "UPDATE user_api_keys SET capabilities = CAST(:caps AS jsonb) WHERE id = :id"
            ),
            {"caps": json.dumps(caps), "id": key_id},
        )
    op.drop_column("user_api_keys", "usage_type")


def downgrade() -> None:
    op.add_column(
        "user_api_keys",
        sa.Column("usage_type", sa.String(), nullable=False, server_default="chat"),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, capabilities FROM user_api_keys")).fetchall()
    # Best-effort: first capability wins; empty -> chat
    for key_id, caps in rows:
        usage = caps[0] if caps else "chat"
        conn.execute(
            sa.text("UPDATE user_api_keys SET usage_type = :u WHERE id = :id"),
            {"u": usage, "id": key_id},
        )
    op.drop_column("user_api_keys", "capabilities")
