"""Estimate LLM tokens when providers omit usage in stream events."""
from __future__ import annotations

import json
from typing import Any

from koraku.core.models import AgentMessage
from koraku.llm.canonical import anthropic_tool_definitions, build_compact_tool_prompt

# Per-message framing overhead (role markers, JSON wrappers).
_MESSAGE_OVERHEAD_TOKENS = 4
# Tool schema + system prompt wrapper fudge.
_REQUEST_WRAPPER_TOKENS = 32


def _encoding_for_model(model: str | None):
    try:
        import tiktoken
    except ImportError:
        return None
    name = (model or "").strip().lower()
    try:
        if name:
            return tiktoken.encoding_for_model(name)
    except Exception:
        pass
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def count_text(text: str, *, model: str | None = None) -> int:
    """Count tokens in a string (tiktoken when installed, else chars/4)."""
    raw = text or ""
    if not raw:
        return 0
    enc = _encoding_for_model(model)
    if enc is not None:
        return len(enc.encode(raw))
    return max(1, (len(raw) + 3) // 4)


def _serialize_message_content(content: str | list[dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(content)


def estimate_messages_tokens(
    messages: list[AgentMessage],
    *,
    system_prompt: str | None = None,
    tool_schemas: list[Any] | None = None,
    model: str | None = None,
    native_tools: bool = True,
) -> int:
    """Estimate input-side tokens for one LLM request."""
    total = _REQUEST_WRAPPER_TOKENS
    if system_prompt and system_prompt.strip():
        total += count_text(system_prompt.strip(), model=model)
    tools = tool_schemas or []
    if tools:
        if native_tools:
            try:
                total += count_text(
                    json.dumps(anthropic_tool_definitions(tools), ensure_ascii=False),
                    model=model,
                )
            except (TypeError, ValueError):
                total += count_text(str(tools), model=model)
        else:
            total += count_text(build_compact_tool_prompt(tools), model=model)
    for msg in messages:
        total += _MESSAGE_OVERHEAD_TOKENS
        total += count_text(_serialize_message_content(msg.content), model=model)
    return total


def estimate_assistant_output_tokens(
    content: list[dict[str, Any]] | str,
    *,
    model: str | None = None,
) -> int:
    """Estimate completion tokens from assistant blocks."""
    if isinstance(content, str):
        return count_text(content, model=model)
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            parts.append(str(block.get("text") or ""))
        elif kind == "thinking":
            parts.append(str(block.get("thinking") or ""))
        elif kind == "tool_use":
            try:
                parts.append(
                    json.dumps(
                        {"name": block.get("name"), "input": block.get("input")},
                        ensure_ascii=False,
                        default=str,
                    ),
                )
            except (TypeError, ValueError):
                parts.append(str(block.get("name") or ""))
    return count_text("\n".join(parts), model=model)


def normalize_provider_usage(raw: dict[str, Any] | None) -> dict[str, int]:
    """Map OpenAI/Anthropic usage dicts to a common shape."""
    if not raw or not isinstance(raw, dict):
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
    inp = int(raw.get("input_tokens") or raw.get("prompt_tokens") or 0)
    out = int(raw.get("output_tokens") or raw.get("completion_tokens") or 0)
    cache_read = int(raw.get("cache_read_input_tokens") or 0)
    cache_create = int(raw.get("cache_creation_input_tokens") or 0)
    return {
        "input_tokens": max(0, inp),
        "output_tokens": max(0, out),
        "cache_creation_input_tokens": max(0, cache_create),
        "cache_read_input_tokens": max(0, cache_read),
    }


def native_tools_for_provider(provider: str, tool_schemas: list[Any] | None) -> bool:
    """Whether the active provider sends tools in API-native form (for input estimates)."""
    tools = tool_schemas or []
    if not tools:
        return False
    if (provider or "").strip().lower() == "anthropic":
        return True
    from koraku.core.config import settings

    return bool(settings.chat_openai_native_tools)


def estimate_llm_round(
    *,
    messages: list[AgentMessage],
    system_prompt: str | None,
    tool_schemas: list[Any] | None,
    assistant_content: list[dict[str, Any]] | str,
    model: str | None,
    native_tools: bool = True,
) -> tuple[int, int]:
    """Return (estimated_input_tokens, estimated_output_tokens) for one model call."""
    est_in = estimate_messages_tokens(
        messages,
        system_prompt=system_prompt,
        tool_schemas=tool_schemas,
        model=model,
        native_tools=native_tools,
    )
    est_out = estimate_assistant_output_tokens(assistant_content, model=model)
    return est_in, est_out
