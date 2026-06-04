"""Memory backend protocol."""
from __future__ import annotations

from typing import Protocol

from koraku.tools.tool_def import Tool


class MemoryBackend(Protocol):
    """Explicit preferences (Memory.md) + optional learned memory."""

    @property
    def name(self) -> str: ...

    def supports_agent_tools(self) -> bool:
        """When True, register MemorySearch / MemorySave style tools."""
        ...

    def agent_tools(self) -> list[Tool]:
        ...

    async def prefetch_learned(self, user_input: str, *, workspace: str) -> str:
        """Volatile-tier context injected before the agent loop."""
        ...
