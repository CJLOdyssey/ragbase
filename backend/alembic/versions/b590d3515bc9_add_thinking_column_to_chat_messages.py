"""add thinking column to chat_messages

Revision ID: b590d3515bc9
Revises: b7e1f0c4619a
Create Date: 2026-07-02 18:53:05.788758

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b590d3515bc9'
down_revision: Union[str, Sequence[str], None] = 'b7e1f0c4619a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_messages', sa.Column('thinking', sa.Text(), nullable=True))
    op.drop_column('chat_messages', 'nodes')


def downgrade() -> None:
    op.add_column('chat_messages', sa.Column('nodes', sa.TEXT(), nullable=True))
    op.drop_column('chat_messages', 'thinking')
