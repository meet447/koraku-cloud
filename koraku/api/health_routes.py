"""Process health and configuration snapshot."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from koraku.automations import scheduler as automation_scheduler
from koraku.automations.supabase_store import supabase_automations_configured
from koraku.integrations.supabase_chat_history import supabase_chat_history_configured
from koraku.integrations.supermemory_client import supermemory_configured
from koraku.integrations.supabase_personalization import supabase_personalization_configured
from koraku.integrations import composio as composio_runtime
from koraku.integrations.blaxel_runtime import cloud_blaxel_block_reason
from koraku.core import redis_client
from koraku.core.detached_run_store import RedisDetachedRunStore, get_detached_run_store
from koraku.core.session_store import active_session_count
from koraku.core.config import settings
from koraku.llm.catalog import any_llm_configured, configured_provider_ids, default_chat_model

router = APIRouter(tags=["health"])


def _health_detail_authorized(authorization: str | None, x_health_token: str | None) -> bool:
    expected = (settings.health_detail_token or "").strip()
    if not expected:
        return False
    for raw in (authorization, x_health_token):
        if not raw:
            continue
        token = raw.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if token == expected:
            return True
    return False


@router.get("/health")
async def health(request: Request):
    """Public liveness + fields required by the web UI."""
    mode = getattr(request.app.state, "server_mode", "unconfigured")
    store = get_detached_run_store()
    return {
        "status": "ok",
        "agent": settings.agent_name,
        "version": settings.version,
        "mode": mode,
        "llm_configured": any_llm_configured(),
        "llm_provider": settings.llm_provider,
        "detached_runs_redis": isinstance(store, RedisDetachedRunStore),
    }


@router.get("/health/detail")
async def health_detail(
    request: Request,
    authorization: str | None = Header(None),
    x_health_token: str | None = Header(None, alias="X-Health-Token"),
):
    """Operational snapshot — requires ``HEALTH_DETAIL_TOKEN`` (Bearer or X-Health-Token)."""
    if not _health_detail_authorized(authorization, x_health_token):
        raise HTTPException(status_code=401, detail="Health detail requires a valid token")

    mode = getattr(request.app.state, "server_mode", "unconfigured")
    return {
        "status": "ok",
        "agent": settings.agent_name,
        "version": settings.version,
        "mode": mode,
        "composio_configured": composio_runtime.is_configured(),
        "llm_configured": any_llm_configured(),
        "llm_provider": settings.llm_provider,
        "configured_providers": configured_provider_ids(),
        "default_model": default_chat_model(),
        "max_steps_standard": settings.max_steps,
        "max_steps_extended": settings.research_max_steps,
        "exa_enabled": bool(settings.exa_api_key),
        "firecrawl_enabled": bool(settings.firecrawl_api_key),
        "session_ttl_hours": settings.session_ttl_hours,
        "session_store_max": settings.session_store_max,
        "session_store_backend": settings.session_store_backend,
        "redis_configured": redis_client.is_configured(),
        "redis_connected": redis_client.get_client() is not None,
        "auth_backend": settings.auth_backend,
        "agent_llm_stream_timeout_seconds": settings.agent_llm_stream_timeout_seconds,
        "agent_tool_phase_timeout_seconds": settings.agent_tool_phase_timeout_seconds,
        "active_chat_sessions": active_session_count(),
        "blaxel_cloud_sandbox_enabled": settings.blaxel_cloud_sandbox_enabled,
        "cloud_chat_sandbox_block_reason": cloud_blaxel_block_reason(settings),
        "automation_scheduler_running": automation_scheduler.is_running(),
        "automation_scheduler_leader": automation_scheduler.is_automation_scheduler_leader(),
        "automation_scheduler_enabled": settings.automation_scheduler_enabled,
        "automation_max_steps": settings.automation_max_steps,
        "automation_run_timeout_seconds": settings.automation_run_timeout_seconds,
        "automations_supabase_configured": supabase_automations_configured(),
        "chat_history_supabase_configured": supabase_chat_history_configured(),
        "personalization_supabase_configured": supabase_personalization_configured(),
        "supermemory_configured": supermemory_configured(),
    }
