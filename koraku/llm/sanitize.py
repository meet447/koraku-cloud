"""Strip inline tool-call JSON from streamed assistant *visible* text.

OpenAI-compatible models often emit ``{"tool":"…","parameters":{…}}`` or
``[Call WebFetch]: {"url":…}`` in the same channel as the user-facing answer.
Some models also emit legacy ``[TOOL_CALL] … [/TOOL_CALL]`` spans (empty or
with JSON), which must not reach the user. Raw chunks are still accumulated
separately for ``_parse_tool_calls`` at EOF.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional

_CALL_TOOL_HEAD = re.compile(
    r"^\s*\[Call\s+([A-Za-z][A-Za-z0-9_]*)\]\s*:\s*",
    re.IGNORECASE,
)
_ANGLE_TOOL_HEAD = re.compile(
    r"^\s*<tool_call>\s*\[([A-Za-z][A-Za-z0-9_]*)\]\s*",
    re.IGNORECASE,
)
_TOOL_JSON_HEAD = re.compile(r"^\s*\{\s*\"tool\"\s*:", re.IGNORECASE)
_ANGLE_TOOL_CLOSE = re.compile(r"\s*</tool_call\s*>\s*", re.IGNORECASE)
_BRACKET_TOOL_HEAD = re.compile(r"^\s*\[TOOL_CALL\]\s*", re.IGNORECASE)
_BRACKET_TOOL_CLOSE_HEAD = re.compile(r"^\s*\[/TOOL_CALL\]\s*", re.IGNORECASE)


def _eat_leading_newlines_only(s: str) -> str:
    """Do not strip spaces/tabs — only CR/LF (see lstrip() bug after tool JSON)."""
    i = 0
    while i < len(s) and s[i] in "\n\r":
        i += 1
    return s[i:]


def _first_tool_marker(s: str) -> re.Match[str] | None:
    json_marker = re.search(r"\{\s*\"tool\"\s*:", s)
    angle_marker = re.search(r"<tool_call>\s*\[[A-Za-z][A-Za-z0-9_]*\]\s*", s, re.IGNORECASE)
    call_marker = re.search(r"\[Call\s+[A-Za-z][A-Za-z0-9_]*\]\s*:\s*", s, re.IGNORECASE)
    bracket_marker = re.search(r"\[\s*TOOL_CALL\]\s*", s, re.IGNORECASE)
    markers = [m for m in (json_marker, angle_marker, call_marker, bracket_marker) if m is not None]
    if not markers:
        return None
    return min(markers, key=lambda m: m.start())


def _split_partial_json_tool_marker(s: str) -> tuple[str, str] | None:
    """If ``s`` ends with a partial ``{\"tool\":`` marker, split emit/hold text."""
    lower = s.lower()
    start = lower.rfind("{")
    if start == -1:
        return None
    tail = s[start:]
    compact = re.sub(r"\s+", "", tail.lower())
    marker = '{"tool":'
    if len(compact) >= 2 and marker.startswith(compact):
        return s[:start], tail
    return None


def _split_partial_call_tool_marker(s: str) -> tuple[str, str] | None:
    """If ``s`` ends with a partial ``[Call Tool]:`` marker, split emit/hold text."""
    needle = "[call "
    lower = s.lower()
    max_check = min(len(lower), len(needle) - 1)
    for n in range(max_check, 0, -1):
        if needle.startswith(lower[-n:]):
            return s[:-n], s[-n:]
    start = lower.rfind("[call")
    if start == -1:
        return None
    tail = s[start:]
    if _CALL_TOOL_HEAD.match(tail):
        return None
    if re.fullmatch(r"\[Call\s*(?:[A-Za-z][A-Za-z0-9_]*\]?)?", tail, re.IGNORECASE):
        return s[:start], tail
    return None


def _split_partial_bracket_tool_marker(s: str) -> tuple[str, str] | None:
    """Hold text when the buffer ends with an incomplete ``[TOOL_CALL]`` span."""
    needle = "[tool_call]"
    lower = s.lower()
    max_check = min(len(lower), len(needle) - 1)
    for n in range(max_check, 0, -1):
        if needle.startswith(lower[-n:]):
            return s[:-n], s[-n:]
    start = lower.rfind("[tool_call]")
    if start == -1:
        return None
    tail = s[start:]
    open_m = _BRACKET_TOOL_HEAD.match(tail)
    if not open_m:
        return None
    rest = tail[open_m.end() :]
    if "[/tool_call]" in rest.lower():
        return None
    return s[:start], tail


def _split_partial_tool_marker(s: str) -> tuple[str, str] | None:
    return (
        _split_partial_json_tool_marker(s)
        or _split_partial_call_tool_marker(s)
        or _split_partial_angle_tool_marker(s)
        or _split_partial_bracket_tool_marker(s)
    )


def _split_partial_angle_tool_marker(s: str) -> tuple[str, str] | None:
    """If ``s`` ends with a partial ``<tool_call>`` marker, split emit/hold text."""
    needle = "<tool_call>"
    lower = s.lower()
    max_check = min(len(lower), len(needle) - 1)
    for n in range(max_check, 0, -1):
        if needle.startswith(lower[-n:]):
            return s[:-n], s[-n:]
    start = lower.rfind("<tool_call>")
    if start == -1:
        return None
    tail = s[start:]
    if _ANGLE_TOOL_HEAD.match(tail):
        return None
    if re.fullmatch(r"<tool_call>\s*(?:\[[A-Za-z][A-Za-z0-9_]*\]?)?", tail, re.IGNORECASE):
        return s[:start], tail
    return None


class VisibleToolJsonFilter:
    """Hold back an incomplete leading tool blob; emit safe text prefixes."""

    def __init__(self) -> None:
        self._buf = ""

    def feed(self, chunk: str) -> List[str]:
        if not chunk:
            return []
        self._buf += chunk
        emitted: List[str] = []
        while self._buf:
            if not self._buf:
                break
            st_b = self._try_strip_leading_bracket_tool_call()
            if st_b is True:
                continue
            if st_b is None:
                break
            st = self._try_strip_leading_call_tool()
            if st is True:
                continue
            if st is None:
                break
            st_angle = self._try_strip_leading_angle_tool()
            if st_angle is True:
                continue
            if st_angle is None:
                break
            st2 = self._try_strip_leading_tool_json_object()
            if st2 is True:
                continue
            if st2 is None:
                break
            m = _first_tool_marker(self._buf)
            if m is None:
                partial = _split_partial_tool_marker(self._buf)
                if partial is not None:
                    emit, hold = partial
                    if emit:
                        emitted.append(emit)
                    self._buf = hold
                    break
                emitted.append(self._buf)
                self._buf = ""
                break
            if m.start() > 0:
                emitted.append(self._buf[: m.start()])
                self._buf = self._buf[m.start() :]
                continue
            if _TOOL_JSON_HEAD.match(self._buf):
                dec = _raw_decode(self._buf)
                if dec is None:
                    break
                obj, end = dec
                if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
                    self._buf = _eat_leading_newlines_only(self._buf[end:])
                    continue
                emitted.append(self._buf[:end])
                self._buf = _eat_leading_newlines_only(self._buf[end:])
                continue
            if _ANGLE_TOOL_HEAD.match(self._buf):
                st_angle = self._try_strip_leading_angle_tool()
                if st_angle is True:
                    continue
                if st_angle is None:
                    break
            if _CALL_TOOL_HEAD.match(self._buf):
                st = self._try_strip_leading_call_tool()
                if st is True:
                    continue
                if st is None:
                    break
            if _BRACKET_TOOL_HEAD.match(self._buf):
                st_b = self._try_strip_leading_bracket_tool_call()
                if st_b is True:
                    continue
                if st_b is None:
                    break
            emitted.append(self._buf[0])
            self._buf = self._buf[1:]
        return emitted

    def flush(self) -> List[str]:
        out: List[str] = []
        while self._buf:
            if not self._buf:
                break
            st_b = self._try_strip_leading_bracket_tool_call(eof=True)
            if st_b is True:
                continue
            if st_b is None:
                break
            st = self._try_strip_leading_call_tool(eof=True)
            if st is True:
                continue
            if st is None:
                break
            st_angle = self._try_strip_leading_angle_tool(eof=True)
            if st_angle is True:
                continue
            if st_angle is None:
                break
            st2 = self._try_strip_leading_tool_json_object(eof=True)
            if st2 is True:
                continue
            if st2 is None:
                break
            m = _first_tool_marker(self._buf)
            if m is not None and m.start() > 0:
                out.append(self._buf[: m.start()])
                self._buf = self._buf[m.start() :]
                continue
            if m is not None and m.start() == 0 and _TOOL_JSON_HEAD.match(self._buf):
                self._buf = ""
                break
            if m is not None and m.start() == 0 and _ANGLE_TOOL_HEAD.match(self._buf):
                st_angle = self._try_strip_leading_angle_tool(eof=True)
                if st_angle is True:
                    continue
                self._buf = ""
                break
            if m is not None and m.start() == 0 and _CALL_TOOL_HEAD.match(self._buf):
                st = self._try_strip_leading_call_tool(eof=True)
                if st is True:
                    continue
                self._buf = ""
                break
            if m is not None and m.start() == 0 and _BRACKET_TOOL_HEAD.match(self._buf):
                st_b = self._try_strip_leading_bracket_tool_call(eof=True)
                if st_b is True:
                    continue
                self._buf = ""
                break
            out.append(self._buf)
            self._buf = ""
        return out

    def _try_strip_leading_bracket_tool_call(self, *, eof: bool = False) -> Optional[bool]:
        """Strip ``[TOOL_CALL] … [/TOOL_CALL]`` (including empty inner content)."""
        m = _BRACKET_TOOL_HEAD.match(self._buf)
        if not m:
            return False
        rest = self._buf[m.end() :]
        lower = rest.lower()
        close_idx = lower.find("[/tool_call]")
        if close_idx == -1:
            if eof:
                self._buf = ""
                return True
            return None
        tail_from_close = rest[close_idx:]
        cm = _BRACKET_TOOL_CLOSE_HEAD.match(tail_from_close)
        if not cm:
            if eof:
                self._buf = ""
                return True
            return None
        self._buf = _eat_leading_newlines_only(tail_from_close[cm.end() :])
        return True

    def _try_strip_leading_call_tool(self, *, eof: bool = False) -> Optional[bool]:
        """True stripped, False no match, None hold (incomplete)."""
        m = _CALL_TOOL_HEAD.match(self._buf)
        if not m:
            return False
        rest = self._buf[m.end() :]
        if not rest.strip():
            if eof:
                self._buf = ""
                return True
            return None
        dec = _raw_decode(rest)
        if dec is None:
            if eof:
                self._buf = ""
                return True
            if rest.lstrip().startswith("{"):
                return None
            self._buf = _eat_leading_newlines_only(rest)
            return True
        _, end = dec
        self._buf = _eat_leading_newlines_only(rest[end:])
        return True

    def _try_strip_leading_angle_tool(self, *, eof: bool = False) -> Optional[bool]:
        """Strip ``<tool_call> [Tool] {...} </tool_call>`` text calls."""
        m = _ANGLE_TOOL_HEAD.match(self._buf)
        if not m:
            return False
        rest = self._buf[m.end() :]
        if not rest.strip():
            if eof:
                self._buf = ""
                return True
            return None
        dec = _raw_decode(rest.lstrip())
        if dec is None:
            if eof:
                self._buf = ""
                return True
            if rest.lstrip().startswith("{"):
                return None
            self._buf = _eat_leading_newlines_only(rest)
            return True
        _, end = dec
        leading = len(rest) - len(rest.lstrip())
        tail = rest[leading + end :]
        close = _ANGLE_TOOL_CLOSE.match(tail)
        if close:
            tail = tail[close.end() :]
        elif not eof:
            return None
        self._buf = _eat_leading_newlines_only(tail)
        return True

    def _try_strip_leading_tool_json_object(self, *, eof: bool = False) -> Optional[bool]:
        if not self._buf or self._buf[0] != "{":
            return False
        dec = _raw_decode(self._buf)
        if dec is None:
            if _TOOL_JSON_HEAD.match(self._buf[:8192]):
                if eof:
                    mm = re.search(r"\{\s*\"tool\"\s*:", self._buf)
                    self._buf = self._buf[: mm.start()] if mm else ""
                    return True
                return None
            return False
        obj, end = dec
        if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
            self._buf = _eat_leading_newlines_only(self._buf[end:])
            return True
        return False


def _raw_decode(s: str) -> tuple[object, int] | None:
    try:
        return json.JSONDecoder().raw_decode(s)
    except json.JSONDecodeError:
        return None
