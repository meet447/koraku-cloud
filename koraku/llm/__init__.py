"""LLM client, model catalog, and stream parsing helpers."""
from __future__ import annotations

from koraku.llm.canonical import CanonicalChatRequest
from koraku.llm.catalog import any_llm_configured, configured_provider_ids, default_chat_model
from koraku.llm.client import UnifiedLLMClient
from koraku.llm.openai_delta import _accumulate_openai_tool_call_deltas, _tool_call_slots_to_blocks

__all__ = [
    "CanonicalChatRequest",
    "UnifiedLLMClient",
    "_accumulate_openai_tool_call_deltas",
    "_tool_call_slots_to_blocks",
    "any_llm_configured",
    "configured_provider_ids",
    "default_chat_model",
]
