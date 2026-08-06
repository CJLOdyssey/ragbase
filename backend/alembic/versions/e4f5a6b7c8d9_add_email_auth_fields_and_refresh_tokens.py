"""add email auth fields and refresh_tokens table

Revision ID: e4f5a6b7c8d9
Revises: d3e1f2a3b4c5
Create Date: 2026-07-13 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: add email auth fields ───────────────────────────────────
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False))
        batch_op.add_column(sa.Column("auth_provider", sa.String(16), server_default="email", nullable=False))
        batch_op.add_column(sa.Column("auth_provider_id", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    # Migrate existing rows: copy username -> email as legacy fallback
    op.execute("UPDATE users SET email = username || '@legacy.local' WHERE email IS NULL")
    op.execute("UPDATE users SET is_verified = true WHERE is_verified IS NULL")

    # Make email NOT NULL + unique after populating
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("email", nullable=False)
        batch_op.create_index(op.f("ix_users_email"), ["email"], unique=True)

    # ── refresh_tokens table ───────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_hash", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"])
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email")
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_attempts")
        batch_op.drop_column("auth_provider_id")
        batch_op.drop_column("auth_provider")
        batch_op.drop_column("is_verified")
        batch_op.drop_column("email")
