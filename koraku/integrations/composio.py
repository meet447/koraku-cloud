"""Composio: OAuth connections + dynamic tools for connected integrations (Gmail, Drive, …)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any, Callable, Coroutine

from concurrent.futures import ThreadPoolExecutor, as_completed

from koraku.core.config import settings
from koraku.integrations.composio_curated_toolkits import CURATED_TOOLKITS, CURATED_TOOLKIT_SLUGS
from koraku.tools.tool_def import Tool

_TOOLKIT_SLUG_SAFE = re.compile(r"^[A-Z0-9][A-Z0-9_]{1,63}$")

logger = logging.getLogger(__name__)

_composio_client: Any = None
_workspace_for_client: str = ""
_composio_tool_map: ContextVar[dict[str, Tool] | None] = ContextVar("koraku_composio_tools", default=None)
# When set, Composio list/auth/execute use this Supabase ``sub`` instead of the global fallback.
_composio_request_user: ContextVar[str | None] = ContextVar("koraku_composio_request_user", default=None)
_connections_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL = 15.0
_CONNECTIONS_CACHE_MAX_SIZE = 2000

_TOOLKITS_CACHE_TTL = 300.0
_curated_toolkits_cache: tuple[float, list[dict[str, str]]] | None = None


def _resolve_curated_toolkit(c: Any, meta: dict[str, str]) -> dict[str, str] | None:
    slug = meta["slug"]
    try:
        tk = c.toolkits.get(slug)
    except Exception:
        logger.debug("Curated toolkit %s not available in Composio", slug, exc_info=True)
        return None
    composio_desc = ""
    tk_meta = getattr(tk, "meta", None)
    if tk_meta is not None:
        composio_desc = str(getattr(tk_meta, "description", "") or "")
    return _curated_row_from_meta(
        dict(meta),
        composio_name=str(getattr(tk, "name", "") or ""),
        composio_desc=composio_desc,
    )

# Composio's toolkit listing is capped and tends to return many low-level actions first (e.g. ACL_*),
# so high-value tools (calendar events, Gmail send/draft) never appear. Always fetch these by slug first.
_COMPOSIO_PRIORITY_SLUGS_BY_TOOLKIT: dict[str, tuple[str, ...]] = {
    "GMAIL": (
        "GMAIL_FETCH_EMAILS",
        "GMAIL_CREATE_EMAIL_DRAFT",
        "GMAIL_SEND_DRAFT",
        "GMAIL_SEND_EMAIL",
        "GMAIL_GET_DRAFT",
        "GMAIL_LIST_DRAFTS",
    ),
    "GOOGLECALENDAR": (
        "GOOGLECALENDAR_EVENTS_LIST",
        "GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS",
        "GOOGLECALENDAR_LIST_CALENDARS",
        "GOOGLECALENDAR_CREATE_EVENT",
        "GOOGLECALENDAR_FIND_EVENT",
        "GOOGLECALENDAR_EVENTS_GET",
        "GOOGLECALENDAR_FREE_BUSY_QUERY",
    ),
}


def effective_api_key() -> str:
    """Key from pydantic settings (repo ``.env``) or process environment (IDE / shell)."""
    return (settings.composio_api_key or os.environ.get("COMPOSIO_API_KEY", "") or "").strip()


def is_configured() -> bool:
    return bool(effective_api_key())


def configure_workspace_cache(workspace: str) -> None:
    """Composio SDK requires a writable ``COMPOSIO_CACHE_DIR`` before first import."""
    global _composio_client, _workspace_for_client
    root = Path(workspace).resolve()
    cache = root / ".koraku" / "composio-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["COMPOSIO_CACHE_DIR"] = str(cache)
    ws = str(root)
    if ws != _workspace_for_client:
        _composio_client = None
        _workspace_for_client = ws


def _client() -> Any:
    global _composio_client
    if not is_configured():
        raise RuntimeError("COMPOSIO_API_KEY is not set")
    if _composio_client is None:
        from composio import Composio  # lazy: needs COMPOSIO_CACHE_DIR

        _composio_client = Composio(api_key=effective_api_key())
    return _composio_client


def set_composio_request_user(user_id: str | None) -> Token | None:
    """Bind Composio API calls to a signed-in user for the current async context."""
    if not user_id or not str(user_id).strip():
        return None
    return _composio_request_user.set(str(user_id).strip())


def reset_composio_request_user(token: Token | None) -> None:
    if token is not None:
        _composio_request_user.reset(token)


def user_id() -> str:
    """Composio entity id: per-request JWT user, else env ``COMPOSIO_USER_ID`` / settings fallback."""
    ctx = _composio_request_user.get()
    if ctx and ctx.strip():
        return ctx.strip()
    return (
        (settings.composio_user_id or os.environ.get("COMPOSIO_USER_ID") or "koraku-local").strip()
        or "koraku-local"
    )


def list_connections_summary() -> list[dict[str, Any]]:
    """All connections for the configured Koraku user (any status)."""
    if not is_configured():
        return []

    uid = user_id()
    now = time.monotonic()

    if uid in _connections_cache:
        cache_time, cached_data = _connections_cache[uid]
        if (now - cache_time) < _CACHE_TTL:
            # Shallow copy of rows (each row is a flat str/bool dict) so callers cannot mutate the cache.
            return [dict(r) for r in cached_data]

    c = _client()
    resp = c.connected_accounts.list(user_ids=[uid], limit=80.0)
    out: list[dict[str, Any]] = []
    for item in resp.items:
        slug = getattr(item.toolkit, "slug", "") or ""
        name = getattr(item.toolkit, "name", "") or slug
        out.append({
            "id": item.id,
            "status": item.status,
            "toolkit_slug": slug,
            "toolkit_name": name,
            "is_disabled": item.is_disabled,
        })

    if len(_connections_cache) >= _CONNECTIONS_CACHE_MAX_SIZE:
        _connections_cache.clear()
    _connections_cache[uid] = (time.monotonic(), out)
    return [dict(r) for r in out]


def active_toolkit_slugs() -> list[str]:
    """Toolkits with at least one ACTIVE, non-disabled connection."""
    slugs: list[str] = []
    for row in list_connections_summary():
        if row.get("status") == "ACTIVE" and not row.get("is_disabled"):
            s = (row.get("toolkit_slug") or "").strip().upper()
            if s and s not in slugs:
                slugs.append(s)
    return slugs


def start_toolkit_auth(toolkit: str, *, callback_url: str | None = None) -> dict[str, Any]:
    """Begin OAuth / Composio Link for a toolkit; returns redirect URL when applicable."""
    # callback_url: reserved for future explicit OAuth return URLs; managed auth uses Composio-hosted flow.
    _ = callback_url
    if not is_configured():
        raise RuntimeError("Composio is not configured")
    slug = toolkit.strip().upper()
    if not _TOOLKIT_SLUG_SAFE.match(slug):
        raise ValueError("Invalid toolkit slug")
    c = _client()
    req = c.toolkits.authorize(user_id=user_id(), toolkit=slug)
    return {
        "connection_request_id": req.id,
        "status": req.status,
        "redirect_url": req.redirect_url,
    }


def _curated_row_from_meta(meta: dict[str, str], *, composio_name: str = "", composio_desc: str = "") -> dict[str, str]:
    name = (composio_name or meta["name"]).strip() or meta["slug"]
    desc = (composio_desc or meta["description"]).strip()
    return {
        "slug": meta["slug"],
        "name": name,
        "description": desc[:240],
        "category": meta["category"],
        "icon_slug": meta["icon_slug"],
    }


def list_curated_toolkits_static(*, query: str = "") -> list[dict[str, str]]:
    """Browse-only catalog from the curated manifest (no Composio API)."""
    return _filter_curated_toolkits(
        [_curated_row_from_meta(dict(meta)) for meta in CURATED_TOOLKITS],
        query=query,
    )


def _filter_curated_toolkits(items: list[dict[str, str]], *, query: str) -> list[dict[str, str]]:
    q = (query or "").strip().lower()
    if not q:
        return items
    return [
        row
        for row in items
        if q in row["slug"].lower()
        or q in row["name"].lower()
        or q in row["description"].lower()
    ]


def list_curated_toolkits(*, query: str = "") -> list[dict[str, str]]:
    """Resolve the curated catalog against Composio; omit slugs Composio does not support."""
    global _curated_toolkits_cache
    now = time.monotonic()
    if _curated_toolkits_cache is not None:
        cache_time, cached = _curated_toolkits_cache
        if (now - cache_time) < _TOOLKITS_CACHE_TTL:
            return _filter_curated_toolkits([dict(r) for r in cached], query=query)

    if not is_configured():
        return list_curated_toolkits_static(query=query)

    c = _client()
    resolved: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_resolve_curated_toolkit, c, dict(meta)): meta["slug"]
            for meta in CURATED_TOOLKITS
        }
        for fut in as_completed(futures):
            row = fut.result()
            if row is not None:
                resolved.append(row)
    resolved.sort(
        key=lambda r: CURATED_TOOLKIT_SLUGS.index(r["slug"])
        if r["slug"] in CURATED_TOOLKIT_SLUGS
        else 999
    )

    _curated_toolkits_cache = (now, resolved)
    return _filter_curated_toolkits([dict(r) for r in resolved], query=query)


def _normalize_input_schema(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {"type": "object", "properties": {}, "required": []}
    if raw.get("type") == "object":
        return raw
    if "properties" in raw:
        return {"type": "object", **{k: v for k, v in raw.items() if k in ("properties", "required", "additionalProperties", "description")}}
    return {"type": "object", "properties": dict(raw), "required": []}


def _execute_factory(slug: str) -> Callable[..., Coroutine[Any, Any, str]]:
    async def _run(**kwargs: Any) -> str:
        return await _execute_composio_tool(slug, kwargs)

    return _run


def _execute_composio_tool_sync(slug: str, arguments: dict[str, Any]) -> str:
    """Sync Composio SDK work; run via ``asyncio.to_thread`` so the asyncio loop stays responsive."""
    try:
        c = _client()
        # Composio SDK refuses ``version="latest"`` unless ``dangerously_skip_version_check`` is set.
        # Pin to the catalog version when available so the API gets a concrete toolkit version.
        version: str | None = None
        try:
            meta = c.tools.get_raw_composio_tool_by_slug(slug)
            v = getattr(meta, "version", None) if meta is not None else None
            if isinstance(v, str) and v.strip() and v.strip().lower() != "latest":
                version = v.strip()
        except Exception:
            pass
        res = c.tools.execute(
            slug=slug,
            arguments=dict(arguments or {}),
            user_id=user_id(),
            version=version,
            dangerously_skip_version_check=True,
        )
        if hasattr(res, "model_dump"):
            res = res.model_dump()
    except Exception as e:
        return f"Error: Composio execute failed: {e}"
    if not isinstance(res, dict):
        return f"Error: unexpected Composio response type: {type(res).__name__}"
    if res.get("successful"):
        try:
            return json.dumps(res.get("data"), indent=2, default=str)[:80_000]
        except (TypeError, ValueError):
            return str(res.get("data"))[:80_000]
    err = res.get("error") or "unknown_error"
    return f"Error: {err}"


async def _execute_composio_tool(slug: str, arguments: dict[str, Any]) -> str:
    if not is_configured():
        return "Error: Composio is not configured (set COMPOSIO_API_KEY)."
    return await asyncio.to_thread(_execute_composio_tool_sync, slug, dict(arguments or {}))


def _tool_from_composio_raw_item(t: Any) -> Tool | None:
    if getattr(t, "is_deprecated", False):
        return None
    slug = t.slug
    desc = (t.human_description or t.description or "").strip() or f"Composio action `{slug}`"
    if len(desc) > 900:
        desc = desc[:897] + "…"
    schema = _normalize_input_schema(dict(t.input_parameters or {}))
    toolkit = getattr(t.toolkit, "slug", "") if t.toolkit else ""
    full_desc = f"[{toolkit}] {desc}" if toolkit else desc
    return Tool(
        name=slug,
        description=full_desc,
        input_schema=schema,
        handler=_execute_factory(slug),
        categories=["composio", toolkit.lower() if toolkit else "composio"],
    )


def _append_tools_from_raw(raw: Any, seen_slugs: set[str], tools: list[Tool]) -> int:
    """Merge Composio raw tool rows into ``tools``; return count of newly added tools."""
    n = 0
    for t in raw:
        item = _tool_from_composio_raw_item(t)
        if item is None or item.name in seen_slugs:
            continue
        seen_slugs.add(item.name)
        tools.append(item)
        n += 1
    return n


def _build_dynamic_composio_tools_for_slugs(tk_slugs: list[str]) -> list[Tool]:
    """Build Composio tools for a non-empty list of toolkit slugs (callers validate ACTIVE / configured)."""
    c = _client()
    cap = max(8, min(int(settings.composio_tools_limit), 120))
    per_toolkit = max(1, cap // len(tk_slugs))
    seen_slugs: set[str] = set()
    tools: list[Tool] = []

    added_by_tk: dict[str, int] = {tk: 0 for tk in tk_slugs}

    priority_slugs: list[str] = []
    for tk in tk_slugs:
        slugs = _COMPOSIO_PRIORITY_SLUGS_BY_TOOLKIT.get(tk)
        if slugs:
            priority_slugs.extend(slugs)

    if priority_slugs:
        try:
            raw_priority = c.tools.get_raw_composio_tools(tools=priority_slugs)
            for t in raw_priority:
                item = _tool_from_composio_raw_item(t)
                if item is None or item.name in seen_slugs:
                    continue
                toolkit_slug = (getattr(t.toolkit, "slug", "") if getattr(t, "toolkit", None) else "").strip().upper()
                if not toolkit_slug:
                    parts = item.name.split("_")
                    if parts:
                        toolkit_slug = parts[0]
                seen_slugs.add(item.name)
                tools.append(item)
                if toolkit_slug in added_by_tk:
                    added_by_tk[toolkit_slug] += 1
        except Exception:
            logger.warning("Composio get_raw_composio_tools failed for priority slugs", exc_info=True)

    try:
        fetch_limit = cap * 2
        raw_general = c.tools.get_raw_composio_tools(toolkits=tk_slugs, limit=float(fetch_limit))

        for t in raw_general:
            item = _tool_from_composio_raw_item(t)
            if item is None or item.name in seen_slugs:
                continue
            toolkit_slug = (getattr(t.toolkit, "slug", "") if getattr(t, "toolkit", None) else "").strip().upper()
            if not toolkit_slug:
                parts = item.name.split("_")
                if parts:
                    toolkit_slug = parts[0]

            if toolkit_slug in added_by_tk and added_by_tk[toolkit_slug] >= per_toolkit:
                continue

            seen_slugs.add(item.name)
            tools.append(item)
            if toolkit_slug in added_by_tk:
                added_by_tk[toolkit_slug] += 1
    except Exception:
        logger.warning("Composio get_raw_composio_tools failed for general toolkits: %s", tk_slugs, exc_info=True)

    return tools


def build_dynamic_composio_tools() -> list[Tool]:
    """Anthropic-shaped tools for active integrations only.

    Fetches tools **per connected toolkit** with an even share of ``composio_tools_limit`` so
    one toolkit (e.g. Gmail) cannot fill the entire budget and hide another (e.g. Calendar).

    For toolkits in ``_COMPOSIO_PRIORITY_SLUGS_BY_TOOLKIT``, high-value actions are loaded **by
    explicit slug** first; Composio's paginated toolkit list often omits them (e.g. many ``ACL_*``
    tools sort before ``GOOGLECALENDAR_EVENTS_LIST``).
    """
    if not is_configured():
        return []
    tk_slugs = active_toolkit_slugs()
    if not tk_slugs:
        return []
    return _build_dynamic_composio_tools_for_slugs(tk_slugs)


def build_dynamic_composio_tools_for_toolkits(toolkits: list[str]) -> list[Tool]:
    """Composio tools for **only** the given toolkits (must be ACTIVE connections).

    Used by the Composio sub-agent so each run exposes a small, toolkit-scoped tool surface
    instead of every integration at once.
    """
    if not is_configured():
        return []
    active = set(active_toolkit_slugs())
    tk_slugs: list[str] = []
    for raw in toolkits or []:
        s = str(raw).strip().upper()
        if not s or s not in active:
            continue
        if not _TOOLKIT_SLUG_SAFE.match(s):
            continue
        if s not in tk_slugs:
            tk_slugs.append(s)
    if not tk_slugs:
        return []
    return _build_dynamic_composio_tools_for_slugs(tk_slugs)


def push_composio_tool_registry(tools: list[Tool]) -> Token | None:
    if not tools:
        return None
    return _composio_tool_map.set({t.name: t for t in tools})


def reset_composio_tool_registry(token: Token | None) -> None:
    if token is not None:
        _composio_tool_map.reset(token)


def get_registered_composio_tool(name: str) -> Tool | None:
    m = _composio_tool_map.get()
    if not m:
        return None
    return m.get(name)


def composio_system_prompt_section() -> str:
    """Injected into the Koraku system prompt when Composio is available."""
    if not is_configured():
        return ""
    lines = [
        "## Connected integrations (Composio)",
        f"- Koraku user id for Composio: `{user_id()}`",
        "- When the user asks to use Gmail, Google Calendar, Google Drive, Slack, Notion, Sheets, or similar apps, "
        "prefer the **Composio** tools that appear in your tool list (for example `GMAIL_*`, `GOOGLECALENDAR_*`, "
        "`GOOGLEDRIVE_*`). They run against the accounts connected in the Koraku **Connections** page.",
        "- For read/search/list tasks, use connected tools directly when available and summarize the account/tool target.",
        "- **Never** tell the user specific mailbox/calendar/Drive contents (counts, subjects, snippets, 'no emails', "
        "'inbox empty', 'nothing found') **before** you have run the relevant Composio tool and read its output. "
        "Guessing from chat context alone is wrong and reads as contradictory when you later report tool results.",
        "- For external side effects like sending email, posting a message, creating/updating calendar events, sharing files, "
        "or editing remote data, verify the recipient/channel/date/content/attachment first. If the user's intent and "
        "details are already explicit, proceed; otherwise ask for the missing high-impact detail.",
        "- If no relevant tool is available, suggest opening **Connections** to connect the needed app. If a Composio tool "
        "returns an auth error, tell the user to reconnect that service in **Connections**.",
    ]
    active = active_toolkit_slugs()
    if active:
        lines.append(f"- Currently **active** toolkits: {', '.join(active)}.")
    else:
        lines.append(
            "- No integrations are **ACTIVE** yet. Suggest opening **Connections** in the app to connect Gmail, "
            "Google Drive, or other services."
        )
    return "\n".join(lines) + "\n\n"


def composio_dispatcher_prompt_section_quick() -> str:
    """Light Composio hint for quick chat — still lists ACTIVE toolkits."""
    if not is_configured():
        return ""
    lines = [
        "## Connected integrations (Composio)",
        "- For Gmail, Calendar, Drive, Slack, and similar tasks, call **ComposioRun** once with ACTIVE "
        "toolkit slugs and a **short, concrete** `goal` (rewrite the user ask — not a copy-paste of chat).",
        "- If the user has not connected an app, suggest the **Connections** page.",
    ]
    active = active_toolkit_slugs()
    if active:
        lines.append(f"- **ACTIVE** toolkits: {', '.join(active)}.")
    else:
        lines.append(
            "- No integrations are **ACTIVE** yet. Suggest **Connections** in the app."
        )
    return "\n".join(lines) + "\n\n"


def composio_dispatcher_prompt_section() -> str:
    """System prompt when the main agent uses **ComposioRun** instead of flat Composio tools."""
    if not is_configured():
        return ""
    lines = [
        "## Connected integrations (Composio) — sub-agent mode",
        f"- Koraku user id for Composio: `{user_id()}`",
        "- Linked apps (Gmail, Calendar, Drive, Slack, …) are accessed via **ComposioRun**, not as individual tools on this agent.",
        "- You still have **WebSearch**, **MemorySearch**, and workspace tools — use whichever fits the user ask.",
        "- For linked-app work, call **ComposioRun** with:",
        "  - `toolkits`: **ACTIVE** toolkit slugs from the list below (uppercase, e.g. `GMAIL`, `GOOGLECALENDAR`).",
        "  - `goal`: one crisp instruction for the worker (include concrete params when known, e.g. Gmail `query: …`).",
        "- Distill intent into `goal`; do not paste the full chat transcript.",
        "- Prefer one ComposioRun per app task when possible; combine toolkits when the task truly spans apps.",
        "- Do not claim inbox/calendar/Drive contents until ComposioRun returns (brief 'checking…' is fine).",
        "- Prefer drafts over send when the user did not clearly confirm.",
        "- If a toolkit is missing, suggest **Connections** in the app.",
    ]
    active = active_toolkit_slugs()
    if active:
        lines.append(f"- **ACTIVE** toolkits (valid `toolkits` values): {', '.join(active)}.")
    else:
        lines.append(
            "- No integrations are **ACTIVE** yet. Suggest **Connections** in the app to link Gmail, Google Calendar, etc."
        )
    return "\n".join(lines) + "\n\n"
