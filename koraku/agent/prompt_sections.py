"""Shared system-prompt section builders (no agent loop imports)."""
from __future__ import annotations

import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from koraku.core.config import settings
from koraku.workspace.context import (
    load_agent_display_name,
    load_memory_snippet,
    load_soul_snippet,
    memory_path,
    soul_path,
)

_CLIENT_META_SAFE = re.compile(r"^[A-Za-z0-9_./+\-]+$")
_CLIENT_LOCALE_SAFE = re.compile(r"^[A-Za-z0-9\-_]+$")


def _sanitize_client_meta(value: str | None, max_len: int = 120, pattern: re.Pattern[str] | None = None) -> str | None:
    if not value:
        return None
    s = value.strip()[:max_len]
    if not s or "\n" in s or "\r" in s:
        return None
    pat = pattern or _CLIENT_META_SAFE
    if not pat.match(s):
        return None
    return s


def format_runtime_context_section(
    client_timezone: str | None = None,
    client_locale: str | None = None,
) -> str:
    tz = _sanitize_client_meta(client_timezone, pattern=_CLIENT_META_SAFE)
    loc = _sanitize_client_meta(client_locale, max_len=40, pattern=_CLIENT_LOCALE_SAFE)
    utc_now = datetime.now(tz=ZoneInfo("UTC"))
    lines = [
        "## User runtime context (from the chat client)",
        f"- Authoritative UTC time on server: `{utc_now:%Y-%m-%d %H:%M:%S} UTC`",
    ]
    if tz:
        try:
            local = utc_now.astimezone(ZoneInfo(tz))
            lines.append(f"- User IANA timezone: `{tz}` → local time `{local:%Y-%m-%d %H:%M:%S %Z}`")
        except ZoneInfoNotFoundError:
            lines.append(
                f"- User timezone string was sent but is not a valid IANA zone: `{tz[:80]}` (ignore for clock math)."
            )
    else:
        lines.append(
            "- No IANA timezone was provided. For 'today' or scheduling, infer from wording or ask once; "
            "use **WebSearch** with explicit dates when recency matters."
        )
    if loc:
        lines.append(f"- Browser / OS locale: `{loc}` (use for regional formatting when relevant).")
    lines.append(
        "- For **latest news** or time-sensitive facts: combine this clock with **WebSearch** when appropriate."
    )
    return "\n".join(lines) + "\n\n"


def _snippet_text(text: str, max_chars: int, truncated_note: str) -> str:
    s = text or ""
    if len(s) > max_chars:
        return s[:max_chars] + truncated_note
    return s


def load_personalization_snippets(
    workspace: str,
    account_personalization: dict[str, str] | None,
) -> tuple[str, str, str | None]:
    snippet_cap = int(settings.context_snippet_max_chars)
    if account_personalization is not None:
        mem = _snippet_text(
            account_personalization.get("memory", ""),
            snippet_cap,
            "\n\n[... Memory truncated ...]",
        )
        soul = _snippet_text(
            account_personalization.get("soul", ""),
            snippet_cap,
            "\n\n[... Soul truncated ...]",
        )
        raw_display = (account_personalization.get("agent_name") or "").strip() or None
    else:
        mem = load_memory_snippet(workspace, snippet_cap)
        soul = load_soul_snippet(workspace, snippet_cap)
        raw_display = load_agent_display_name(workspace)

    display_name = None
    if raw_display:
        safe = raw_display.replace("**", "").replace("\n", " ").strip()
        display_name = safe[:120] if safe else None
    return mem, soul, display_name


def format_memory_section(mem: str, account_personalization: dict[str, str] | None, workspace: str) -> str:
    if account_personalization is not None:
        return (
            "## Explicit preferences (Personalization — user-edited in the app)\n"
            f"{mem}\n"
            if mem.strip()
            else (
                "## Explicit preferences (Personalization)\n"
                "No saved preferences yet — the user can add them under **Personalization** in the app.\n"
            )
        )
    return (
        f"## User memory (from `{memory_path(workspace)}`)\n{mem}\n"
        if mem
        else (
            f"## User memory\nPreferences live in `{memory_path(workspace)}` "
            "(create `.koraku/` when needed).\n"
        )
    )


def format_soul_section(soul: str, account_personalization: dict[str, str] | None, workspace: str) -> str:
    if account_personalization is not None:
        return (
            f"## Persona (from Koraku account profile)\n{soul}\n"
            if soul.strip()
            else "## Persona\nNo saved persona text — optional tone under **Personalization**.\n"
        )
    return (
        f"## Persona / soul (from `{soul_path(workspace)}`)\n{soul}\n"
        if soul
        else f"## Persona / soul\nOptional tone: `{soul_path(workspace)}`.\n"
    )


def format_workspace_section(
    ws: str,
    cloud_tool_root: str | None,
    account_personalization: dict[str, str] | None,
) -> str:
    if cloud_tool_root:
        ctr = cloud_tool_root.rstrip("/")
        host_hint = (
            "skills below are loaded from this path; **Memory** and **Soul** come from the user's **Koraku account**"
            if account_personalization is not None
            else "skills/memory below are loaded from here"
        )
        return (
            f"## Workspace\n"
            f"- **Tool-visible directory**: `{ctr}`\n"
            f"- Use **paths relative to that directory** (isolated VM).\n"
            f"- **Repo on the user's machine** ({host_hint}): `{ws}`\n"
        )
    return f"## Workspace\n- Working directory: `{os.path.abspath(ws)}`\n"
