"""One-shot assistant text completion (non-streaming consumer)."""
from __future__ import annotations

from koraku.core.models import AgentMessage
from koraku.llm.client import UnifiedLLMClient


async def complete_assistant_text(
    *,
    system: str,
    user: str,
    model: str | None = None,
) -> str:
    client = UnifiedLLMClient()
    messages = [
        AgentMessage(role="user", content=[{"type": "text", "text": user}]),
    ]
    chunks: list[str] = []
    async for event in client.stream(
        messages,
        [],
        system_prompt=system,
        model=model,
    ):
        if event.get("type") != "content_block_delta":
            continue
        delta = event.get("delta") or {}
        if delta.get("type") == "text_delta":
            piece = delta.get("text")
            if isinstance(piece, str) and piece:
                chunks.append(piece)
    return "".join(chunks).strip()
