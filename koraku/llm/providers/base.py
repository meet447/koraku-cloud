"""Protocol for streaming backends that emit normalized events."""
from __future__ import annotations

from typing import Any, AsyncIterator, Protocol

from koraku.llm.canonical import CanonicalChatRequest


class LLMStreamingBackend(Protocol):
    async def stream(self, req: CanonicalChatRequest) -> AsyncIterator[dict[str, Any]]:
        """Yield normalized stream events ending with ``assistant_message``."""
