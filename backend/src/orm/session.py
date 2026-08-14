"""Session, ProjectRun, MemoryEntry, ChatMessage ORM models."""


from datetime import UTC, datetime
from uuid import uuid4

from core.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class SessionDB(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(256), default="新对话")
    user_id: Mapped[str] = mapped_column(String(128), default="default", index=True)
    kind: Mapped[str] = mapped_column(String(16), default="normal")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="f")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    runs: Mapped[list["ProjectRun"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ProjectRun.created_at",
    )
    memories: Mapped[list["MemoryEntry"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MemoryEntry.created_at",
    )

class ProjectRun(Base):
    __tablename__ = "project_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    pm_document: Mapped[str] = mapped_column(Text, default="", server_default="")
    code: Mapped[str] = mapped_column(Text, default="", server_default="")
    review: Mapped[str] = mapped_column(Text, default="", server_default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="f")
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        server_default="pending",
        comment="pending|running|converged|max_rounds_reached|error",
    )
    parent_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("project_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Edit-regenerate chain: the run whose answer this run replaces",
    )
    requirement_versions: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of prior user-message edits"
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

    session: Mapped["SessionDB | None"] = relationship(back_populates="runs")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_role: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="pm_document|code|review|decision",
    )
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    session: Mapped["SessionDB"] = relationship(back_populates="memories")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="pm|programmer|tester",
    )
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    thinking: Mapped[str | None] = mapped_column(Text, nullable=True)
    versions: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of prior answer versions"
    )
    thinking_versions: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of prior thinking versions"
    )
    sources: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of RAG citation sources"
    )
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    run: Mapped["ProjectRun"] = relationship(back_populates="messages")
