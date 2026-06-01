"""Parse inline / compact tool-call text emitted by OpenAI-compatible models."""
from __future__ import annotations

import json
import re
from typing import Any

_CALL_TOOL_HEAD = re.compile(
    r"\[Call\s+([A-Za-z][A-Za-z0-9_]*)\]\s*:\s*",
    re.IGNORECASE,
)
_ANGLE_TOOL_HEAD = re.compile(
    r"<tool_call>\s*\[([A-Za-z][A-Za-z0-9_]*)\]\s*",
    re.IGNORECASE,
)
_ANGLE_TOOL_CLOSE = re.compile(r"\s*</tool_call\s*>\s*", re.IGNORECASE)
_BRACKET_TOOL_OPEN = re.compile(r"\[TOOL_CALL\]\s*", re.IGNORECASE)
_BRACKET_TOOL_CLOSE = re.compile(r"\[/TOOL_CALL\]", re.IGNORECASE)
_COMPACT_TOOL_HEAD = re.compile(r"\{\s*\"tool\"\s*:", re.IGNORECASE)


def raw_decode_json(s: str) -> tuple[Any, int] | None:
    try:
        return json.JSONDecoder().raw_decode(s)
    except json.JSONDecodeError:
        return None


def strip_markdown_fences(text: str) -> str:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text


def normalize_ruby_style_tool_json(blob: str) -> str:
    t = blob.strip()
    t = re.sub(r"\[TOOL_CALL\]\s*", "", t, flags=re.IGNORECASE)
    t = re.split(r"\[/TOOL_CALL", t, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    t = re.sub(r"{\s*tool\s*=>", '{"tool":', t)
    t = re.sub(r",\s*parameters\s*=>", ', "parameters":', t)
    return t.strip()


def _tool_params_from_payload(data: dict[str, Any]) -> dict[str, Any]:
    params = data.get("parameters", data.get("input", data.get("args", {})))
    return params if isinstance(params, dict) else {}


def _append_tool_call(
    tool_calls: list[dict[str, Any]],
    *,
    start: int,
    end: int,
    tool_name: str,
    params: dict[str, Any],
) -> None:
    if not tool_name:
        return
    if any(t["start"] == start for t in tool_calls):
        return
    tool_calls.append({
        "start": start,
        "end": end,
        "data": {"tool": tool_name, "parameters": params},
    })


def _scan_bracket_tool_calls(clean_text: str, tool_calls: list[dict[str, Any]]) -> None:
    for m in re.finditer(
        r"\[TOOL_CALL\]\s*(\{[\s\S]*?\})\s*\[/TOOL_CALL\]",
        clean_text,
        re.IGNORECASE,
    ):
        normalized = normalize_ruby_style_tool_json(m.group(1))
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("tool"), str):
            _append_tool_call(
                tool_calls,
                start=m.start(),
                end=m.end(),
                tool_name=parsed["tool"],
                params=_tool_params_from_payload(parsed),
            )


def _scan_angle_tool_calls(clean_text: str, tool_calls: list[dict[str, Any]]) -> None:
    pos = 0
    while pos < len(clean_text):
        m = _ANGLE_TOOL_HEAD.search(clean_text, pos)
        if not m:
            break
        tool_name = m.group(1)
        rest = clean_text[m.end() :]
        leading = len(rest) - len(rest.lstrip())
        dec = raw_decode_json(rest.lstrip())
        if dec is None:
            pos = m.end()
            continue
        _, json_end = dec
        json_end += leading + len(rest) - len(rest.lstrip())
        tail = clean_text[m.end() + json_end :]
        close = _ANGLE_TOOL_CLOSE.match(tail)
        end = m.end() + json_end + (close.end() if close else 0)
        params = dec[0] if isinstance(dec[0], dict) else {}
        _append_tool_call(
            tool_calls,
            start=m.start(),
            end=end,
            tool_name=tool_name,
            params=params,
        )
        pos = end


def _scan_call_tool_markers(clean_text: str, tool_calls: list[dict[str, Any]]) -> None:
    pos = 0
    while pos < len(clean_text):
        m = _CALL_TOOL_HEAD.search(clean_text, pos)
        if not m:
            break
        tool_name = m.group(1)
        rest = clean_text[m.end() :]
        leading = len(rest) - len(rest.lstrip())
        dec = raw_decode_json(rest.lstrip())
        if dec is None:
            pos = m.end()
            continue
        params, json_len = dec
        if not isinstance(params, dict):
            pos = m.end()
            continue
        end = m.end() + leading + json_len
        _append_tool_call(
            tool_calls,
            start=m.start(),
            end=end,
            tool_name=tool_name,
            params=params,
        )
        pos = end


def _scan_compact_tool_json(clean_text: str, tool_calls: list[dict[str, Any]]) -> None:
    pos = 0
    while pos < len(clean_text):
        m = _COMPACT_TOOL_HEAD.search(clean_text, pos)
        if not m:
            break
        start = m.start()
        dec = raw_decode_json(clean_text[start:])
        if dec is None:
            pos = m.end()
            continue
        parsed, json_len = dec
        if isinstance(parsed, dict) and isinstance(parsed.get("tool"), str):
            inside = any(t["start"] <= start < t["end"] for t in tool_calls)
            if not inside:
                _append_tool_call(
                    tool_calls,
                    start=start,
                    end=start + json_len,
                    tool_name=parsed["tool"],
                    params=_tool_params_from_payload(parsed),
                )
        pos = start + max(json_len, 1)


def _scan_ruby_style_whole_blob(clean_text: str, tool_calls: list[dict[str, Any]]) -> None:
    if tool_calls or "tool" not in clean_text.lower() or "=>" not in clean_text:
        return
    normalized = normalize_ruby_style_tool_json(clean_text)
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        return
    if isinstance(parsed, dict) and isinstance(parsed.get("tool"), str):
        _append_tool_call(
            tool_calls,
            start=0,
            end=len(clean_text),
            tool_name=parsed["tool"],
            params=_tool_params_from_payload(parsed),
        )


def parse_tool_calls_from_text(text: str) -> list[dict[str, Any]]:
    """Extract tool calls from model text (compact / legacy inline formats)."""
    blocks: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []

    clean_text = strip_markdown_fences(text)
    _scan_bracket_tool_calls(clean_text, tool_calls)
    _scan_angle_tool_calls(clean_text, tool_calls)
    _scan_call_tool_markers(clean_text, tool_calls)
    _scan_compact_tool_json(clean_text, tool_calls)
    _scan_ruby_style_whole_blob(clean_text, tool_calls)

    if not tool_calls:
        if text.strip():
            blocks.append({"type": "text", "text": text})
        return blocks

    tool_calls.sort(key=lambda x: x["start"])
    last_end = 0
    for i, tc in enumerate(tool_calls):
        before = clean_text[last_end:tc["start"]]
        if before.strip():
            blocks.append({"type": "text", "text": before.strip()})
        params = _tool_params_from_payload(tc["data"])
        blocks.append({
            "type": "tool_use",
            "id": f"tool_{i}",
            "name": tc["data"]["tool"],
            "input": params,
        })
        last_end = tc["end"]

    after = clean_text[last_end:]
    if after.strip():
        blocks.append({"type": "text", "text": after.strip()})
    return blocks


def strip_inline_tool_call_text(text: str) -> str:
    """Remove parsed inline tool-call blobs, keeping any surrounding prose."""
    clean_text = strip_markdown_fences(text)
    tool_calls: list[dict[str, Any]] = []
    _scan_bracket_tool_calls(clean_text, tool_calls)
    _scan_angle_tool_calls(clean_text, tool_calls)
    _scan_call_tool_markers(clean_text, tool_calls)
    _scan_compact_tool_json(clean_text, tool_calls)
    if not tool_calls:
        return text.strip()
    tool_calls.sort(key=lambda x: x["start"])
    parts: list[str] = []
    last_end = 0
    for tc in tool_calls:
        before = clean_text[last_end:tc["start"]]
        if before.strip():
            parts.append(before.strip())
        last_end = tc["end"]
    after = clean_text[last_end:]
    if after.strip():
        parts.append(after.strip())
    return "\n\n".join(parts).strip()


__all__ = [
    "normalize_ruby_style_tool_json",
    "parse_tool_calls_from_text",
    "raw_decode_json",
    "strip_inline_tool_call_text",
    "strip_markdown_fences",
]
