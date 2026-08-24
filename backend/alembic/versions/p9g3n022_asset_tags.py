"""Add assets.tags — user-curated labels injected into chunk tags at index time.

Revision ID: p9g3n022
Revises: p9g3n021
Create Date: 2026-08-24

Enables tag-based retrieval filtering (the search layer already supports a
tag_filter leg). JSON on sqlite / JSONB on postgres, mirroring the
capabilities-column pattern.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'p9g3n022'
down_revision: str | None = 'p9g3n021'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('assets')}
    if 'tags' not in cols:
        op.add_column(
            'assets',
            sa.Column('tags', JSONB().with_variant(sa.JSON(), 'sqlite'),
                      nullable=False, server_default='[]'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('assets')}
    if 'tags' in cols:
        op.drop_column('assets', 'tags')
