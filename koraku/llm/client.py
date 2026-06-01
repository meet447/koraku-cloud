"""Unified LLM client: pick a streaming backend and normalize request/response.

Providers:
- anthropic: native Messages API + tools (:class:`AnthropicMessagesBackend`)
- fireworks: Fireworks OpenAI-compatible API
- named OpenAI-compatible providers from ``LLM_OPENAI_COMPAT_IDS`` / ``LLM_OPENAI_COMPAT_JSON``

All paths use :class:`koraku.llm.canonical.CanonicalChatRequest` for the outbound request and emit
the same normalized stream event shapes (see ``koraku.llm.canonical`` module docstring).
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from koraku.core.config import settings
from koraku.core.models import AgentMessage
from koraku.llm.canonical import CanonicalChatRequest, build_compact_tool_prompt
from koraku.llm.openai_compat_registry import get_openai_compat_provider
from koraku.llm.providers.anthropic_backend import AnthropicMessagesBackend
from koraku.llm.providers.openai_compat_backend import OpenAICompatBackend


class UnifiedLLMClient:
    """Routes to Anthropic or OpenAI-compatible backends via a shared canonical request."""

    def __init__(self, provider_override: str | None = None) -> None:
        self.provider = (provider_override or settings.llm_provider or "fireworks").strip().lower()
        if self.provider == "anthropic":
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.model = settings.anthropic_model
            self._backend = AnthropicMessagesBackend(self._client)
        elif self.provider == "fireworks":
            self.model = settings.fireworks_model
            self._backend = OpenAICompatBackend(
                base_url=settings.fireworks_base_url,
                api_key=settings.fireworks_api_key,
                timeout=120.0,
            )
        else:
            compat = get_openai_compat_provider(self.provider)
            if not compat:
                raise ValueError(f"Unknown provider: {self.provider}")
            self.model = compat.default_model
            self._backend = OpenAICompatBackend(
                base_url=compat.base_url,
                api_key=compat.api_key,
                timeout=120.0,
            )

    def build_compact_tool_prompt(self, tools: list[Any]) -> str:
        """Ultra-compact tool prompt for small models (delegates to canonical builder)."""
        return build_compact_tool_prompt(tools)

    async def stream(
        self,
        messages: list[AgentMessage],
        tool_schemas: list[Any],
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        model_id = (model or "").strip() or self.model
        req = CanonicalChatRequest.for_turn(
            model_id=model_id,
            messages=messages,
            tool_schemas=tool_schemas,
            system_prompt=system_prompt,
        )
        async for ev in self._backend.stream(req):
            yield ev
