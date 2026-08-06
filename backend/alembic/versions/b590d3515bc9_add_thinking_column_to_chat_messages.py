"""add thinking column to chat_messages

Revision ID: b590d3515bc9
Revises: b7e1f0c4619a
Create Date: 2026-07-02 18:53:05.788758

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b590d3515bc9'
down_revision: str | Sequence[str] | None = 'b7e1f0c4619a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('chat_messages', sa.Column('thinking', sa.Text(), nullable=True))
    op.drop_column('chat_messages', 'nodes')


def downgrade() -> None:
    op.add_column('chat_messages', sa.Column('nodes', sa.TEXT(), nullable=True))
    op.drop_column('chat_messages', 'thinking')
