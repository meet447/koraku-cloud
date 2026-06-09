"""Minimal Koraku HTTP server for embedders (no Supabase product routes)."""
from __future__ import annotations

from fastapi import FastAPI

from koraku.api.chat_routes import router as chat_router
from koraku.api.composio_routes import router as composio_router
from koraku.api.health_routes import router as health_router
from koraku.core.config import settings
from koraku.server_core import (
    attach_common_middleware,
    attach_index_route,
    make_lifespan,
    run_startup_checks,
)

from typing import Any

_AGENT_VAL: Any = None
_MODE_VAL: str | None = None


def _resolve_lazy_checks() -> tuple[Any, str]:
    global _AGENT_VAL, _MODE_VAL
    if _MODE_VAL is None:
        _AGENT_VAL, _MODE_VAL = run_startup_checks()
    return _AGENT_VAL, _MODE_VAL


def __getattr__(name: str) -> Any:
    if name in {"_AGENT", "_MODE"}:
        agent, mode = _resolve_lazy_checks()
        if name == "_AGENT":
            return agent
        return mode
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def create_sdk_app(
    *,
    enable_automation_scheduler: bool = False,
    index_variant: str = "sdk",
) -> FastAPI:
    """FastAPI app: health, chat stream, optional Composio proxy routes."""
    app = FastAPI(
        title=f"{settings.agent_name} (SDK)" if index_variant == "sdk" else settings.agent_name,
        version=settings.version,
        lifespan=make_lifespan(
            enable_automation_scheduler=enable_automation_scheduler,
        ),
    )
    attach_common_middleware(app)
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(composio_router)
    attach_index_route(app, variant=index_variant)
    return app


app = create_sdk_app()
