"""AgentConfigDB, TeamDB, TeamAgentDB ORM models."""


from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from core.base import Base
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from orm.workflow import WorkflowConfigDB


class TeamDB(Base):
    """ORM model for agent teams."""

    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(16), default="active")
    category: Mapped[str] = mapped_column(
        String(16), default="dev", server_default="dev"
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_expanded: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    workflow_config_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workflow_configs.id", ondelete="SET NULL"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    members: Mapped[list["TeamAgentDB"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
        order_by="TeamAgentDB.order",
    )
    workflow_config: Mapped["WorkflowConfigDB | None"] = relationship(
        foreign_keys=[workflow_config_id],
    )

class TeamAgentDB(Base):
    """ORM model linking agents to teams."""

    __tablename__ = "team_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_config_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("agent_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(64), default="待配置角色")
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    team: Mapped["TeamDB"] = relationship(back_populates="members")
    agent_config: Mapped["AgentConfigDB | None"] = relationship()

class AgentConfigDB(Base):
    """ORM model for agent configurations."""

    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    role_identifier: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[str | None] = mapped_column(Text, nullable=True)
    mcp: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_approver: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    icon: Mapped[str] = mapped_column(String(8), default="🤖", nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
