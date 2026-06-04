"""Map agent SSE-style events to automation run progress fields."""
from __future__ import annotations

import time
from typing import Any

_last_patch_at: dict[str, float] = {}
_MIN_INTERVAL_SEC = 1.0


def progress_from_event(ev: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (phase, detail) for persistence, or (None, None) to skip."""
    et = str(ev.get("type") or "")
    data = ev.get("data") if isinstance(ev.get("data"), dict) else {}
    if et == "agent.tools":
        tools = data.get("tools")
        if isinstance(tools, list) and tools:
            return "tools", f"Tools: {', '.join(str(t) for t in tools[:6])}"
        return "tools", "Loading tools…"
    if et == "tool_execution":
        name = str(data.get("tool") or "tool")
        return "tool", f"Running {name}"
    if et == "agent.trace":
        trace = str(data.get("trace") or "")
        if trace == "worker_status":
            msg = str(data.get("message") or "Working…")
            return "working", msg[:200]
    if et == "agent.mode":
        mode = str(data.get("mode") or "running")
        return "agent", f"Mode: {mode}"
    if et == "agent.error":
        err = str(data.get("error") or "Error")
        return "error", err[:200]
    return None, None


def should_throttle_progress_patch(run_id: str) -> bool:
    rid = (run_id or "").strip()
    if not rid:
        return True
    now = time.monotonic()
    last = _last_patch_at.get(rid, 0.0)
    if now - last < _MIN_INTERVAL_SEC:
        return True
    _last_patch_at[rid] = now
    return False
