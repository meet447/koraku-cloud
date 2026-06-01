"""Supermemory: learned user context (profile + search). Supabase stays explicit identity/soul."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from koraku.core.config import settings

if TYPE_CHECKING:
    from koraku.core.models import SessionState

log = logging.getLogger(__name__)

_CLIENT: Any = None


def supermemory_configured() -> bool:
    return bool((settings.supermemory_api_key or "").strip())


def _api_key() -> str:
    return (settings.supermemory_api_key or "").strip()


def container_tag(user_id: str, org_id: str | None = None) -> str:
    """Stable Supermemory namespace per Koraku user (optionally scoped by org)."""
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    raw = f"{oid}:{uid}" if oid else uid
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", raw)[:120].strip("-") or "user"
    return f"koraku-{safe}"


def _client() -> Any:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not supermemory_configured():
        raise RuntimeError("SUPERMEMORY_API_KEY is not set")
    from supermemory import Supermemory

    _CLIENT = Supermemory(api_key=_api_key())
    return _CLIENT


def _format_profile_response(profile: Any, *, max_chars: int) -> str:
    lines: list[str] = []
    prof = getattr(profile, "profile", None)
    if prof is not None:
        static = getattr(prof, "static", None) or []
        dynamic = getattr(prof, "dynamic", None) or []
        if static:
            lines.append("**Long-term facts**")
            for item in static[:24]:
                s = str(item).strip()
                if s:
                    lines.append(f"- {s}")
        if dynamic:
            lines.append("**Recent context**")
            for item in dynamic[:16]:
                s = str(item).strip()
                if s:
                    lines.append(f"- {s}")
    search = getattr(profile, "search_results", None)
    results = getattr(search, "results", None) if search is not None else None
    if results:
        lines.append("**Relevant to this message**")
        for row in results[:12]:
            mem = ""
            if isinstance(row, dict):
                mem = str(row.get("memory") or row.get("content") or "").strip()
            else:
                mem = str(getattr(row, "memory", "") or getattr(row, "content", "") or "").strip()
            if mem:
                lines.append(f"- {mem}")
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[... learned memory truncated ...]"
    return text


def fetch_learned_context_sync(
    user_id: str,
    *,
    org_id: str | None = None,
    query: str | None = None,
) -> str:
    """Profile + optional query search for injection into the system prompt."""
    if not supermemory_configured():
        return ""
    uid = (user_id or "").strip()
    if not uid:
        return ""
    tag = container_tag(uid, org_id)
    q = (query or "").strip()
    try:
        c = _client()
        if q:
            resp = c.profile(container_tag=tag, q=q, threshold=0.55)
        else:
            resp = c.profile(container_tag=tag)
        body = _format_profile_response(resp, max_chars=max(500, int(settings.supermemory_context_max_chars)))
        if not body:
            return ""
        return (
            "## Learned memory (Supermemory — auto-extracted across chats)\n"
            f"{body}\n\n"
            "Use **MemorySearch** to recall more, **MemorySave** when the user asks you to remember something durable.\n"
            "Do not duplicate explicit preferences from **Persona** / **Explicit preferences** above.\n"
        )
    except Exception as e:
        log.warning("supermemory profile failed tag=%s: %s", tag[:32], e)
        return ""


def search_memories_sync(
    user_id: str,
    query: str,
    *,
    org_id: str | None = None,
    limit: int = 8,
) -> str:
    if not supermemory_configured():
        return "Error: Supermemory is not configured (set SUPERMEMORY_API_KEY)."
    uid = (user_id or "").strip()
    q = (query or "").strip()
    if not uid or not q:
        return "Error: query required."
    tag = container_tag(uid, org_id)
    try:
        c = _client()
        resp = c.search.memories(
            q=q,
            container_tag=tag,
            limit=max(1, min(int(limit), 20)),
            search_mode="hybrid",
            threshold=0.5,
        )
        results = getattr(resp, "results", None) or []
        if not results:
            return "No matching memories found."
        lines: list[str] = []
        for i, row in enumerate(results[:limit], 1):
            mem = ""
            score = ""
            if isinstance(row, dict):
                mem = str(row.get("memory") or row.get("content") or "").strip()
                score = row.get("score")
            else:
                mem = str(getattr(row, "memory", "") or getattr(row, "content", "") or "").strip()
                score = getattr(row, "score", None)
            if not mem:
                continue
            suffix = f" (score {score:.2f})" if isinstance(score, (int, float)) else ""
            lines.append(f"{i}. {mem}{suffix}")
        return "\n".join(lines) if lines else "No matching memories found."
    except Exception as e:
        log.warning("supermemory search failed: %s", e)
        return f"Error searching memory: {e}"


def save_memory_sync(
    user_id: str,
    content: str,
    *,
    org_id: str | None = None,
    session_id: str | None = None,
) -> str:
    if not supermemory_configured():
        return "Error: Supermemory is not configured."
    uid = (user_id or "").strip()
    text = (content or "").strip()
    if not uid or not text:
        return "Error: content required."
    tag = container_tag(uid, org_id)
    meta: dict[str, str] = {"source": "koraku_agent", "app": "koraku"}
    if session_id:
        meta["session_id"] = session_id.strip()[:64]
    custom_id = None
    if session_id and len(text) < 200:
        custom_id = f"koraku-note-{session_id[:36]}-{abs(hash(text)) % 10_000_000}"
    try:
        c = _client()
        c.add(
            content=text,
            container_tag=tag,
            metadata=meta,
            custom_id=custom_id,
            task_type="memory",
        )
        return "Saved to long-term memory."
    except Exception as e:
        log.warning("supermemory add failed: %s", e)
        return f"Error saving memory: {e}"


def extract_last_assistant_text(session: "SessionState") -> str:
    """Plain text from the latest assistant turn (for post-turn Supermemory ingest)."""
    for message in reversed(session.messages):
        if message.role != "assistant":
            continue
        content = message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
            return "\n".join(parts).strip()
    return ""


def ingest_chat_turn_sync(
    user_id: str,
    *,
    user_text: str,
    assistant_text: str,
    org_id: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
) -> None:
    """After a chat turn, let Supermemory extract/update memories from the exchange."""
    if not supermemory_configured():
        return
    uid = (user_id or "").strip()
    u = (user_text or "").strip()
    a = (assistant_text or "").strip()
    if not uid or (not u and not a):
        return
    tag = container_tag(uid, org_id)
    parts: list[str] = []
    if u:
        parts.append(f"user: {u}")
    if a:
        parts.append(f"assistant: {a}")
    body = "\n".join(parts)
    meta: dict[str, str] = {"source": "koraku_chat_turn", "app": "koraku"}
    if session_id:
        meta["session_id"] = session_id.strip()[:64]
    custom_id = None
    if run_id:
        custom_id = f"koraku-turn-{run_id.strip()[:80]}"
    try:
        c = _client()
        c.add(
            content=body,
            container_tag=tag,
            metadata=meta,
            custom_id=custom_id,
            task_type="memory",
        )
    except Exception as e:
        log.warning("supermemory ingest turn failed: %s", e)
