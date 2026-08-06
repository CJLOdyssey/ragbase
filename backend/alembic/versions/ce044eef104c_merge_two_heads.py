"""merge two heads

Revision ID: ce044eef104c
Revises: 8347788032e5, e4f5a6b7c8d9
Create Date: 2026-07-14 22:23:13.061058

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'ce044eef104c'
down_revision: str | Sequence[str] | None = ('8347788032e5', 'e4f5a6b7c8d9')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
