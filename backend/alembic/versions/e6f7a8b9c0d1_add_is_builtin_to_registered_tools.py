"""add_is_builtin_to_registered_tools

Revision ID: e6f7a8b9c0d1
Revises: 17962fcb5c1d
Create Date: 2026-07-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: str | Sequence[str] | None = '17962fcb5c1d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "registered_tools",
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("registered_tools", "is_builtin")
