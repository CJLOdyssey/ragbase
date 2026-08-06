"""Drop stripped agent-studio tables.

Revision ID: c0nt3nt01drop
Revises: f7c3d9a1b2e4
Create Date: 2026-08-06

Drops tables removed from content-studio: teams, team_agents, agent_configs,
registered_tools, mcp_servers, registered_skills, workflow_configs,
workflow_nodes, workflow_edges, and the sessions.agent_id column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c0nt3nt01drop'
down_revision: str | Sequence[str] | None = 'f7c3d9a1b2e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DROPPED_TABLES = [
    "teams",
    "team_agents",
    "agent_configs",
    "registered_tools",
    "mcp_servers",
    "registered_skills",
    "workflow_configs",
    "workflow_nodes",
    "workflow_edges",
]


def upgrade() -> None:
    op.drop_index("ix_sessions_agent_id", table_name="sessions", if_exists=True)
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_constraint("sessions_agent_id_fkey", type_="foreignkey")
        batch_op.drop_column("agent_id")
    # Children before parents to satisfy FK dependencies.
    for table in ["team_agents", "workflow_edges", "workflow_nodes"]:
        op.drop_table(table)
    for table in ["workflow_configs", "teams"]:
        op.execute(f"DROP TABLE {table} CASCADE")
    for table in ["agent_configs", "registered_tools", "mcp_servers", "registered_skills"]:
        op.drop_table(table)


def downgrade() -> None:
    for table in _DROPPED_TABLES:
        op.create_table(
            table,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("agent_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key("sessions_agent_id_fkey", "agent_configs", ["agent_id"], ["id"])
