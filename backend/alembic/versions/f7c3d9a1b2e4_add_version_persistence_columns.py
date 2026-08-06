"""add version persistence columns to chat_messages and project_runs

Revision ID: f7c3d9a1b2e4
Revises: a1f2b3c4d5e6
Create Date: 2026-08-02 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7c3d9a1b2e4'
down_revision: Union[str, Sequence[str], None] = 'a1f2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_messages', sa.Column('versions', sa.Text(), nullable=True))
    op.add_column('chat_messages', sa.Column('thinking_versions', sa.Text(), nullable=True))
    op.add_column('project_runs', sa.Column('parent_run_id', sa.String(36), nullable=True))
    op.add_column('project_runs', sa.Column('requirement_versions', sa.Text(), nullable=True))
    op.create_index('ix_project_runs_parent_run_id', 'project_runs', ['parent_run_id'])


def downgrade() -> None:
    op.drop_index('ix_project_runs_parent_run_id', table_name='project_runs')
    op.drop_column('project_runs', 'requirement_versions')
    op.drop_column('project_runs', 'parent_run_id')
    op.drop_column('chat_messages', 'thinking_versions')
    op.drop_column('chat_messages', 'versions')
