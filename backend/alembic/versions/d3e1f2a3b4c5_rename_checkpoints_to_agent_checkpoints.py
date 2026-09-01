"""rename checkpoints to agent_checkpoints

Avoids table name conflict with LangGraph PostgresSaver which also
creates a table named ``checkpoints``.

Revision ID: d3e1f2a3b4c5
Revises: c848912454db
Create Date: 2026-06-30 07:35:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "c848912454db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(conn)
    if "checkpoints" in inspector.get_table_names():
        op.rename_table("checkpoints", "agent_checkpoints")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(conn)
    tables = inspector.get_table_names()
    # Restore the pre-rename layout: exactly one ``checkpoints`` table.
    # 8347788032e5.downgrade restores BOTH runtime artifacts (LangGraph's
    # ``checkpoints`` and the legacy ``agent_checkpoints``); the rename-back
    # can only keep one — drop the leftover duplicate rather than collide
    # (both are runtime-owned; neither is created by the migration chain).
    if "agent_checkpoints" not in tables:
        return
    if "checkpoints" in tables:
        op.drop_table("agent_checkpoints")
    else:
        op.rename_table("agent_checkpoints", "checkpoints")
