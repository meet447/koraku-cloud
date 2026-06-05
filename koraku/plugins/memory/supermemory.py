"""Supermemory learned-memory plugin (optional API key)."""
from __future__ import annotations

import asyncio
import logging

from koraku.core.config import settings
from koraku.core.tenant import effective_tenant_org_id
from koraku.integrations.cloud_user import effective_auth_user_sub
from koraku.integrations.supermemory_client import (
    fetch_learned_context_sync,
    save_memory_sync,
    search_memories_sync,
    supermemory_configured,
)
from koraku.tools.tool_def import Tool

log = logging.getLogger(__name__)


class SupermemoryBackend:
    name = "supermemory"

    def supports_agent_tools(self) -> bool:
        return supermemory_configured()

    def agent_tools(self) -> list[Tool]:
        if not self.supports_agent_tools():
            return []
        return [memory_search_tool, memory_save_tool]

    async def prefetch_learned(self, user_input: str, *, workspace: str) -> str:
        if not bool(settings.chat_prefetch_learned_memory) or not supermemory_configured():
            return ""
        q = (user_input or "").strip()
        if not q:
            return ""
        try:
            uid = effective_auth_user_sub()
        except RuntimeError:
            return ""
        timeout = max(0.5, float(settings.chat_learned_memory_timeout_seconds))
        try:
            block = await asyncio.wait_for(
                asyncio.to_thread(
                    fetch_learned_context_sync,
                    uid,
                    org_id=effective_tenant_org_id(),
                    query=q[:800],
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            log.info("supermemory prefetch timed out after %.1fs", timeout)
            return ""
        except Exception as e:
            log.warning("supermemory prefetch failed: %s", e)
            return ""
        if not (block or "").strip():
            return ""
        return f"## Learned memory (Supermemory)\n{block.strip()}\n"


async def _memory_search(query: str, limit: int = 8) -> str:
    if not supermemory_configured():
        return "Error: Supermemory is not configured (set SUPERMEMORY_API_KEY)."
    try:
        uid = effective_auth_user_sub()
    except RuntimeError as e:
        return f"Error: {e}"
    return await asyncio.to_thread(
        search_memories_sync,
        uid,
        query,
        org_id=effective_tenant_org_id(),
        limit=limit,
    )


async def _memory_save(content: str) -> str:
    if not supermemory_configured():
        return "Error: Supermemory is not configured (set SUPERMEMORY_API_KEY)."
    try:
        uid = effective_auth_user_sub()
    except RuntimeError as e:
        return f"Error: {e}"
    return await asyncio.to_thread(
        save_memory_sync,
        uid,
        content,
        org_id=effective_tenant_org_id(),
    )


memory_search_tool = Tool(
    name="MemorySearch",
    description=(
        "Search the user's long-term learned memory (Supermemory) for facts, preferences, and past context. "
        "Required before any statement about the user's preferences, contacts, schedule, or history."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "limit": {"type": "integer", "description": "Max results (1-20)", "default": 8},
        },
        "required": ["query"],
    },
    handler=_memory_search,
    categories=["memory"],
)

memory_save_tool = Tool(
    name="MemorySave",
    description=(
        "Save a durable fact to long-term memory (Supermemory). "
        "Use when the user asks to remember something, or for stable workflow rules."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Concise fact or preference to remember"},
        },
        "required": ["content"],
    },
    handler=_memory_save,
    categories=["memory"],
)
