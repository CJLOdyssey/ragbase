"""Add audit_logs + versions tables and sessions.kind — close ORM/migration gaps.

Revision ID: p9g3n024
Revises: p9g3n023
Create Date: 2026-08-25

The ORM (orm/infra.py, orm/prompt_db.py, orm/session.py) declares these
objects, but no migration created them — runtime init_db() create_all() and
an ad-hoc ALTER patched the gap. This migration makes the Alembic chain
self-sufficient for production (alembic upgrade head only).

Idempotent like its predecessors: safe on fresh and legacy databases.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p9g3n024'
down_revision: str | None = 'p9g3n023'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('audit_logs'):
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('action', sa.String(64), nullable=False),
            sa.Column('entity_type', sa.String(32), nullable=False),
            sa.Column('entity_name', sa.String(255), server_default=''),
            sa.Column('detail', sa.Text(), server_default=''),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
        op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    if not inspector.has_table('versions'):
        op.create_table(
            'versions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('resource_type', sa.String(32), nullable=False),
            sa.Column('resource_id', sa.String(36), nullable=False),
            sa.Column('version_num', sa.Integer(), nullable=False),
            sa.Column('snapshot', sa.JSON(), nullable=False),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_versions_resource_type', 'versions', ['resource_type'])
        op.create_index('ix_versions_resource_id', 'versions', ['resource_id'])
        op.create_index('ix_versions_resource', 'versions', ['resource_type', 'resource_id'])

    sessions_cols = {c['name'] for c in inspector.get_columns('sessions')}
    if 'kind' not in sessions_cols:
        op.add_column(
            'sessions',
            sa.Column('kind', sa.String(16), nullable=False, server_default='normal'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    sessions_cols = {c['name'] for c in inspector.get_columns('sessions')}
    if 'kind' in sessions_cols:
        op.drop_column('sessions', 'kind')

    if inspector.has_table('versions'):
        op.drop_index('ix_versions_resource', table_name='versions')
        op.drop_index('ix_versions_resource_id', table_name='versions')
        op.drop_index('ix_versions_resource_type', table_name='versions')
        op.drop_table('versions')

    if inspector.has_table('audit_logs'):
        op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
        op.drop_index('ix_audit_logs_action', table_name='audit_logs')
        op.drop_table('audit_logs')