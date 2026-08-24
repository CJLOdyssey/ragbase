"""KB parser_config + vector_chunks.enabled — configurable chunking & chunk governance.

Revision ID: p9g3n021
Revises: p9g3n020
Create Date: 2026-08-24

- knowledge_bases.parser_config: JSONB {chunk_size, overlap} — per-KB chunking
  parameters applied at (re)index time; changing them invalidates vectors.
- vector_chunks.enabled: soft-disable flag so retrieval skips individual
  chunks without a full reindex (chunk governance baseline).

Idempotent like its predecessors; safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'p9g3n021'
down_revision: str | None = 'p9g3n020'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    kb_cols = {c['name'] for c in inspector.get_columns('knowledge_bases')}
    if 'parser_config' not in kb_cols:
        op.add_column(
            'knowledge_bases',
            sa.Column('parser_config', JSONB(), nullable=True),
        )

    has_vector_chunks = inspector.has_table('vector_chunks')
    if has_vector_chunks:
        vc_cols = {c['name'] for c in inspector.get_columns('vector_chunks')}
        if 'enabled' not in vc_cols:
            op.add_column(
                'vector_chunks',
                sa.Column('enabled', sa.Boolean(), nullable=False,
                          server_default=sa.true()),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('vector_chunks'):
        vc_cols = {c['name'] for c in inspector.get_columns('vector_chunks')}
        if 'enabled' in vc_cols:
            op.drop_column('vector_chunks', 'enabled')

    kb_cols = {c['name'] for c in inspector.get_columns('knowledge_bases')}
    if 'parser_config' in kb_cols:
        op.drop_column('knowledge_bases', 'parser_config')
