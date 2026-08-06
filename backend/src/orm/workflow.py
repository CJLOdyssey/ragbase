"""WorkflowConfigDB, WorkflowNodeDB, WorkflowEdgeDB ORM models."""


from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from core.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from orm.agent import AgentConfigDB


class WorkflowConfigDB(Base):
    __tablename__ = "workflow_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    max_rounds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    nodes: Mapped[list["WorkflowNodeDB"]] = relationship(
        back_populates="workflow_config",
        cascade="all, delete-orphan",
        order_by="WorkflowNodeDB.order",
    )
    edges: Mapped[list["WorkflowEdgeDB"]] = relationship(
        back_populates="workflow_config",
        cascade="all, delete-orphan",
    )

class WorkflowNodeDB(Base):
    __tablename__ = "workflow_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_configs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    role_identifier: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy: Mapped[str] = mapped_column(String(16), default="generator", nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    workflow_config: Mapped["WorkflowConfigDB"] = relationship(back_populates="nodes")
    agent_config: Mapped["AgentConfigDB"] = relationship()
    outgoing_edges: Mapped[list["WorkflowEdgeDB"]] = relationship(
        back_populates="from_node",
        foreign_keys="WorkflowEdgeDB.from_node_id",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["WorkflowEdgeDB"]] = relationship(
        back_populates="to_node",
        foreign_keys="WorkflowEdgeDB.to_node_id",
        cascade="all, delete-orphan",
    )

class WorkflowEdgeDB(Base):
    __tablename__ = "workflow_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    condition_key: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    workflow_config: Mapped["WorkflowConfigDB"] = relationship(back_populates="edges")
    from_node: Mapped["WorkflowNodeDB"] = relationship(
        back_populates="outgoing_edges", foreign_keys=[from_node_id]
    )
    to_node: Mapped["WorkflowNodeDB"] = relationship(
        back_populates="incoming_edges", foreign_keys=[to_node_id]
    )
