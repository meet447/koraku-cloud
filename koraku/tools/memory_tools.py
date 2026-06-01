"""Supermemory tools: explicit recall and save for the agent."""
from __future__ import annotations

from koraku.core.tenant import effective_tenant_org_id
from koraku.integrations.cloud_user import effective_auth_user_sub
from koraku.integrations.supermemory_client import save_memory_sync, search_memories_sync, supermemory_configured
from koraku.tools.tool_def import Tool


async def _memory_search(query: str, limit: int = 8) -> str:
    if not supermemory_configured():
        return "Error: Long-term memory is not configured on this server."
    try:
        uid = effective_auth_user_sub()
    except RuntimeError as e:
        return f"Error: {e}"
    return search_memories_sync(
        uid,
        query,
        org_id=effective_tenant_org_id(),
        limit=limit,
    )


async def _memory_save(content: str) -> str:
    if not supermemory_configured():
        return "Error: Long-term memory is not configured on this server."
    try:
        uid = effective_auth_user_sub()
    except RuntimeError as e:
        return f"Error: {e}"
    return save_memory_sync(uid, content, org_id=effective_tenant_org_id())


memory_search_tool = Tool(
    name="MemorySearch",
    description=(
        "Search the user's long-term learned memory (Supermemory) for facts, preferences, and past context. "
        "Use before answering when prior decisions, names, or preferences might matter."
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
        "Save a durable fact or preference to long-term memory (Supermemory). "
        "Use when the user asks to remember something, or for stable workflow rules — not one-off task noise."
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
