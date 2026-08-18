"""Add knowledge_bases table and asset knowledge_base_id column.

Revision ID: p9g3n016
Revises: p9g3n015
Create Date: 2026-08-18

Adds multi-knowledge-base isolation support:
- New `knowledge_bases` table for user-level KB grouping
- New `knowledge_base_id` column on `assets` table for KB assignment
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n016'
down_revision: Union[str, None] = 'p9g3n015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column(
        'assets',
        sa.Column('knowledge_base_id', sa.String(36), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column('assets', 'knowledge_base_id')
    op.drop_table('knowledge_bases')
