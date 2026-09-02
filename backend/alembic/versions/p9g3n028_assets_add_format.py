"""Add format column to assets table.

Revision ID: p9g3n028
Revises: p9g3n027
Create Date: 2026-09-01

Adds the `format` column (file extension: pdf, docx, png, etc.) to store
the specific file format for precise filtering and display.

Also updates the `asset_type` CHECK constraint to support the new `data`
category (xlsx, csv, xls) alongside existing `document` and `image`.

Idempotent: safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n028'
down_revision: str | None = 'p9g3n027'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c['name'] == column for c in inspector.get_columns(table))


def _constraint_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(c['name'] == name for c in inspector.get_check_constraints(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Add format column
    if inspector.has_table('assets') and not _column_exists(inspector, 'assets', 'format'):
        op.add_column(
            'assets',
            sa.Column('format', sa.String(16), nullable=True, comment='File extension: pdf, docx, png, etc.'),
        )

    # 2. Update asset_type CHECK constraint to support 'data' category
    if inspector.has_table('assets') and _constraint_exists(inspector, 'assets', 'chk_assets_asset_type'):
        op.drop_constraint('chk_assets_asset_type', 'assets', type_='check')

    if inspector.has_table('assets') and not _constraint_exists(inspector, 'assets', 'chk_assets_asset_type'):
        op.create_check_constraint(
            'chk_assets_asset_type',
            'assets',
            "asset_type IN ('document', 'image', 'data')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Revert asset_type CHECK constraint to original
    if inspector.has_table('assets') and _constraint_exists(inspector, 'assets', 'chk_assets_asset_type'):
        op.drop_constraint('chk_assets_asset_type', 'assets', type_='check')

    if inspector.has_table('assets') and not _constraint_exists(inspector, 'assets', 'chk_assets_asset_type'):
        op.create_check_constraint(
            'chk_assets_asset_type',
            'assets',
            "asset_type IN ('document', 'image')",
        )

    # 2. Remove format column
    if inspector.has_table('assets') and _column_exists(inspector, 'assets', 'format'):
        op.drop_column('assets', 'format')
