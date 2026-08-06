"""add_fk_indexes_memory_edges_nodes_agents

Revision ID: 17962fcb5c1d
Revises: ce044eef104c
Create Date: 2026-07-21 14:26:17.571203

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17962fcb5c1d'
down_revision: Union[str, Sequence[str], None] = 'ce044eef104c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing FK indexes for query performance."""
    op.create_index(op.f('ix_memory_entries_run_id'), 'memory_entries', ['run_id'], unique=False)
    op.create_index(op.f('ix_team_agents_agent_config_id'), 'team_agents', ['agent_config_id'], unique=False)
    op.create_index(op.f('ix_workflow_edges_from_node_id'), 'workflow_edges', ['from_node_id'], unique=False)
    op.create_index(op.f('ix_workflow_edges_to_node_id'), 'workflow_edges', ['to_node_id'], unique=False)
    op.create_index(op.f('ix_workflow_nodes_agent_config_id'), 'workflow_nodes', ['agent_config_id'], unique=False)


def downgrade() -> None:
    """Remove the added indexes."""
    op.drop_index(op.f('ix_workflow_nodes_agent_config_id'), table_name='workflow_nodes')
    op.drop_index(op.f('ix_workflow_edges_to_node_id'), table_name='workflow_edges')
    op.drop_index(op.f('ix_workflow_edges_from_node_id'), table_name='workflow_edges')
    op.drop_index(op.f('ix_team_agents_agent_config_id'), table_name='team_agents')
    op.drop_index(op.f('ix_memory_entries_run_id'), table_name='memory_entries')
