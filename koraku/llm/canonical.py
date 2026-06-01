"""
Provider-agnostic LLM chat request and outbound message normalization.

All streaming backends yield the same **normalized stream vocabulary** (Anthropic-shaped
deltas: ``message_start``, ``content_block_*``, ``message_delta``, ``message_stop``,
``assistant_message``) so the agent loop stays provider-blind.

Inbound: :class:`CanonicalChatRequest` (messages + tools + sampling + system).
Outbound: dict events as produced by ``AnthropicMessagesBackend`` /
``OpenAICompatBackend`` (documented on :class:`CanonicalChatRequest`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from koraku.core.config import settings
from koraku.core.models import AgentMessage


def anthropic_tool_definitions(tool_schemas: list[Any]) -> list[dict[str, Any]]:
    """Anthropic Messages API requires JSON tool defs, not Python Tool objects."""
    out: list[dict[str, Any]] = []
    for t in tool_schemas or []:
        if hasattr(t, "to_anthropic_schema"):
            out.append(t.to_anthropic_schema())
        elif isinstance(t, dict) and "name" in t and "input_schema" in t:
            out.append(t)
    return out


def build_compact_tool_prompt(tools: list[Any]) -> str:
    """Ultra-compact tool prompt for small / non-native-tool models."""
    lines = [
        "",
        "TOOLS: Emit exactly one JSON object per call (double quotes, colons — not Ruby ``=>``):",
        "{\"tool\":\"Name\",\"parameters\":{...}}",
        "Do not use [TOOL_CALL] tags or ``tool =>`` syntax.",
        "",
    ]
    for tool in tools:
        if hasattr(tool, "to_compact_prompt"):
            lines.append(tool.to_compact_prompt())
        else:
            name = tool.get("name", "Unknown")
            desc = tool.get("description", "")
            lines.append(f"{name}: {desc}")
        lines.append("")
    lines.append("Call tools when needed. Provide final answer when done.")
    return "\n".join(lines)


def _openai_user_multimodal_parts(blocks: list[Any]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            parts.append({"type": "text", "text": str(block)})
            continue
        t = block.get("type")
        if t == "image":
            src = block.get("source") or {}
            if src.get("type") == "base64" and src.get("data"):
                mt = str(src.get("media_type") or "image/png")
                b64 = str(src.get("data", ""))
                parts.append({"type": "image_url", "image_url": {"url": f"data:{mt};base64,{b64}"}})
        elif t == "text":
            parts.append({"type": "text", "text": str(block.get("text", ""))})
        elif t == "tool_result":
            tid = block.get("tool_use_id", "?")
            content = block.get("content", "")
            parts.append({"type": "text", "text": f"[Result {tid}]:\n{content}"})
        elif t == "tool_use":
            parts.append({
                "type": "text",
                "text": f"[Call {block.get('name', '?')}]:\n{json.dumps(block.get('input', {}))}",
            })
        else:
            parts.append({"type": "text", "text": json.dumps(block)})
    return parts


def _user_blocks_have_image(blocks: list[Any]) -> bool:
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "image":
            return True
    return False


def openai_chat_messages_from_agent_messages(messages: list[AgentMessage]) -> list[dict[str, Any]]:
    """Map internal :class:`AgentMessage` list to OpenAI ``messages`` JSON objects."""
    openai_msgs: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg.content, str):
            openai_msgs.append({"role": msg.role, "content": msg.content})
        elif msg.role == "user" and _user_blocks_have_image(msg.content):
            openai_msgs.append({
                "role": "user",
                "content": _openai_user_multimodal_parts(msg.content),
            })
        else:
            parts: list[str] = []
            for block in msg.content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        parts.append(f"[Result {block.get('tool_use_id', '?')}]:\n{block.get('content', '')}")
                    elif block.get("type") == "tool_use":
                        parts.append(f"[Call {block.get('name', '?')}]:\n{json.dumps(block.get('input', {}))}")
                    elif block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    else:
                        parts.append(json.dumps(block))
                else:
                    parts.append(str(block))
            openai_msgs.append({"role": msg.role, "content": "\n".join(parts)})
    return openai_msgs


def anthropic_messages_from_agent_messages(messages: list[AgentMessage]) -> list[dict[str, Any]]:
    """Map internal messages to Anthropic Messages API ``messages`` list."""
    return [{"role": msg.role, "content": msg.content} for msg in messages]


@dataclass(frozen=True)
class CanonicalChatRequest:
    """Normalized chat completion request (all providers consume this shape)."""

    model_id: str
    messages: list[AgentMessage]
    tool_schemas: list[Any]
    system_prompt: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None

    @classmethod
    def for_turn(
        cls,
        *,
        model_id: str,
        messages: list[AgentMessage],
        tool_schemas: list[Any],
        system_prompt: str | None,
    ) -> CanonicalChatRequest:
        return cls(
            model_id=model_id,
            messages=list(messages),
            tool_schemas=list(tool_schemas or []),
            system_prompt=system_prompt,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            top_p=settings.top_p,
            top_k=settings.top_k,
        )

    def anthropic_stream_kwargs(self) -> dict[str, Any]:
        """Normalized → Anthropic Messages API ``messages.stream`` keyword arguments."""
        max_tok = self.max_tokens if self.max_tokens is not None else settings.max_tokens
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": max_tok,
            "messages": anthropic_messages_from_agent_messages(self.messages),
            "stream": True,
        }
        tools = anthropic_tool_definitions(self.tool_schemas)
        if tools:
            kwargs["tools"] = tools
        if self.system_prompt:
            kwargs["system"] = self.system_prompt
        return kwargs

    def openai_chat_completions_body(self) -> dict[str, Any]:
        """Normalized → OpenAI-compatible ``POST .../chat/completions`` JSON body."""
        max_tok = self.max_tokens if self.max_tokens is not None else settings.max_tokens
        temp = self.temperature if self.temperature is not None else settings.temperature
        top_p = self.top_p if self.top_p is not None else settings.top_p
        top_k = self.top_k if self.top_k is not None else settings.top_k

        if self.tool_schemas:
            tool_prompt = build_compact_tool_prompt(self.tool_schemas)
            full_system = (self.system_prompt or "") + tool_prompt
        else:
            full_system = self.system_prompt or ""

        openai_messages: list[dict[str, Any]] = []
        if full_system:
            openai_messages.append({"role": "system", "content": full_system})
        openai_messages.extend(openai_chat_messages_from_agent_messages(self.messages))

        return {
            "model": self.model_id,
            "messages": openai_messages,
            "stream": True,
            "max_tokens": max_tok,
            "temperature": temp,
            "top_p": top_p,
            "top_k": top_k,
        }


__all__ = [
    "CanonicalChatRequest",
    "anthropic_messages_from_agent_messages",
    "anthropic_tool_definitions",
    "build_compact_tool_prompt",
    "openai_chat_messages_from_agent_messages",
]
