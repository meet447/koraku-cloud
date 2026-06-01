"""Normalize OpenAI-compatible streaming deltas (Fireworks, vLLM, local endpoints, …)."""
from __future__ import annotations

import json
from typing import Any


def _retryable_http_status(status_code: int) -> bool:
    return status_code in (408, 409, 425, 429, 500, 502, 503, 504)


def openai_delta_content_to_str(raw: Any) -> str:
    """Coerce ``choices[].delta.content`` to plain text (OpenAI string or list-of-parts shapes)."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for p in raw:
            if isinstance(p, dict):
                if p.get("type") == "text" and isinstance(p.get("text"), str):
                    parts.append(p["text"])
                elif isinstance(p.get("content"), str):
                    parts.append(p["content"])
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return str(raw)


def _accumulate_openai_tool_call_deltas(
    slots: dict[int, dict[str, str]],
    tool_calls_delta: list[Any],
) -> None:
    """Merge streaming ``choices[].delta.tool_calls`` fragments (OpenAI / Fireworks / Kimi)."""
    for tc in tool_calls_delta:
        if not isinstance(tc, dict):
            continue
        idx = int(tc.get("index", 0))
        slot = slots.setdefault(idx, {"id": "", "name": "", "arguments": ""})
        tid = tc.get("id")
        if tid:
            slot["id"] = str(tid)
        fn = tc.get("function")
        if isinstance(fn, dict):
            if fn.get("name"):
                slot["name"] = str(fn["name"])
            arg = fn.get("arguments")
            if arg is not None and arg != "":
                slot["arguments"] += str(arg)


def _tool_call_slots_to_blocks(slots: dict[int, dict[str, str]]) -> list[dict[str, Any]]:
    """Turn accumulated native tool-call slots into Anthropic-style ``tool_use`` blocks."""
    blocks: list[dict[str, Any]] = []
    for idx in sorted(slots.keys()):
        slot = slots[idx]
        name = (slot.get("name") or "").strip()
        raw_args = slot.get("arguments") or ""
        tid = (slot.get("id") or "").strip() or f"tool_{idx}"
        if not name:
            continue
        try:
            inp = json.loads(raw_args) if raw_args.strip() else {}
        except json.JSONDecodeError:
            inp = {"_partial_json": raw_args}
        if not isinstance(inp, dict):
            inp = {"_value": inp}
        blocks.append({"type": "tool_use", "id": tid, "name": name, "input": inp})
    return blocks


__all__ = [
    "_retryable_http_status",
    "openai_delta_content_to_str",
    "_accumulate_openai_tool_call_deltas",
    "_tool_call_slots_to_blocks",
]
