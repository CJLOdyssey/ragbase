"""Drop the command_logs table — zero-consumer skeleton leftover.

Revision ID: p9g3n025
Revises: p9g3n024
Create Date: 2026-08-26

The command-log feature was never wired: repository ``log_command`` had no
callers and was removed (QA A4-04), leaving the table with no write path.
The ORM model (CommandLogDB) is removed in the same change so fresh
``create_all()`` databases stop creating it; this migration drops it from
databases provisioned by earlier Alembic revisions.

Idempotent like its predecessors: safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n025'
down_revision: str | None = 'p9g3n024'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('command_logs'):
        return
    index_names = {i['name'] for i in inspector.get_indexes('command_logs')}
    if 'ix_command_logs_session_id' in index_names:
        op.drop_index('ix_command_logs_session_id', table_name='command_logs')
    op.drop_table('command_logs')


def downgrade() -> None:
    """Recreate the table exactly as 3a5020dfb72d defined it."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('command_logs'):
        return
    op.create_table(
        'command_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'session_id',
            sa.String(36),
            sa.ForeignKey('sessions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('command_id', sa.String(64), nullable=False),
        sa.Column('command_name', sa.String(64), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('result', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_command_logs_session_id', 'command_logs', ['session_id'])
