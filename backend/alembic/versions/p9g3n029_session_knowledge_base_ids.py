"""Add knowledge_base_ids column to sessions table.

Revision ID: p9g3n029
Revises: p9g3n028
Create Date: 2026-09-01

Adds the `knowledge_base_ids` JSONB column to store which knowledge bases
are bound to a chat session for RAG retrieval.  Defaults to empty list.

Idempotent: safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n029'
down_revision: str | None = 'p9g3n028'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c['name'] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('sessions') and not _column_exists(inspector, 'sessions', 'knowledge_base_ids'):
        op.add_column(
            'sessions',
            sa.Column(
                'knowledge_base_ids',
                sa.JSON(),
                nullable=True,
                server_default='[]',
                comment='KB IDs bound to this chat session for RAG retrieval',
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('sessions') and _column_exists(inspector, 'sessions', 'knowledge_base_ids'):
        op.drop_column('sessions', 'knowledge_base_ids')
