"""Shared FastAPI wiring for SDK and Cloud server apps."""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from koraku.agent import Agent
from koraku.core.config import settings
from koraku.core.startup_checks import assert_redis_for_multi_worker
from koraku.llm.catalog import any_llm_configured, default_model_for_provider
from koraku.profiles import is_cloud_profile
from koraku.workspace.paths import workspace_dir

log = logging.getLogger(__name__)


def resolve_server_mode() -> tuple[Agent | None, str]:
    if any_llm_configured():
        return Agent(), "live"
    return None, "unconfigured"


def assert_workspace_safe() -> None:
    ws = workspace_dir()
    if ws == "/" or ws == "":
        raise RuntimeError(
            "Refusing to start: workspace_dir() resolved to filesystem root. "
            "Run Koraku from a project directory, not /."
        )


def assert_cors_safe(mode: str) -> None:
    if mode != "live":
        return
    origins = settings.cors_origins_list
    if not origins:
        log.warning(
            "CORS_ALLOWED_ORIGINS is empty; browser CORS preflights will fail. "
            "Set this to your production web origin(s) before exposing the API."
        )
        return
    if any(o.strip() == "*" for o in origins):
        raise RuntimeError(
            "Refusing to start in live mode with CORS_ALLOWED_ORIGINS='*'. "
            "Set explicit origins (e.g. https://app.example.com)."
        )


def warn_startup_profile() -> None:
    if not is_cloud_profile():
        log.info(
            "Koraku SDK HTTP server (no Supabase product routes). "
            "Run koraku_cloud.app for Koraku Cloud.",
        )
        return
    try:
        from koraku_cloud.integrations.supabase_tenant import supabase_tenant_configured
    except ImportError:
        log.warning(
            "koraku_cloud is not installed — Cloud product routes require the monorepo or koraku-cloud package."
        )
        return
    if not supabase_tenant_configured():
        log.warning(
            "Supabase tenant storage is not configured (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY). "
            "Chat and personalization require a signed-in user with an organization."
        )
    if settings.default_execution_target == "cloud" and not settings.blaxel_cloud_sandbox_enabled:
        log.warning(
            "Cloud execution is enabled but BLAXEL_CLOUD_SANDBOX_ENABLED is false — "
            "file/shell tools on cloud runs need Blaxel or use execution_target=local."
        )


def run_startup_checks() -> None:
    assert_workspace_safe()
    agent, mode = resolve_server_mode()
    assert_cors_safe(mode)
    warn_startup_profile()
    assert_redis_for_multi_worker()
    return agent, mode


def make_lifespan(
    agent: Agent | None,
    mode: str,
    *,
    enable_automation_scheduler: bool,
) -> Callable[[FastAPI], AsyncIterator[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.koraku_agent = agent
        app.state.server_mode = mode
        log.info("%s v%s starting up in %s mode", settings.agent_name, settings.version, mode)
        if mode == "unconfigured":
            log.warning(
                "LLM is not configured. Set API keys / base URL (see /health). "
                "SSE will return setup instructions."
            )
        else:
            log.info("LLM provider: %s", settings.llm_provider)
            if settings.llm_provider == "fireworks":
                log.info("LLM model: %s", settings.fireworks_model)
            elif settings.llm_provider == "anthropic":
                log.info("LLM model: %s", settings.anthropic_model)
            else:
                log.info("LLM model: %s", default_model_for_provider(settings.llm_provider))
            log.info(
                "Max steps standard: %d | extended: %d",
                settings.max_steps,
                settings.research_max_steps,
            )
            if settings.exa_api_key:
                log.info("ExaSearch enabled")
            if settings.firecrawl_api_key:
                log.info("Firecrawl enabled")
            if settings.blaxel_cloud_sandbox_enabled:
                import sys

                from koraku.integrations import blaxel_runtime as _blaxel_rt

                if not _blaxel_rt.blaxel_sdk_available():
                    err = _blaxel_rt.blaxel_import_error_message() or "unknown"
                    log.warning(
                        "BLAXEL_CLOUD_SANDBOX_ENABLED=true but `blaxel` is not importable. "
                        "sys.executable=%s import_error=%s",
                        sys.executable,
                        err,
                    )
                else:
                    log.info("Blaxel (cloud sandboxes) enabled")
        if enable_automation_scheduler:
            from koraku_cloud.automations import scheduler as automation_scheduler

            automation_scheduler.configure_automation_scheduler(agent)
            if agent is not None:
                automation_scheduler.start_automation_scheduler()
        if enable_automation_scheduler:
            try:
                from koraku_cloud.integrations.composio_webhooks import (
                    ensure_project_webhook_subscription,
                )

                await asyncio.to_thread(ensure_project_webhook_subscription)
            except Exception:
                log.exception("Composio webhook subscription setup failed")
        try:
            yield
        finally:
            if enable_automation_scheduler:
                from koraku_cloud.automations import scheduler as automation_scheduler

                automation_scheduler.shutdown_automation_scheduler()
            log.info("Shutting down")

    return lifespan


def attach_common_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.middleware("http")
    async def body_size_limit_middleware(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            cl = request.headers.get("content-length")
            if cl:
                try:
                    size = int(cl)
                except ValueError:
                    return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
                if size > settings.max_request_body_bytes:
                    return JSONResponse(
                        {
                            "detail": (
                                f"Request body exceeds {settings.max_request_body_bytes} bytes."
                            )
                        },
                        status_code=413,
                    )
        return await call_next(request)

    origins = settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def attach_index_route(app: FastAPI, *, variant: str) -> None:
    @app.get("/")
    async def index() -> dict[str, Any]:
        if variant == "cloud":
            ui = "Run the Next.js app from the web/ directory for the browser UI."
        else:
            ui = "Embed via Koraku Python SDK or POST /stream from your own UI."
        return {
            "service": settings.agent_name,
            "version": settings.version,
            "runtime": "cloud" if is_cloud_profile() else "sdk",
            "health": "/health",
            "ui": ui,
        }
