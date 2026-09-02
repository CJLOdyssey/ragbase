"""Add knowledge_bases.embed_model column.

Revision ID: p9g3n020
Revises: p9g3n019
Create Date: 2026-08-24

Binds each knowledge base to an embedding model (Dify/FastGPT-aligned):
vectors inside one KB must share a single embedding space. NULL is allowed
only for legacy rows created before this column — they keep the global
resolution behavior until first edit.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n020'
down_revision: str | None = 'p9g3n019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('knowledge_bases')}
    if 'embed_model' not in cols:
        op.add_column(
            'knowledge_bases',
            sa.Column('embed_model', sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('knowledge_bases')}
    if 'embed_model' in cols:
        op.drop_column('knowledge_bases', 'embed_model')
