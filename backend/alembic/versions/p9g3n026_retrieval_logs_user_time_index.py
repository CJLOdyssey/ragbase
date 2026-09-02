"""Add composite index on retrieval_logs (user_id, created_at).

Revision ID: p9g3n026
Revises: p9g3n025
Create Date: 2026-08-26

The monitoring/retrieval-log hot query filters ``WHERE user_id = ? AND
created_at BETWEEN ? AND ?``. The two single-column indexes force the
planner to pick one and filter the rest post-hoc (QA A5-12); a composite
index answers both predicates in one seek on large tables.

Idempotent like its predecessors: safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n026'
down_revision: str | None = 'p9g3n025'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = 'ix_retrieval_logs_user_created'


def _index_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(i['name'] == name for i in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('retrieval_logs') and not _index_exists(
        inspector, 'retrieval_logs', _INDEX_NAME
    ):
        op.create_index(_INDEX_NAME, 'retrieval_logs', ['user_id', 'created_at'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('retrieval_logs') and _index_exists(
        inspector, 'retrieval_logs', _INDEX_NAME
    ):
        op.drop_index(_INDEX_NAME, table_name='retrieval_logs')
