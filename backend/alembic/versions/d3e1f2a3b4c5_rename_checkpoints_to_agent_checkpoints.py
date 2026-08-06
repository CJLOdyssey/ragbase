"""rename checkpoints to agent_checkpoints

Avoids table name conflict with LangGraph PostgresSaver which also
creates a table named ``checkpoints``.

Revision ID: d3e1f2a3b4c5
Revises: c848912454db
Create Date: 2026-06-30 07:35:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c848912454db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(conn)
    if "checkpoints" in inspector.get_table_names():
        op.rename_table("checkpoints", "agent_checkpoints")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(conn)
    if "agent_checkpoints" in inspector.get_table_names():
        op.rename_table("agent_checkpoints", "checkpoints")
