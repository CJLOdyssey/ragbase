"""UserApiKey, KeyUsageLog ORM models."""


from datetime import UTC, datetime
from uuid import uuid4

from core.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class UserApiKey(Base):
    """Enterprise API key vault — encrypted at rest, never returned to client."""

    __tablename__ = "user_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="openai|deepseek|anthropic|custom"
    )
    capabilities: Mapped[list[str]] = mapped_column(
        "capabilities",
        JSONB().with_variant(JSON, "sqlite"),
        default=list,
        nullable=False,
        comment="llm|embedding|rerank|speech2text|tts|moderation|tool — what this key can do",
    )
    model_types: Mapped[dict[str, str] | None] = mapped_column(
        "model_types",
        JSONB().with_variant(JSON, "sqlite"),
        default=None,
        nullable=True,
        comment="per-model capability map (model -> llm|embedding|...); None = name heuristic",
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    models: Mapped[str] = mapped_column(Text, default="", comment="Comma-separated model IDs")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

class KeyUsageLog(Base):
    """Audit log: records every LLM call with token consumption."""

    __tablename__ = "key_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    key_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="success", comment="success|error")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
