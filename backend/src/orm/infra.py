"""CommandLogDB, AuditLogDB, AttachmentDB, AssetDB ORM models."""


from datetime import UTC, datetime
from uuid import uuid4

from core.base import Base
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class CommandLogDB(Base):
    __tablename__ = "command_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    command_id: Mapped[str] = mapped_column(String(64), nullable=False)
    command_name: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

class AuditLogDB(Base):
    """Admin audit log — records management CRUD operations (no session FK)."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )

class AttachmentDB(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Null until bound to a run's session (pre-upload before first message)",
    )
    user_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True,
        comment="Uploader; ownership check for pre-session attachments",
    )
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class KnowledgeBaseDB(Base):
    """Knowledge base — logical grouping for assets (multi-KB isolation)."""

    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AssetDB(Base):
    """User-level asset library (distinct from session-scoped attachments)."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), default="document")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[str] = mapped_column(
        String(16), default="upload", comment="upload | url — B/C: sharepoint, s3, db, dir"
    )
    source_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="URL for source=url; connector-native ref for B/C sources"
    )
    knowledge_base_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True, comment="Optional KB grouping"
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class FeedbackLog(Base):
    """Answer-quality feedback — the online eval loop's intake channel."""

    __tablename__ = "feedback_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rating: Mapped[str] = mapped_column(String(8), nullable=False)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of RAG citation sources at rating time"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class FeedbackReviewDB(Base):
    """Human triage of a bad rating — feeds the golden-set eval pipeline.

    One review per feedback row (unique feedback_id). Status flow:
    pending → resolved | dismissed. ``root_cause`` is the enum that later
    becomes the eval-case category.
    """

    __tablename__ = "feedback_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    feedback_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("feedback_logs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    root_cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        default="pending",
        server_default="pending",
        comment="pending|resolved|dismissed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class RetrievalLogDB(Base):
    """Append-only retrieval activity log (OWASP LLM08 — forensics + quality).

    Written once per user question at the retrieval boundary; intentionally
    exposes no update/delete path (immutability for audit).
    """

    __tablename__ = "retrieval_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="project_runs.id — enables log-to-conversation replay",
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    rerank: Mapped[bool] = mapped_column(Boolean, default=False)
    min_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    sources: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of {asset_id, asset_name, similarity, text}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class ShadowRetrievalLogDB(Base):
    """O4: append-only shadow retrieval log (variant config comparison).

    Written once per user question when RAG_SHADOW_VARIANTS is set; mirrors
    retrieval_logs plus the variant label. Kept separate so shadow replays
    never pollute retrieval_logs / the online monitoring metrics.
    """

    __tablename__ = "shadow_retrieval_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    rerank: Mapped[bool] = mapped_column(Boolean, default=False)
    min_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    sources: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of {asset_id, asset_name, similarity, text}"
    )
    variant: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
