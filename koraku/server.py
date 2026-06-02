"""FastAPI application: lifespan and included API routers."""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from koraku.core.config import settings
from koraku.agent import Agent
from koraku.api.automations_routes import router as automations_router
from koraku.api.chat_routes import router as chat_router
from koraku.api.detached_runs import router as detached_runs_router
from koraku.api.composio_routes import router as composio_router
from koraku.api.health_routes import router as health_router
from koraku.api.memory_routes import router as memory_router
from koraku.api.personalization_routes import router as personalization_router
from koraku.api.workspace_routes import router as workspace_router
from koraku.api.sendblue_routes import router as sendblue_router
from koraku.automations import scheduler as automation_scheduler
from koraku.integrations.supabase_tenant import supabase_tenant_configured
from koraku.core.startup_checks import assert_redis_for_multi_worker
from koraku.llm.catalog import any_llm_configured, default_model_for_provider
from koraku.workspace.paths import workspace_dir

log = logging.getLogger(__name__)

if any_llm_configured():
    _default_agent: Agent | None = Agent()
    MODE = "live"
else:
    _default_agent = None
    MODE = "unconfigured"


def _assert_workspace_safe() -> None:
    ws = workspace_dir()
    if ws == "/" or ws == "":
        raise RuntimeError(
            "Refusing to start: workspace_dir() resolved to filesystem root. "
            "Run Koraku from a project directory, not /."
        )


def _assert_cors_safe() -> None:
    if MODE != "live":
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


def _warn_tenant_storage() -> None:
    if not supabase_tenant_configured():
        log.warning(
            "Supabase tenant storage is not configured (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY). "
            "Chat and personalization require a signed-in user with an organization."
        )
    if not settings.blaxel_cloud_sandbox_enabled:
        log.warning(
            "BLAXEL_CLOUD_SANDBOX_ENABLED is false — chat tool execution will be blocked until Blaxel is configured."
        )


_assert_workspace_safe()
_assert_cors_safe()
_warn_tenant_storage()
assert_redis_for_multi_worker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    app.state.koraku_agent = _default_agent
    app.state.server_mode = MODE
    log.info("%s v%s starting up in %s mode", settings.agent_name, settings.version, MODE)
    if MODE == "unconfigured":
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
                    "BLAXEL_CLOUD_SANDBOX_ENABLED=true but `blaxel` is not importable in this worker. "
                    "sys.executable=%s import_error=%s install_with=%s -m pip install blaxel",
                    sys.executable,
                    err,
                    sys.executable,
                )
            else:
                log.info("Blaxel (cloud sandboxes) enabled")
    automation_scheduler.configure_automation_scheduler(_default_agent)
    if _default_agent is not None:
        automation_scheduler.start_automation_scheduler()
    yield
    automation_scheduler.shutdown_automation_scheduler()
    log.info("Shutting down")


app = FastAPI(title=settings.agent_name, version=settings.version, lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a request id so support can correlate browser, API, and provider logs."""
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next):
    """Reject body-bearing requests whose Content-Length exceeds the configured cap."""
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


_cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(detached_runs_router)
app.include_router(personalization_router)
app.include_router(memory_router)
app.include_router(composio_router)
app.include_router(automations_router)
app.include_router(workspace_router)
app.include_router(sendblue_router)


@app.get("/")
async def index():
    """API root; the chat UI lives in ``web/`` (Next.js)."""
    return {
        "service": settings.agent_name,
        "version": settings.version,
        "health": "/health",
        "ui": "Run the Next.js app from the web/ directory for the browser UI.",
    }
