"""Sync session/run deletion: cascade session delete to runs, cascade parent runs to branch descendants.

Revision ID: p9g3n004
Revises: p9g3n003
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "p9g3n004"
down_revision: str | Sequence[str] | None = "p9g3n003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite dev DBs are bootstrapped via create_all() from ORM metadata,
        # which already declares these CASCADE FKs — no named-constraint ALTER
        # exists there, so this migration is a no-op on that dialect.
        return
    # 删会话 → 级联删该会话全部 run（行业标准：子数据无父无意义，
    # 孤儿 run 不可达即垃圾）。chat_messages 已对 run CASCADE，随 run 一起清。
    op.drop_constraint("project_runs_session_id_fkey", "project_runs", type_="foreignkey")
    op.create_foreign_key(
        "project_runs_session_id_fkey",
        "project_runs",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # 分支树：删父 run → 级联删子孙分支 run（自引用 CASCADE，Postgres 递归支持）。
    op.create_foreign_key(
        "project_runs_parent_run_id_fkey",
        "project_runs",
        "project_runs",
        ["parent_run_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint("project_runs_parent_run_id_fkey", "project_runs", type_="foreignkey")
    op.drop_constraint("project_runs_session_id_fkey", "project_runs", type_="foreignkey")
    op.create_foreign_key(
        "project_runs_session_id_fkey",
        "project_runs",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
