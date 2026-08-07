"""Pydantic data models shared across the application."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Role(StrEnum):
    """Agent roles for team-based conversations."""

    PM = "pm"
    PROGRAMMER = "programmer"
    TESTER = "tester"

    @property
    def display_name(self) -> str:
        """Chinese display name for the role."""
        mapping = {
            Role.PM: "产品经理",
            Role.PROGRAMMER: "资深程序员",
            Role.TESTER: "测试工程师",
        }
        return mapping[self]


class AgentConfig(BaseModel):
    """Agent configuration — name, model, temperature, prompts."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=64)
    role_identifier: str = Field(..., min_length=1, max_length=32, pattern=r"^[a-z_]+$")
    system_prompt: str = Field(..., min_length=1)
    model: str | None = Field(default=None)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    is_approver: bool = Field(default=False)
    icon: str = Field(default="🤖", max_length=8)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Message(BaseModel):
    """A chat message with role, content, and optional thinking."""

    role: str  # Now a string (role_identifier), not enum
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    round_number: int = Field(default=1, ge=1)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        """Validate that content is not empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("content must not be empty")
        return stripped


class ConversationStatus(StrEnum):
    """Possible states for a team conversation."""

    IN_PROGRESS = "in_progress"
    CONVERGED = "converged"
    MAX_ROUNDS_REACHED = "max_rounds_reached"
    ERROR = "error"


class ConversationRound(BaseModel):
    """A single round in a team conversation with its messages."""

    round_number: int = Field(ge=1)
    messages: list[Message] = Field(min_length=1)


class MemoryEntryItem(BaseModel):
    """A memory entry stored for session context retrieval."""

    id: str
    agent_role: str
    content_type: str = Field(..., pattern=r"^(pm_document|code|review|decision)$")
    summary: str
    details: str
    created_at: datetime


class SessionItem(BaseModel):
    """Summary view of a session (list view)."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionItem):
    """Detailed session view including runs."""

    runs: list[Any] = Field(default_factory=list)


class AttachmentResponse(BaseModel):
    """Attachment metadata returned from the API."""

    id: str
    session_id: str
    run_id: str | None = None
    filename: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    has_extracted_text: bool = False
    created_at: datetime | None = None


class CommandResponse(BaseModel):
    """Registered command definition returned to the frontend."""

    id: str
    name: str
    description: str
    shortcut: str | None = None
    category: str = "general"
    requires_input: bool = False
    enabled: bool = True


class CommandExecuteRequest(BaseModel):
    """Request to execute a registered command."""

    command_id: str
    session_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class CommandExecuteResponse(BaseModel):
    """Response from executing a command."""

    success: bool
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class SessionSummary(BaseModel):
    """Lightweight session summary for list views."""

    id: str
    title: str
    kind: str = "normal"
    run_count: int = 0
    is_pinned: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class RunSummary(BaseModel):
    """Lightweight run summary for session detail views."""

    id: str
    session_id: str | None = None
    requirement: str
    pm_document: str = ""
    code: str = ""
    review: str = ""
    approved: bool = False
    status: str = "pending"
    parent_run_id: str | None = None
    requirement_versions: list[str] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    messages: list["MessageItem"] = Field(default_factory=list)


class MessageItem(BaseModel):
    """A chat message item returned from the API."""

    id: str
    role: str
    agent_name: str
    content: str
    thinking: str | None = None
    round_number: int = 1
    created_at: str | None = None


class RunDetail(RunSummary):
    """Detailed run view including messages."""

    messages: list[MessageItem] = Field(default_factory=list)


class MemoryItem(BaseModel):
    """A memory entry returned from the API."""

    id: str
    agent_role: str
    content_type: str
    summary: str
    details: str = ""
    created_at: str | None = None


class SessionDetailResponse(BaseModel):
    """Full session detail response including runs and memories."""

    id: str
    title: str
    kind: str = "normal"
    created_at: str | None = None
    updated_at: str | None = None
    runs: list[RunSummary] = Field(default_factory=list)
    memories: list[MemoryItem] = Field(default_factory=list)
