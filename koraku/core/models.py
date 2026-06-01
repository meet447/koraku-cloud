"""Pydantic models for SSE events and agent messages."""
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Timezone-aware UTC (avoid naive ``datetime.utcnow()``)."""
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Normalize datetimes from storage for comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StreamEvent(BaseModel):
    """A raw streaming event from the LLM."""
    type: Literal[
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    event: dict[str, Any] = Field(default_factory=dict)


class AgentEvent(BaseModel):
    """Top-level wrapper for all events sent over SSE."""
    type: Literal[
        "agent.started",
        "agent.event",
        "agent.error",
        "agent.completed",
    ]
    data: dict[str, Any] = Field(default_factory=dict)


class ToolUse(BaseModel):
    """A tool invocation."""
    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result from executing a tool."""
    tool_use_id: str
    content: str
    is_error: bool = False


class AgentMessage(BaseModel):
    """A message in the agent conversation."""
    role: Literal["user", "assistant"]
    content: str | list[dict[str, Any]]
    model: Optional[str] = None
    usage: Optional[dict[str, int]] = None
    stop_reason: Optional[str] = None


class SessionState(BaseModel):
    """Per-session state."""
    session_id: str
    owner_sub: Optional[str] = None
    owner_org_id: Optional[str] = None
    messages: list[AgentMessage] = Field(default_factory=list)
    todos: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    step_count: int = 0

    def touch(self) -> None:
        self.updated_at = utcnow()

    def add_message(self, role: str, content: Any, **kwargs) -> None:
        self.messages.append(AgentMessage(role=role, content=content, **kwargs))
        self.touch()
