"""Local learned memory under ``.koraku/learned.md`` (no external API)."""
from __future__ import annotations

import re
from pathlib import Path

from koraku.workspace.context import koraku_dir
from koraku.tools.tool_def import Tool

_LEARNED_FILE = "learned.md"
_MAX_FILE_CHARS = 200_000
_MAX_ENTRY_CHARS = 2_000


def learned_memory_path(workspace: str) -> Path:
    return koraku_dir(workspace) / _LEARNED_FILE


def _read_learned(workspace: str) -> str:
    path = learned_memory_path(workspace)
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) > _MAX_FILE_CHARS:
        return text[-_MAX_FILE_CHARS:]
    return text


def _append_learned(workspace: str, content: str) -> None:
    line = " ".join((content or "").split())
    if not line:
        return
    line = line[:_MAX_ENTRY_CHARS]
    path = learned_memory_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = path.read_text(encoding="utf-8", errors="replace")
        body = (existing.rstrip() + "\n" if existing.strip() else "") + f"- {line}\n"
    else:
        body = f"# Learned memory\n\n- {line}\n"
    if len(body) > _MAX_FILE_CHARS:
        body = body[-_MAX_FILE_CHARS:]
    path.write_text(body, encoding="utf-8")


def _search_learned(workspace: str, query: str, *, limit: int) -> str:
    blob = _read_learned(workspace)
    if not blob.strip():
        return "No learned memories saved yet."
    q = (query or "").strip().lower()
    lines = [ln.strip() for ln in blob.splitlines() if ln.strip() and not ln.startswith("#")]
    if not q:
        hits = lines[-limit:]
    else:
        tokens = [t for t in re.split(r"\W+", q) if len(t) >= 2]
        scored: list[tuple[int, str]] = []
        for ln in lines:
            low = ln.lower()
            score = sum(1 for t in tokens if t in low) if tokens else (1 if q in low else 0)
            if score > 0:
                scored.append((score, ln))
        scored.sort(key=lambda x: (-x[0], x[1]))
        hits = [ln for _, ln in scored[:limit]]
    if not hits:
        return "No matching learned memories."
    return "\n".join(f"- {h.lstrip('- ').strip()}" for h in hits)


class FilesystemLearnedMemoryBackend:
    name = "filesystem"

    def supports_agent_tools(self) -> bool:
        return True

    def agent_tools(self) -> list[Tool]:
        return [_search_tool, _save_tool]

    async def prefetch_learned(self, user_input: str, *, workspace: str) -> str:
        q = (user_input or "").strip()
        if not q:
            return ""
        block = _search_learned(workspace, q, limit=6)
        if block.startswith("No "):
            return ""
        return f"## Learned memory (local)\n{block}\n"


async def _tool_search(query: str, limit: int = 8) -> str:
    from koraku.workspace.agent_workspace import get_active_agent_workspace

    ws = get_active_agent_workspace()
    if not ws:
        return "Error: No active workspace for memory search."
    return _search_learned(ws, query, limit=max(1, min(int(limit), 20)))


async def _tool_save(content: str) -> str:
    from koraku.workspace.agent_workspace import get_active_agent_workspace

    ws = get_active_agent_workspace()
    if not ws:
        return "Error: No active workspace for memory save."
    _append_learned(ws, content)
    return "Saved to local learned memory (.koraku/learned.md)."


_search_tool = Tool(
    name="MemorySearch",
    description=(
        "Search local learned memory (``.koraku/learned.md``) for facts and preferences. "
        "Use before claims about the user's history or stored preferences."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "limit": {"type": "integer", "description": "Max results (1-20)", "default": 8},
        },
        "required": ["query"],
    },
    handler=_tool_search,
    categories=["memory"],
)

_save_tool = Tool(
    name="MemorySave",
    description=(
        "Save a durable fact to local learned memory (``.koraku/learned.md``). "
        "Use when the user asks to remember something stable — not one-off task output."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Concise fact to remember"},
        },
        "required": ["content"],
    },
    handler=_tool_save,
    categories=["memory"],
)
