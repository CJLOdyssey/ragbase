"""add description and status to teams

Revision ID: c848912454db
Revises: 3a5020dfb72d
Create Date: 2026-06-30 01:53:00.548051

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c848912454db'
down_revision: str | Sequence[str] | None = '3a5020dfb72d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("teams", sa.Column("description", sa.String(256), nullable=True))
    op.add_column("teams", sa.Column("status", sa.String(16), nullable=False, server_default="active"))
    op.alter_column("teams", "status", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("teams", "status")
    op.drop_column("teams", "description")
