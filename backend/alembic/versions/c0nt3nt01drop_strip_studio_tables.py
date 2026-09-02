"""Drop stripped studio tables.

Revision ID: c0nt3nt01drop
Revises: f7c3d9a1b2e4
Create Date: 2026-08-06

Drops tables stripped from the shared base: teams, team_agents, agent_configs,
registered_tools, mcp_servers, registered_skills, workflow_configs,
workflow_nodes, workflow_edges, and the sessions.agent_id column.

Downgrade recreates each table with its FULL schema as of f7c3d9a1b2e4
(columns added/removed by every revision up to that point, plus all indexes
that existed back then — including the FK indexes 17962fcb5c1d adds, whose
downgrade runs later in the rollback and expects them present). Skeleton
recreation here previously broke ``alembic downgrade base`` at a1f2b3c4d5e6
(QA A3-11).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c0nt3nt01drop'
down_revision: str | Sequence[str] | None = 'f7c3d9a1b2e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_sessions_agent_id", table_name="sessions", if_exists=True)
    with op.batch_alter_table("sessions") as batch_op:
        # Named constraint exists only on PostgreSQL; SQLite batch recreate
        # drops the inline FK together with the column.
        if op.get_bind().dialect.name == "postgresql":
            batch_op.drop_constraint("sessions_agent_id_fkey", type_="foreignkey")
        batch_op.drop_column("agent_id")
    # Children before parents to satisfy FK dependencies.
    for table in ["team_agents", "workflow_edges", "workflow_nodes"]:
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        # PostgreSQL: FK from teams.workflow_config_id blocks plain drop.
        for table in ["workflow_configs", "teams"]:
            op.execute(f"DROP TABLE {table} CASCADE")
    else:
        op.drop_table("workflow_configs")
        op.drop_table("teams")
    for table in ["agent_configs", "registered_tools", "mcp_servers", "registered_skills"]:
        op.drop_table(table)


def _create_teams() -> None:
    """teams at f7c3d9a1b2e4 = base + category + description/status.

    workflow_config_id is attached afterwards so the FK can reference
    workflow_configs, which itself references teams (creation-order cycle).
    """
    op.create_table(
        "teams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("is_expanded", sa.Boolean(), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(256), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("category", sa.String(16), nullable=False, server_default="dev"),
    )
    op.create_index(op.f("ix_teams_name"), "teams", ["name"], unique=True)
    op.create_table(
        "workflow_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("team_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("max_rounds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_workflow_configs_team_id"), "workflow_configs", ["team_id"], unique=True)
    with op.batch_alter_table("teams") as batch_op:
        batch_op.add_column(sa.Column("workflow_config_id", sa.String(36), nullable=True))
        # Named constraint only materializes on PostgreSQL; SQLite stores an
        # inline FK that the next batch recreate picks up automatically.
        if op.get_bind().dialect.name == "postgresql":
            batch_op.create_foreign_key(
                "fk_teams_workflow_config_id",
                "workflow_configs",
                ["workflow_config_id"],
                ["id"],
                ondelete="SET NULL",
            )


def _create_registered_skills() -> None:
    """registered_skills at f7c3d9a1b2e4 = base − description/owner_id/prompt_id
    + content + script_files + mcp_names."""
    op.create_table(
        "registered_skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("author", sa.String(64), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("tool_names", sa.JSON(), nullable=False),
        sa.Column("output_constraint", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("script_files", sa.JSON(), nullable=True),
        sa.Column("mcp_names", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # Creation order resolves the FK web: teams ↔ workflow_configs cycle is
    # broken by attaching teams.workflow_config_id after both tables exist.
    _create_teams()
    op.create_table(
        "agent_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("role_identifier", sa.String(32), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("output_constraints", sa.Text(), nullable=True),
        sa.Column("tools", sa.Text(), nullable=True),
        sa.Column("mcp", sa.Text(), nullable=True),
        sa.Column("skills", sa.Text(), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_approver", sa.Boolean(), nullable=False),
        sa.Column("icon", sa.String(8), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        op.f("ix_agent_configs_role_identifier"), "agent_configs", ["role_identifier"], unique=True
    )
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("endpoint", sa.String(256), nullable=False),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    # registered_tools at f7c3d9a1b2e4 = base + method/headers + is_builtin.
    op.create_table(
        "registered_tools",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("endpoint", sa.String(256), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("method", sa.String(8), nullable=False, server_default="GET"),
        sa.Column("headers", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    _create_registered_skills()
    op.create_table(
        "team_agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("team_id", sa.String(36), nullable=False),
        sa.Column("agent_config_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_config_id"], ["agent_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_team_agents_team_id"), "team_agents", ["team_id"], unique=False)
    # FK indexes added by 17962fcb5c1d existed here historically; its
    # downgrade runs later in the rollback and drops them by name.
    op.create_index(
        op.f("ix_team_agents_agent_config_id"), "team_agents", ["agent_config_id"], unique=False
    )
    op.create_table(
        "workflow_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_config_id", sa.String(36), nullable=False),
        sa.Column("agent_config_id", sa.String(36), nullable=False),
        sa.Column("role_identifier", sa.String(32), nullable=False),
        sa.Column("strategy", sa.String(16), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_config_id"], ["agent_configs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workflow_config_id"], ["workflow_configs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_workflow_nodes_workflow_config_id"),
        "workflow_nodes",
        ["workflow_config_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_nodes_agent_config_id"), "workflow_nodes", ["agent_config_id"], unique=False
    )
    op.create_table(
        "workflow_edges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_config_id", sa.String(36), nullable=False),
        sa.Column("from_node_id", sa.String(36), nullable=False),
        sa.Column("to_node_id", sa.String(36), nullable=False),
        sa.Column("condition_key", sa.String(128), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["from_node_id"], ["workflow_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_node_id"], ["workflow_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_config_id"], ["workflow_configs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_workflow_edges_workflow_config_id"),
        "workflow_edges",
        ["workflow_config_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_edges_from_node_id"), "workflow_edges", ["from_node_id"], unique=False
    )
    op.create_index(
        op.f("ix_workflow_edges_to_node_id"), "workflow_edges", ["to_node_id"], unique=False
    )

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("agent_id", sa.String(36), nullable=True))
        # Same name and ondelete as the original 3a5020dfb72d definition so
        # the PG constraint the upgrade drops is restored byte-for-byte.
        batch_op.create_foreign_key(
            "sessions_agent_id_fkey",
            "agent_configs",
            ["agent_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(op.f("ix_sessions_agent_id"), "sessions", ["agent_id"], unique=False)
