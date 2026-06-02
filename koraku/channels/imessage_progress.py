"""Map agent SSE-style events to short iMessage progress bubbles."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from koraku.channels.context import get_active_channel

MAX_AUTO_BUBBLES = 16
MAX_BUBBLE_CHARS = 380

_SKIP_TOOLS = frozenset({"ChannelSend"})


def _s(v: Any) -> str | None:
    if not isinstance(v, str):
        return None
    t = v.strip()
    return t or None


def _trunc(text: str, limit: int = MAX_BUBBLE_CHARS) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 1].rstrip() + "…"


def bubble_for_tool(tool: str, tool_input: Any) -> str | None:
    """Human-readable 'about to…' line for a tool call."""
    if tool in _SKIP_TOOLS:
        return None
    o = tool_input if isinstance(tool_input, dict) else {}
    name = tool or "tool"

    if name == "WebSearch":
        q = _s(o.get("query"))
        return _trunc(f"Searching the web{f' for “{q}”' if q else ''}…")
    if name in ("WebFetch", "WebPage", "Firecrawl"):
        url = _s(o.get("url"))
        return _trunc(f"Opening a page{f' ({url})' if url else ''}…")
    if name == "FirecrawlMap":
        url = _s(o.get("url"))
        return _trunc(f"Mapping links on a site{f' ({url})' if url else ''}…")
    if name == "Read":
        path = _s(o.get("file_path")) or _s(o.get("path"))
        return _trunc(f"Reading {path or 'a file'}…")
    if name == "Write":
        path = _s(o.get("file_path")) or _s(o.get("path"))
        return _trunc(f"Creating {path or 'a file'}…")
    if name == "Edit":
        path = _s(o.get("file_path")) or _s(o.get("path"))
        return _trunc(f"Editing {path or 'a file'}…")
    if name == "Bash":
        cmd = _s(o.get("command"))
        if cmd:
            return _trunc(f"Running: {cmd[:120]}…")
        return "Running a command…"
    if name == "Glob":
        pat = _s(o.get("pattern"))
        return _trunc(f"Finding files{f' ({pat})' if pat else ''}…")
    if name == "Grep":
        pat = _s(o.get("pattern"))
        return _trunc(f"Searching files{f' for “{pat}”' if pat else ''}…")
    if name == "ComposioRun":
        goal = _s(o.get("goal"))
        return _trunc(f"Using your connected apps{f' — {goal}' if goal else ''}…")
    if name == "MemorySearch":
        q = _s(o.get("query"))
        return _trunc(f"Checking memory{f' for “{q}”' if q else ''}…")
    if name == "MemorySave":
        return "Saving to memory…"
    return _trunc(f"Working: {name}…")


def message_for_agent_event(ev: dict[str, Any]) -> str | None:
    t = str(ev.get("type") or "")
    if t == "tool_execution":
        data = ev.get("data")
        if not isinstance(data, dict):
            return None
        tool = str(data.get("tool") or "")
        return bubble_for_tool(tool, data.get("input"))
    if t == "agent.subagent":
        data = ev.get("data")
        if isinstance(data, dict) and data.get("phase") == "composio_start":
            kits = data.get("toolkits")
            if isinstance(kits, list) and kits:
                names = ", ".join(str(k) for k in kits[:4])
                return _trunc(f"Digging into {names}…")
            return "Using your connected apps…"
    return None


def make_imessage_emit(
    on_send: Callable[[str], Awaitable[None]],
) -> tuple[Callable[[dict[str, Any]], None], Callable[[], Awaitable[None]]]:
    """Sync emit hook + ``drain`` to await scheduled bubbles before the final reply."""
    seen_tool_ids: set[str] = set()
    bubble_count = 0
    opened = False
    pending: list[asyncio.Task[None]] = []

    async def _send(msg: str) -> None:
        nonlocal bubble_count
        if bubble_count >= MAX_AUTO_BUBBLES:
            return
        if get_active_channel() is None:
            return
        body = _trunc(msg)
        if not body:
            return
        bubble_count += 1
        await on_send(body)

    def _schedule(coro: Awaitable[None]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        pending.append(loop.create_task(coro))

    async def drain() -> None:
        if not pending:
            return
        await asyncio.gather(*pending, return_exceptions=True)
        pending.clear()

    def emit(ev: dict[str, Any]) -> None:
        nonlocal opened
        if get_active_channel() is None:
            return

        msg = message_for_agent_event(ev)
        if ev.get("type") == "tool_execution":
            data = ev.get("data") if isinstance(ev.get("data"), dict) else {}
            tid = str(data.get("id") or "")
            if tid:
                if tid in seen_tool_ids:
                    return
                seen_tool_ids.add(tid)
            if not opened:
                opened = True
                _schedule(_send("On it — I'll send updates as I go."))
            if msg:
                _schedule(_send(msg))
            return

        if msg:
            _schedule(_send(msg))

    return emit, drain
