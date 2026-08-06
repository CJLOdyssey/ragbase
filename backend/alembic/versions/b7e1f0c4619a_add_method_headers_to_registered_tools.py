"""add_method_headers_to_registered_tools

Revision ID: b7e1f0c4619a
Revises: 07f6aa60fbdc
Create Date: 2026-07-02 12:08:02.717472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e1f0c4619a'
down_revision: Union[str, Sequence[str], None] = '07f6aa60fbdc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("registered_tools", sa.Column("method", sa.String(8), nullable=False, server_default="GET"))
    op.add_column("registered_tools", sa.Column("headers", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("registered_tools", "headers")
    op.drop_column("registered_tools", "method")
