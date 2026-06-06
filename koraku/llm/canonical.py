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
from koraku.llm.model_profiles import resolve_limits


def anthropic_tool_definitions(tool_schemas: list[Any]) -> list[dict[str, Any]]:
    """Anthropic Messages API requires JSON tool defs, not Python Tool objects."""
    out: list[dict[str, Any]] = []
    for t in tool_schemas or []:
        if hasattr(t, "to_anthropic_schema"):
            out.append(t.to_anthropic_schema())
        elif isinstance(t, dict) and "name" in t and "input_schema" in t:
            out.append(t)
    return out


def openai_tool_definitions(tool_schemas: list[Any]) -> list[dict[str, Any]]:
    """OpenAI Chat Completions ``tools`` array (function calling)."""
    out: list[dict[str, Any]] = []
    for t in tool_schemas or []:
        if hasattr(t, "to_openai_schema"):
            out.append(t.to_openai_schema())
        elif isinstance(t, dict) and "name" in t and "input_schema" in t:
            out.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t["input_schema"],
                },
            })
    return out


def build_compact_tool_prompt(tools: list[Any]) -> str:
    """Ultra-compact tool prompt for endpoints without native function calling."""
    lines = [
        "",
        "TOOLS: Emit exactly one JSON object per call (double quotes, colons — not Ruby ``=>``):",
        "{\"tool\":\"Name\",\"parameters\":{...}}",
        "Do not use [TOOL_CALL] tags, ``[Call ToolName]:`` prose, ``tool =>`` syntax, or XML tags.",
        "Never paste tool JSON inside your user-facing answer — only emit the JSON tool object.",
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


def _openai_native_tool_hint() -> str:
    return (
        "\n\nTools are bound via function calling. Invoke tools through the API tool channel only — "
        "never embed ``{\"tool\":...}``, ``[Call ToolName]:``, or similar JSON in plain assistant text."
    )


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
        else:
            parts.append({"type": "text", "text": json.dumps(block)})
    return parts


def _user_blocks_have_image(blocks: list[Any]) -> bool:
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "image":
            return True
    return False


def _assistant_openai_message(blocks: list[Any]) -> dict[str, Any]:
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            text_parts.append(str(block))
            continue
        t = block.get("type")
        if t == "text":
            text_parts.append(str(block.get("text", "")))
        elif t == "tool_use":
            tid = str(block.get("id") or f"tool_{len(tool_calls)}")
            tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
            tool_calls.append({
                "id": tid,
                "type": "function",
                "function": {
                    "name": str(block.get("name") or ""),
                    "arguments": json.dumps(tool_input, ensure_ascii=False),
                },
            })
        else:
            text_parts.append(json.dumps(block))

    content_text = "\n".join(part for part in text_parts if part).strip()
    msg: dict[str, Any] = {"role": "assistant"}
    if tool_calls:
        msg["tool_calls"] = tool_calls
        msg["content"] = content_text or None
    else:
        msg["content"] = content_text
    return msg


def _user_openai_messages(blocks: list[Any]) -> list[dict[str, Any]]:
    text_parts: list[str] = []
    tool_results: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            text_parts.append(str(block))
            continue
        t = block.get("type")
        if t == "tool_result":
            tool_results.append(block)
        elif t == "text":
            text_parts.append(str(block.get("text", "")))
        else:
            text_parts.append(json.dumps(block))

    out: list[dict[str, Any]] = []
    user_text = "\n".join(part for part in text_parts if part).strip()
    if user_text:
        out.append({"role": "user", "content": user_text})
    for tr in tool_results:
        out.append({
            "role": "tool",
            "tool_call_id": str(tr.get("tool_use_id") or ""),
            "content": str(tr.get("content") or ""),
        })
    return out


def openai_chat_messages_from_agent_messages(messages: list[AgentMessage]) -> list[dict[str, Any]]:
    """Map internal :class:`AgentMessage` list to OpenAI ``messages`` JSON objects."""
    openai_msgs: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg.content, str):
            openai_msgs.append({"role": msg.role, "content": msg.content})
            continue

        if msg.role == "user" and _user_blocks_have_image(msg.content):
            openai_msgs.append({
                "role": "user",
                "content": _openai_user_multimodal_parts(msg.content),
            })
            continue

        if msg.role == "assistant":
            openai_msgs.append(_assistant_openai_message(msg.content))
            continue

        if msg.role == "user":
            openai_msgs.extend(_user_openai_messages(msg.content))
            continue

        parts: list[str] = []
        for block in msg.content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(json.dumps(block) if isinstance(block, dict) else str(block))
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
        limits = resolve_limits(model_id)
        return cls(
            model_id=model_id,
            messages=list(messages),
            tool_schemas=list(tool_schemas or []),
            system_prompt=system_prompt,
            max_tokens=limits.max_output_tokens,
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

        native_tools = (
            openai_tool_definitions(self.tool_schemas)
            if settings.chat_openai_native_tools and self.tool_schemas
            else []
        )
        if native_tools:
            full_system = (self.system_prompt or "") + _openai_native_tool_hint()
        elif self.tool_schemas:
            tool_prompt = build_compact_tool_prompt(self.tool_schemas)
            full_system = (self.system_prompt or "") + tool_prompt
        else:
            full_system = self.system_prompt or ""

        openai_messages: list[dict[str, Any]] = []
        if full_system:
            openai_messages.append({"role": "system", "content": full_system})
        openai_messages.extend(openai_chat_messages_from_agent_messages(self.messages))

        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": openai_messages,
            "stream": True,
            "max_tokens": max_tok,
            "temperature": temp,
            "top_p": top_p,
            "top_k": top_k,
        }
        if native_tools:
            body["tools"] = native_tools
            body["tool_choice"] = "auto"
        return body


__all__ = [
    "CanonicalChatRequest",
    "anthropic_messages_from_agent_messages",
    "anthropic_tool_definitions",
    "build_compact_tool_prompt",
    "openai_chat_messages_from_agent_messages",
    "openai_tool_definitions",
]
