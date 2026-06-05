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
_prompt_section_cache: dict[str, tuple[float, str]] = {}
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
    """
    Composio entity id: per-request JWT user (``set_composio_request_user``), else explicit
    ``COMPOSIO_USER_ID`` / settings for single-tenant embeds.
    """
    ctx = _composio_request_user.get()
    if ctx and ctx.strip():
        return ctx.strip()
    from_env = (os.environ.get("COMPOSIO_USER_ID") or "").strip()
    from_settings = (settings.composio_user_id or "").strip()
    explicit = from_env or (
        from_settings if from_settings and from_settings != "koraku-local" else ""
    )
    if is_configured():
        if explicit:
            return explicit
        raise RuntimeError(
            "Composio requires a per-request user id. "
            "Use set_composio_request_user(auth_sub) or set COMPOSIO_USER_ID for single-tenant mode."
        )
    return explicit or "koraku-local"


def list_connections_summary() -> list[dict[str, Any]]:
    """All connections for the configured Koraku user (any status)."""
    if not is_configured():
        return []

    uid = user_id()
    now = time.monotonic()

    if uid in _connections_cache:
        cache_time, cached_data = _connections_cache[uid]
        if (now - cache_time) < _CACHE_TTL:
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
        _prompt_section_cache.clear()
    _connections_cache[uid] = (time.monotonic(), out)
    for suffix in ("quick", "full", "flat"):
        _prompt_section_cache.pop(f"{uid}:{suffix}", None)
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
    try:
        c = _client()
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
    if not is_configured():
        return []
    tk_slugs = active_toolkit_slugs()
    if not tk_slugs:
        return []
    return _build_dynamic_composio_tools_for_slugs(tk_slugs)


def build_dynamic_composio_tools_for_toolkits(toolkits: list[str]) -> list[Tool]:
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
        "## Connected Integration Infrastructure",
        f"- Scope Context Identifier: `{user_id()}`",
        "- When executing tasks regarding Gmail, Calendar, Drive, Slack, Notion, or Sheets, use the explicit "
        "**Composio** tools in your environment (e.g., `GMAIL_*`, `GOOGLECALENDAR_*`). These interface with the "
        "accounts bound to the environment.",
        "- Never declare evaluation conclusions or make absolute claims about mailbox states, documents, or event logs "
        "(such as stating an inbox is empty, or no matches exist) *until* you have executed the respective tracking "
        "tool and evaluated the operational output payload. Reporting on context assumptions prior to execution is banned.",
        "- Before dispatching mutating requests (sending email, modifying remote data states, publishing events), verify the "
        "structural parameters (recipient targets, channels, timestamps, payload parameters) are cleanly stated. Speak using your "
        "assigned identity layer to verify missing variables naturally.",
        "- If an app configuration is missing or encounters validation failures, explicitly prompt the account owner to check the "
        "**Connections** environment mapping.",
    ]
    active = active_toolkit_slugs()
    if active:
        lines.append(f"- Active Toolset Baselines: {', '.join(active)}.")
    else:
        lines.append(
            "- No integrations are mapped yet. Prompt the session manager to update the **Connections** layout."
        )
    return "\n".join(lines) + "\n\n"


def composio_dispatcher_prompt_section_quick() -> str:
    """Light Composio hint for quick chat — still lists ACTIVE toolkits."""
    if not is_configured():
        return ""
    lines = [
        "## Connected Integration Baselines",
        "- For targeted integrations (Gmail, Calendar, Drive, Slack), call **ComposioRun** supplying the chosen uppercase toolkit "
        "identifier and a single concise, optimized operational `goal`. Frame the intent cleanly using your voice layer.",
        "- If a system target is not connected, reference updating the configuration maps.",
    ]
    active = active_toolkit_slugs()
    if active:
        lines.append(f"- Active Targets: {', '.join(active)}.")
    else:
        lines.append(
            "- No integrated channels mapped. Reference the configuration interface."
        )
    return "\n".join(lines) + "\n\n"


def _cached_composio_prompt_section(cache_key: str, builder: Callable[[], str]) -> str:
    now = time.monotonic()
    cached = _prompt_section_cache.get(cache_key)
    if cached is not None:
        cache_time, text = cached
        if (now - cache_time) < _CACHE_TTL:
            return text
    text = builder()
    _prompt_section_cache[cache_key] = (now, text)
    return text


def composio_prompt_section_for_turn(task_class: str) -> str:
    if not is_configured():
        return ""
    uid = user_id()
    use_quick = (task_class or "").strip().lower() != "research"
    if bool(settings.composio_subagent_mode):
        variant = "quick" if use_quick else "full"
        cache_key = f"{uid}:{variant}"
        builder = (
            composio_dispatcher_prompt_section_quick
            if use_quick
            else composio_dispatcher_prompt_section
        )
        return _cached_composio_prompt_section(cache_key, builder)
    return _cached_composio_prompt_section(f"{uid}:flat", composio_system_prompt_section)


def composio_dispatcher_prompt_section() -> str:
    """System prompt when the main agent uses **ComposioRun** instead of flat Composio tools."""
    if not is_configured():
        return ""
    lines = [
        "## Connected Integration Infrastructure — Task Redirection Mode",
        f"- Scope Context Identifier: `{user_id()}`",
        "- External platform operations (Gmail, Calendar, Drive, Slack, etc.) must be accessed via **ComposioRun**. Do not call standalone action bindings.",
        "- Retain your core tool baseline capabilities (**WebSearch**, **MemorySearch**, and local system tools) alongside this channel.",
        "- Execute **ComposioRun** with the following structural layout parameters:",
        "  - `toolkits`: The uppercase identifier from the validated set detailed below (e.g., `GMAIL`, `GOOGLECALENDAR`).",
        "  - `goal`: A single concise instruction statement for the worker thread. Deliver clear context parameters natively.",
        "- Consolidate operations cleanly; avoid raw chat log duplication into payload string spaces.",
        "- Retain full identity consistency: Do not report data assertions until the subprocess loop returns execution output payloads.",
        "- If an app mapping is not listed, reference updating the configuration dashboard maps.",
    ]
    active = active_toolkit_slugs()
    if active:
        lines.append(f"- Valid Toolset Directives: {', '.join(active)}.")
    else:
        lines.append(
            "- No integrations mapped yet. Prompt the execution environment manager to initialize needed channels."
        )
    return "\n".join(lines) + "\n\n"