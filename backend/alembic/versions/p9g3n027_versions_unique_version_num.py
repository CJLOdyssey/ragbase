"""Add unique constraint on versions (resource_type, resource_id, version_num).

Revision ID: p9g3n027
Revises: p9g3n026
Create Date: 2026-08-26

``create_version`` computes ``max(version_num) + 1`` without locks; on
multi-instance deployments two writers could produce the same version_num
for one resource (QA A4-05). The unique index makes the race fail loud at
the database so the repository's savepoint retry can recompute, instead of
silently persisting duplicate version numbers.

Fails loud if historical duplicates exist — those are a data-integrity bug
that must be resolved manually, not papered over.

Idempotent like its predecessors: safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n027'
down_revision: str | None = 'p9g3n026'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = 'ux_versions_resource_version'


def _index_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(i['name'] == name for i in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('versions') and not _index_exists(
        inspector, 'versions', _INDEX_NAME
    ):
        op.create_index(
            _INDEX_NAME,
            'versions',
            ['resource_type', 'resource_id', 'version_num'],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('versions') and _index_exists(
        inspector, 'versions', _INDEX_NAME
    ):
        op.drop_index(_INDEX_NAME, table_name='versions')
