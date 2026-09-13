"""Add request-context columns to audit_logs.

Revision ID: p9g3n030
Revises: p9g3n029
Create Date: 2026-09-13

Adds ``user_name`` / ``client_ip`` / ``user_agent`` / ``request_id`` so audit
entries carry the authenticated user and request origin. Populated by
AuthMiddleware via ``core.audit.set_audit_context``.

Idempotent: safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n030'
down_revision: str | None = 'p9g3n029'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS: tuple[tuple[str, sa.types.TypeEngine[str]], ...] = (
    ('user_name', sa.String(length=64)),
    ('client_ip', sa.String(length=64)),
    ('user_agent', sa.String(length=255)),
    ('request_id', sa.String(length=36)),
)


def _column_exists(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c['name'] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('audit_logs'):
        return
    for name, type_ in _COLUMNS:
        if not _column_exists(inspector, 'audit_logs', name):
            # server_default keeps legacy rows valid under NOT NULL;
            # the ORM supplies '' for new rows.
            op.add_column(
                'audit_logs',
                sa.Column(name, type_, nullable=False, server_default=''),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('audit_logs'):
        return
    for name, _ in _COLUMNS:
        if _column_exists(inspector, 'audit_logs', name):
            op.drop_column('audit_logs', name)
