"""Load chat thread messages from Supabase for LLM session context (PostgREST + service role)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any
import httpx

from koraku.core.config import settings
from koraku.core.models import AgentMessage, SessionState

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatHistoryHydration:
    session_id: str
    source: str
    reason: str
    auth_present: bool
    supabase_configured: bool
    rows_fetched: int
    messages_loaded: int
    messages_before: int

    def to_trace_data(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source": self.source,
            "reason": self.reason,
            "auth_present": self.auth_present,
            "supabase_configured": self.supabase_configured,
            "rows_fetched": self.rows_fetched,
            "messages_loaded": self.messages_loaded,
            "messages_before": self.messages_before,
        }


def supabase_chat_history_configured() -> bool:
    u = (settings.supabase_url or "").strip().rstrip("/")
    k = (settings.supabase_service_role_key or "").strip()
    return bool(u and k)


def _require_rest() -> tuple[str, str]:
    u = (settings.supabase_url or "").strip().rstrip("/")
    k = (settings.supabase_service_role_key or "").strip()
    if not u or not k:
        raise RuntimeError("Supabase URL and service role key required for chat history fetch.")
    return u, k


def _headers() -> dict[str, str]:
    _, key = _require_rest()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _rest_url(path: str) -> str:
    base, _ = _require_rest()
    return f"{base}/rest/v1{path}"


def _user_text_from_content_json(cj: dict[str, Any]) -> str:
    return str(cj.get("text") or "").strip()


def _assistant_run_dict(cj: dict[str, Any]) -> dict[str, Any]:
    r = cj.get("run")
    return r if isinstance(r, dict) else {}


def _assistant_incomplete_placeholder(run: dict[str, Any]) -> bool:
    md = str(run.get("assistantMarkdown") or "").strip()
    if md:
        return False
    if run.get("error"):
        return False
    return True


def trim_persisted_rows_for_incoming_message(rows: list[dict[str, Any]], incoming_user_text: str) -> list[dict[str, Any]]:
    """Drop a trailing (user, assistant) pair when it matches the in-flight persist from the web UI."""
    incoming_s = (incoming_user_text or "").strip()
    out = list(rows)
    while len(out) >= 2:
        u_row, a_row = out[-2], out[-1]
        if (u_row.get("role") or "") != "user" or (a_row.get("role") or "") != "assistant":
            break
        uj = u_row.get("content_json")
        aj = a_row.get("content_json")
        if not isinstance(uj, dict):
            uj = {}
        if not isinstance(aj, dict):
            aj = {}
        utext = _user_text_from_content_json(uj)
        run = _assistant_run_dict(aj)
        if _assistant_incomplete_placeholder(run) and incoming_s == utext:
            out = out[:-2]
            continue
        break
    return out


def _user_row_to_agent_message(cj: dict[str, Any]) -> AgentMessage:
    text = _user_text_from_content_json(cj) or "(empty message)"
    return AgentMessage(role="user", content=[{"type": "text", "text": text}])


def _assistant_row_to_agent_message(cj: dict[str, Any]) -> AgentMessage | None:
    run = _assistant_run_dict(cj)
    md = str(run.get("assistantMarkdown") or "").strip()
    if not md and run.get("error"):
        md = f"(Assistant error: {run.get('error')})"
    if not md:
        return None
    return AgentMessage(role="assistant", content=[{"type": "text", "text": md}])


def db_message_rows_to_agent_messages(rows: list[dict[str, Any]]) -> list[AgentMessage]:
    out: list[AgentMessage] = []
    for row in rows:
        role = (row.get("role") or "").strip()
        cj = row.get("content_json")
        if not isinstance(cj, dict):
            cj = {}
        if role == "user":
            out.append(_user_row_to_agent_message(cj))
        elif role == "assistant":
            msg = _assistant_row_to_agent_message(cj)
            if msg is not None:
                out.append(msg)
    return out


def client_history_rows_to_agent_messages(rows: list[dict[str, Any]]) -> list[AgentMessage]:
    """Map browser-provided visible chat history to LLM messages.

    This is a fallback for cases where DB history is unavailable because auth/config/lookup
    failed. It intentionally only accepts visible text, not tool payloads.
    """
    out: list[AgentMessage] = []
    for row in rows:
        role = str(row.get("role") or "").strip()
        text = str(row.get("text") or "").strip()
        if role not in ("user", "assistant") or not text:
            continue
        out.append(AgentMessage(role=role, content=[{"type": "text", "text": text}]))
    return out


def fetch_thread_messages_sync(
    thread_id: str,
    user_sub: str,
    *,
    org_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """Return ``chat_message`` rows or ``None`` on skip / hard failure."""
    tid = (thread_id or "").strip()
    uid = (user_sub or "").strip()
    if not tid or not uid:
        return None
    try:
        uuid.UUID(tid)
        uuid.UUID(uid)
    except ValueError:
        return None
    if not supabase_chat_history_configured():
        return None

    try:
        with httpx.Client(timeout=30.0) as client:
            tq = f"/chat_thread?id=eq.{tid}&user_id=eq.{uid}&select=id&limit=1"
            if (org_id or "").strip():
                tq = (
                    f"/chat_thread?id=eq.{tid}&user_id=eq.{uid}"
                    f"&org_id=eq.{(org_id or '').strip()}&select=id&limit=1"
                )
            tr = client.get(_rest_url(tq), headers=_headers())
            tr.raise_for_status()
            trows = tr.json()
            if not isinstance(trows, list) or len(trows) == 0:
                return None

            mq = f"/chat_message?thread_id=eq.{tid}&order=created_at.asc&select=role,content_json"
            mr = client.get(_rest_url(mq), headers=_headers())
            mr.raise_for_status()
            mrows = mr.json()
            if not isinstance(mrows, list):
                return []
            return [x for x in mrows if isinstance(x, dict)]
    except Exception as e:
        log.warning("supabase chat history fetch failed: %s", e)
        return None


async def hydrate_session_messages_from_db(
    session: SessionState,
    *,
    incoming_user_text: str,
    auth_sub: str | None,
    auth_org_id: str | None = None,
    client_history: list[dict[str, Any]] | None = None,
) -> ChatHistoryHydration:
    """Replace ``session.messages`` with the best available prior chat history."""
    configured = supabase_chat_history_configured()
    messages_before = len(session.messages)

    def report(source: str, reason: str, rows_fetched: int, messages_loaded: int) -> ChatHistoryHydration:
        return ChatHistoryHydration(
            session_id=session.session_id,
            source=source,
            reason=reason,
            auth_present=bool(auth_sub),
            supabase_configured=configured,
            rows_fetched=rows_fetched,
            messages_loaded=messages_loaded,
            messages_before=messages_before,
        )

    def apply_client_history(reason: str) -> ChatHistoryHydration | None:
        fallback = client_history_rows_to_agent_messages(list(client_history or []))
        if not fallback:
            return None
        session.messages = fallback
        session.touch()
        return report("client", reason, 0, len(fallback))

    if not auth_sub:
        fallback_report = apply_client_history("missing_auth")
        if fallback_report is not None:
            return fallback_report
        return report("memory", "missing_auth" if messages_before else "missing_auth_empty", 0, messages_before)

    if not configured:
        fallback_report = apply_client_history("supabase_not_configured")
        if fallback_report is not None:
            return fallback_report
        return report(
            "memory",
            "supabase_not_configured" if messages_before else "supabase_not_configured_empty",
            0,
            messages_before,
        )

    rows = await asyncio.to_thread(
        fetch_thread_messages_sync,
        session.session_id,
        auth_sub,
        org_id=auth_org_id,
    )
    if rows is None:
        fallback_report = apply_client_history("db_unavailable")
        if fallback_report is not None:
            return fallback_report
        return report("memory", "db_unavailable" if messages_before else "db_unavailable_empty", 0, messages_before)

    trimmed = trim_persisted_rows_for_incoming_message(rows, incoming_user_text)
    mapped = db_message_rows_to_agent_messages(trimmed)
    if not mapped:
        fallback_report = apply_client_history("db_empty")
        if fallback_report is not None:
            return fallback_report
    session.messages = mapped
    session.touch()
    return report("supabase", "ok", len(rows), len(mapped))

