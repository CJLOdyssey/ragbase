"""Checkpoint data models — ORM entity and in-memory dataclass."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from core.base import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class CheckpointDB(Base):
    """ORM model for persisting agent checkpoint state."""

    __tablename__ = "agent_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("project_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    agent_state: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-serialized state
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


@dataclass
class AgentCheckpoint:
    """In-memory representation of a saved agent state."""

    session_id: str
    run_id: str | None
    step_index: int
    system_prompt: str = ""
    user_input: str = ""
    messages: list[dict[str, object]] = field(default_factory=list)
    react_steps: list[dict[str, object]] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize the checkpoint to a JSON string."""
        return json.dumps(
            {
                "session_id": self.session_id,
                "run_id": self.run_id,
                "step_index": self.step_index,
                "system_prompt": self.system_prompt,
                "user_input": self.user_input,
                "messages": self.messages,
                "react_steps": self.react_steps,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, data: str) -> "AgentCheckpoint":
        """Deserialize a JSON string back into an AgentCheckpoint."""
        obj = json.loads(data)
        return cls(**obj)
