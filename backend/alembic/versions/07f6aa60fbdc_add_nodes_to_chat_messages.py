"""add_nodes_to_chat_messages

Revision ID: 07f6aa60fbdc
Revises: d3e1f2a3b4c5
Create Date: 2026-07-02 08:20:04.010238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07f6aa60fbdc'
down_revision: Union[str, Sequence[str], None] = 'd3e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("nodes", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "nodes")
