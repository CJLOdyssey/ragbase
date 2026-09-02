"""merge knowledge bases and sessions index heads

Revision ID: be83b3bbb10a
Revises: 97dc4aa7ce5a, p9g3n016
Create Date: 2026-08-20 09:28:53.995135

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'be83b3bbb10a'
down_revision: str | Sequence[str] | None = ('97dc4aa7ce5a', 'p9g3n016')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
