"""add sessions user_id index

Revision ID: 97dc4aa7ce5a
Revises: p9g3n015
Create Date: 2026-08-14 18:27:48.407281

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '97dc4aa7ce5a'
down_revision: str | Sequence[str] | None = 'p9g3n015'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_sessions_user_id", table_name="sessions")
