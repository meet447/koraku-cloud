"""Shared chat history types and client-side hydration helpers (SDK + Cloud)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from koraku.core.models import AgentMessage


@dataclass(frozen=True)
class ChatHistoryHydration:
    session_id: str
    source: str
    reason: str
    auth_present: bool
    supabase_configured: bool
    rows_fetched: int
    messages_loaded: int
    messages_before: int

    def to_trace_data(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source": self.source,
            "reason": self.reason,
            "auth_present": self.auth_present,
            "supabase_configured": self.supabase_configured,
            "rows_fetched": self.rows_fetched,
            "messages_loaded": self.messages_loaded,
            "messages_before": self.messages_before,
        }


def client_history_rows_to_agent_messages(rows: list[dict[str, Any]]) -> list[AgentMessage]:
    """Map browser-visible chat history to LLM messages (no DB)."""
    out: list[AgentMessage] = []
    for row in rows:
        role = str(row.get("role") or "").strip()
        text = str(row.get("text") or "").strip()
        if role not in {"user", "assistant"} or not text:
            continue
        out.append(AgentMessage(role=role, content=[{"type": "text", "text": text}]))
    return out
