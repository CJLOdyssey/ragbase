"""Add assets.index_error — persist indexing failure reason on the asset row.

Revision ID: p9g3n023
Revises: p9g3n022
Create Date: 2026-08-25

Index failures previously lived only in Redis progress keys (10-min TTL),
so a failed asset degraded to "unindexed" in the UI after refresh. The
failure terminal state must survive in the DB (industry standard: Dify
documents.error / indexing_status).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n023'
down_revision: str | None = 'p9g3n022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('assets')}
    if 'index_error' not in cols:
        op.add_column('assets', sa.Column('index_error', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('assets')}
    if 'index_error' in cols:
        op.drop_column('assets', 'index_error')
