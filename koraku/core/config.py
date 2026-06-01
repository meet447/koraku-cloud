"""Configuration and settings for the agent."""
from __future__ import annotations

import contextvars
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PACKAGE_DIR.parent

_default_settings: Settings | None = None
_settings_override: contextvars.ContextVar[Settings | None] = contextvars.ContextVar(
    "koraku_settings",
    default=None,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        # Prefer repo-root ``.env`` so the backend picks up keys even when cwd is not the project root.
        env_file=(str(_REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    # Comma-separated browser origins allowed to call the Python API directly.
    # In production, prefer routing browsers through the Next.js BFF and keep this list tight.
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "cors_allowed_origins"),
    )
    # Trusted reverse-proxy CIDRs whose X-Forwarded-For header we honor. When empty
    # (default) we ignore XFF and use the direct connection IP — preventing rate-limit
    # bypass via spoofed XFF when the API is exposed without a known proxy in front.
    trusted_proxy_cidrs: str = Field(
        default="",
        validation_alias=AliasChoices("TRUSTED_PROXY_CIDRS", "trusted_proxy_cidrs"),
    )
    # Reject requests whose advertised Content-Length exceeds this cap before any
    # handler runs. Chat /stream allows 8 images × 14MB + ~400KB text by default —
    # a default cap of 16MB rejects degenerate multi-image bursts that would
    # otherwise let a single request balloon to ~112MB.
    max_request_body_bytes: int = Field(
        default=16 * 1024 * 1024,
        validation_alias=AliasChoices("MAX_REQUEST_BODY_BYTES", "max_request_body_bytes"),
    )
    # Local or hosted Redis (``redis://localhost:6379/0``). Sessions + rate limits when
    # ``SESSION_STORE_BACKEND=redis``. Same URL as the Next.js app (``REDIS_URL``).
    redis_url: str = Field(
        default="",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    # Chat and agent routes require a signed-in Supabase user (override via ``configure()`` in tests only).
    require_auth_for_chat: bool = Field(
        default=True,
        validation_alias=AliasChoices("__koraku_require_auth_for_chat"),
    )
    # Auth backend: ``supabase`` (JWT) or ``api_key`` (service bearer for automation hooks).
    auth_backend: str = Field(
        default="supabase",
        validation_alias=AliasChoices("AUTH_BACKEND", "KORAKU_AUTH_BACKEND", "auth_backend"),
    )
    koraku_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("KORAKU_API_KEY", "koraku_api_key"),
    )
    # Chat session persistence: ``memory`` (single worker) or ``redis`` (requires ``REDIS_URL``).
    session_store_backend: str = Field(
        default="redis",
        validation_alias=AliasChoices(
            "SESSION_STORE_BACKEND",
            "KORAKU_SESSION_STORE",
            "session_store_backend",
        ),
    )
    # Detached runs: ``memory`` (single worker), ``redis`` (multi-worker), or ``auto`` (redis when REDIS_URL works).
    detached_run_store_backend: str = Field(
        default="auto",
        validation_alias=AliasChoices(
            "DETACHED_RUN_STORE_BACKEND",
            "detached_run_store_backend",
        ),
    )
    chat_rate_limit_per_minute: int = Field(
        default=12,
        validation_alias=AliasChoices("CHAT_RATE_LIMIT_PER_MINUTE", "chat_rate_limit_per_minute"),
    )
    automation_rate_limit_per_minute: int = Field(
        default=6,
        validation_alias=AliasChoices("AUTOMATION_RATE_LIMIT_PER_MINUTE", "automation_rate_limit_per_minute"),
    )
    automation_manual_run_concurrency_per_user: int = Field(
        default=1,
        validation_alias=AliasChoices(
            "AUTOMATION_MANUAL_RUN_CONCURRENCY_PER_USER",
            "automation_manual_run_concurrency_per_user",
        ),
    )
    # While the model is thinking, emit SSE comment lines so proxies/browsers do not close the stream.
    sse_keepalive_seconds: float = 12.0
    # In-memory chat sessions (/stream): drop after idle TTL; cap total sessions to limit RAM.
    session_ttl_hours: float = 168.0
    session_store_max: int = 2000
    # Backpressure / memory caps for long-running SSE agent work.
    agent_concurrency_limit: int = 8
    tool_concurrency_limit: int = 16
    # Interactive chat: wall-clock caps so one turn cannot block workers indefinitely (Phase A reliability).
    agent_llm_stream_timeout_seconds: float = Field(
        default=180.0,
        validation_alias=AliasChoices(
            "AGENT_LLM_STREAM_TIMEOUT_SECONDS",
            "agent_llm_stream_timeout_seconds",
        ),
    )
    agent_tool_phase_timeout_seconds: float = Field(
        default=240.0,
        validation_alias=AliasChoices(
            "AGENT_TOOL_PHASE_TIMEOUT_SECONDS",
            "agent_tool_phase_timeout_seconds",
        ),
    )
    detached_run_subscriber_queue_max: int = 256
    # Keep host file tools inside the server workspace. Cloud tools already run inside Blaxel.
    host_file_tools_restrict_to_workspace: bool = True
    # When True, each LLM call sees user text + assistant visible replies only (tool_use /
    # tool_result pairs from past turns are omitted) to save tokens. Set CHAT_COMPACT_TOOL_CONTEXT=false
    # to send full ReAct traces to the model.
    chat_compact_tool_context: bool = Field(
        default=True,
        validation_alias=AliasChoices("CHAT_COMPACT_TOOL_CONTEXT", "chat_compact_tool_context"),
    )

    # LLM provider: "anthropic" | "fireworks" | named OpenAI-compatible ids (see LLM_OPENAI_COMPAT_IDS)
    llm_provider: str = "fireworks"

    # Anthropic Claude
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Comma-separated model IDs for the chat UI (optional; defaults to built-in lists per provider)
    chat_model_options: str = ""

    # Fireworks AI (high-quality hosted models)
    fireworks_api_key: str = os.environ.get("FIREWORKS_API_KEY", "")
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"
    fireworks_model: str = "accounts/fireworks/models/kimi-k2p6"

    # Comma-separated ids for OpenAI-compatible providers (openai, groq, custom, …)
    # Unset + CUSTOM_BASE_URL auto-registers provider id ``custom`` (CUSTOM_* env vars).
    llm_openai_compat_ids: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_OPENAI_COMPAT_IDS", "llm_openai_compat_ids"),
    )
    # Optional JSON list: [{"id":"groq","label":"Groq","base_url":"...","api_key":"...","default_model":"...","models":[...]}]
    llm_openai_compat_json: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_OPENAI_COMPAT_JSON", "llm_openai_compat_json"),
    )

    # Shared LLM settings
    # Transient errors (429, 502, 503, …): retry POST / stream open with exponential backoff.
    llm_max_retries: int = 5
    llm_retry_base_seconds: float = 1.5
    max_tokens: int = 4096
    max_steps: int = 15
    research_max_steps: int = 100
    # Per tool_result string cap when building the next LLM request (saves tokens; raise for verbose Composio/API JSON).
    max_tool_result_chars: int = 48_000
    temperature: float = 0.5
    top_p: float = 0.85
    top_k: int = 20

    # Premium tools (read without AGENT_ prefix since these are external services)
    exa_api_key: str = os.environ.get("EXA_API_KEY", os.environ.get("AGENT_EXA_API_KEY", ""))
    firecrawl_api_key: str = os.environ.get("FIRECRAWL_API_KEY", os.environ.get("AGENT_FIRECRAWL_API_KEY", ""))

    # Composio (Gmail, Google Drive, Slack, …) — OAuth connections / integrations
    composio_api_key: str = ""
    # Fallback Composio entity id when no signed-in user (JWT) is present (dev / scripts only).
    composio_user_id: str = "koraku-local"
    # Max Composio tool definitions per agent run, split evenly across active connected toolkits
    # (so Gmail cannot consume the whole budget and hide Google Calendar, etc.).
    composio_tools_limit: int = 48
    # When True (default), the chat agent uses **ComposioRun** to spawn a scoped sub-run per toolkit
    # instead of loading all Composio tools on the main agent (toolkit-scoped ComposioRun sub-agent).
    composio_subagent_mode: bool = True
    # Step cap for each ComposioRun inner loop (separate from chat max_steps).
    composio_subagent_max_steps: int = 20
    # Supabase JWT secret (Settings → API) so the backend can verify browser access tokens for
    # per-user Composio linking and tool execution.
    supabase_jwt_secret: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_JWT_SECRET", "supabase_jwt_secret"),
    )
    # PostgREST for ``koraku_automation`` tables (Python API + scheduler). Use the service role key
    # only on the backend; never expose it to the browser.
    supabase_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SUPABASE_URL",
            "NEXT_PUBLIC_SUPABASE_URL",
            "supabase_url",
        ),
    )
    supabase_service_role_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_SECRET_KEY",
            "supabase_service_role_key",
        ),
    )

    # Supermemory — learned facts across chats (explicit name/soul/preferences stay in Supabase).
    supermemory_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPERMEMORY_API_KEY", "supermemory_api_key"),
    )
    supermemory_context_max_chars: int = Field(
        default=6_000,
        validation_alias=AliasChoices(
            "SUPERMEMORY_CONTEXT_MAX_CHARS",
            "supermemory_context_max_chars",
        ),
    )
    # Chat turn startup: cache slow Supabase / Supermemory lookups (seconds).
    personalization_cache_ttl_seconds: float = Field(
        default=300.0,
        validation_alias=AliasChoices(
            "PERSONALIZATION_CACHE_TTL_SECONDS",
            "personalization_cache_ttl_seconds",
        ),
    )
    learned_memory_cache_ttl_seconds: float = Field(
        default=90.0,
        validation_alias=AliasChoices(
            "LEARNED_MEMORY_CACHE_TTL_SECONDS",
            "learned_memory_cache_ttl_seconds",
        ),
    )
    # Max wait for Supermemory before starting the agent (empty context if slower).
    chat_learned_memory_timeout_seconds: float = Field(
        default=4.0,
        validation_alias=AliasChoices(
            "CHAT_LEARNED_MEMORY_TIMEOUT_SECONDS",
            "chat_learned_memory_timeout_seconds",
        ),
    )
    tenant_org_membership_cache_ttl_seconds: float = Field(
        default=120.0,
        validation_alias=AliasChoices(
            "TENANT_ORG_MEMBERSHIP_CACHE_TTL_SECONDS",
            "tenant_org_membership_cache_ttl_seconds",
        ),
    )

    @field_validator("supabase_jwt_secret", mode="before")
    @classmethod
    def _strip_supabase_jwt_secret(cls, v: object) -> str:
        """Allow quoted values in ``.env`` without quotes becoming part of the secret."""
        if v is None:
            return ""
        s = str(v).strip()
        if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
            s = s[1:-1].strip()
        return s

    # Tools
    enable_bash: bool = True
    enable_web_search: bool = True
    enable_web_fetch: bool = True
    enable_file_ops: bool = True

    # Web
    web_timeout: int = 15
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"

    # Agent identity
    agent_name: str = "koraku-agent"
    version: str = "1.0.0"

    # Saved automations (scheduler + headless agent runs)
    # Set to false on worker-only processes when exactly one leader runs the cron scheduler.
    automation_scheduler_enabled: bool = True
    # How often the leader re-syncs scheduled jobs from Supabase (multi-worker).
    automation_scheduler_resync_seconds: int = 60
    # Tighter cap than chat for scheduled / manual automation runs (cost + safety).
    automation_max_steps: int = 12
    # Wall-clock cap for one automation agent run (LLM + tools).
    automation_run_timeout_seconds: float = 180.0

    # Blaxel sandboxes for chat ``execution_target=cloud`` (isolated file + shell tools).
    # When enabled with BL_WORKSPACE + BL_API_KEY set, each cloud chat session gets a VM; Bash
    # and file tools run there. When disabled or keys missing, cloud chat is refused (no host fallback).
    blaxel_cloud_sandbox_enabled: bool = False
    bl_workspace: str = Field(default="", validation_alias=AliasChoices("BL_WORKSPACE", "bl_workspace"))
    bl_api_key: str = Field(default="", validation_alias=AliasChoices("BL_API_KEY", "bl_api_key"))
    blaxel_sandbox_image: str = "blaxel/base-image:latest"
    blaxel_sandbox_region: str = "us-pdx-1"
    blaxel_sandbox_memory_mb: int = 512
    # Blaxel VM images may not ship ``/home/user``; ``/tmp`` exists on typical Linux sandboxes.
    blaxel_sandbox_workdir: str = "/tmp"
    # Wall-clock cap for Blaxel ``create_if_not_exists`` per chat turn (first bytes still flush via preamble).
    blaxel_sandbox_ready_timeout_seconds: float = 120.0
    # Reuse a warm Blaxel VM handle for this many seconds (per user) between chat turns.
    blaxel_sandbox_cache_ttl_seconds: float = Field(
        default=600.0,
        validation_alias=AliasChoices(
            "BLAXEL_SANDBOX_CACHE_TTL_SECONDS",
            "blaxel_sandbox_cache_ttl_seconds",
        ),
    )
    # Short conversational turns skip upfront sandbox provisioning (tools provision lazily).
    chat_defer_blaxel_provision: bool = Field(
        default=True,
        validation_alias=AliasChoices("CHAT_DEFER_BLAXEL_PROVISION", "chat_defer_blaxel_provision"),
    )
    # Max ReAct steps for very short prompts (e.g. greetings) without research markers.
    chat_quick_max_steps: int = Field(
        default=4,
        validation_alias=AliasChoices("CHAT_QUICK_MAX_STEPS", "chat_quick_max_steps"),
    )

    @field_validator("bl_workspace", "bl_api_key", mode="before")
    @classmethod
    def _strip_blaxel_credentials(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @property
    def cors_origins_list(self) -> list[str]:
        raw = (self.cors_allowed_origins or "").strip()
        if not raw:
            return []
        return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]

    @property
    def trusted_proxy_cidrs_list(self) -> list[str]:
        raw = (self.trusted_proxy_cidrs or "").strip()
        if not raw:
            return []
        return [c.strip() for c in raw.split(",") if c.strip()]

    def model_post_init(self, __context: Any) -> None:
        """The Blaxel SDK authenticates from ``os.environ`` (or ``~/.blaxel/config``), not Pydantic's in-memory merge."""
        key = (self.bl_api_key or "").strip()
        ws = (self.bl_workspace or "").strip()
        if key:
            os.environ["BL_API_KEY"] = key
        if ws:
            os.environ["BL_WORKSPACE"] = ws


def get_settings() -> Settings:
    """Return active settings (override context, else process default)."""
    override = _settings_override.get()
    if override is not None:
        return override
    global _default_settings
    if _default_settings is None:
        loaded = Settings()
        if not loaded.require_auth_for_chat:
            loaded = loaded.model_copy(update={"require_auth_for_chat": True})
        _default_settings = loaded
    return _default_settings


class _SettingsProxy:
    """Backward-compatible module-level ``settings`` that respects ``configure()`` / ``use_settings()``."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        return repr(get_settings())


settings = _SettingsProxy()


def configure(settings_obj: Settings | None = None, **kwargs: Any) -> Settings:
    """Set process-wide default settings (SDK embed entry point)."""
    global _default_settings
    if settings_obj is not None:
        _default_settings = settings_obj
    elif kwargs:
        _default_settings = get_settings().model_copy(update=kwargs)
    else:
        _default_settings = Settings()
    return _default_settings


@contextmanager
def use_settings(settings_obj: Settings) -> Iterator[Settings]:
    """Temporarily bind settings for the current async/task context."""
    token = _settings_override.set(settings_obj)
    try:
        yield settings_obj
    finally:
        _settings_override.reset(token)
