"""Embeddable Koraku SDK settings (agent, LLM, tools) — no Cloud product secrets."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PACKAGE_DIR.parent


class SdkSettings(BaseSettings):
    """SDK / agent configuration. Safe to ship on PyPI; no Supabase or Blaxel product keys."""

    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = "127.0.0.1"
    port: int = 8000
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "cors_allowed_origins"),
    )
    trusted_proxy_cidrs: str = Field(
        default="",
        validation_alias=AliasChoices("TRUSTED_PROXY_CIDRS", "trusted_proxy_cidrs"),
    )
    max_request_body_bytes: int = Field(
        default=16 * 1024 * 1024,
        validation_alias=AliasChoices("MAX_REQUEST_BODY_BYTES", "max_request_body_bytes"),
    )

    default_execution_target: str = Field(
        default="local",
        validation_alias=AliasChoices("DEFAULT_EXECUTION_TARGET", "default_execution_target"),
    )
    memory_backend: str = Field(
        default="filesystem",
        validation_alias=AliasChoices("MEMORY_BACKEND", "memory_backend"),
    )
    session_store_backend: str = Field(
        default="memory",
        validation_alias=AliasChoices(
            "SESSION_STORE_BACKEND",
            "KORAKU_SESSION_STORE",
            "session_store_backend",
        ),
    )
    detached_run_store_backend: str = Field(
        default="memory",
        validation_alias=AliasChoices(
            "DETACHED_RUN_STORE_BACKEND",
            "detached_run_store_backend",
        ),
    )

    sse_keepalive_seconds: float = 12.0
    session_ttl_hours: float = 168.0
    session_store_max: int = 2000
    agent_concurrency_limit: int = 8
    tool_concurrency_limit: int = 16
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
    host_file_tools_restrict_to_workspace: bool = True
    chat_compact_tool_context: bool = Field(
        default=True,
        validation_alias=AliasChoices("CHAT_COMPACT_TOOL_CONTEXT", "chat_compact_tool_context"),
    )
    chat_openai_native_tools: bool = Field(
        default=True,
        validation_alias=AliasChoices("CHAT_OPENAI_NATIVE_TOOLS", "chat_openai_native_tools"),
    )

    llm_provider: str = "fireworks"
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    chat_model_options: str = ""
    fireworks_api_key: str = os.environ.get("FIREWORKS_API_KEY", "")
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"
    fireworks_model: str = "accounts/fireworks/models/kimi-k2p6"
    llm_openai_compat_ids: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_OPENAI_COMPAT_IDS", "llm_openai_compat_ids"),
    )
    llm_openai_compat_json: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_OPENAI_COMPAT_JSON", "llm_openai_compat_json"),
    )

    llm_max_retries: int = 5
    llm_retry_base_seconds: float = 1.5
    max_tokens: int = 4096
    max_steps: int = 15
    research_max_steps: int = 100
    chat_turn_wall_seconds_standard: float = Field(
        default=180.0,
        validation_alias=AliasChoices("CHAT_TURN_WALL_SECONDS_STANDARD", "chat_turn_wall_seconds_standard"),
    )
    chat_turn_wall_seconds_quick: float = Field(
        default=75.0,
        validation_alias=AliasChoices("CHAT_TURN_WALL_SECONDS_QUICK", "chat_turn_wall_seconds_quick"),
    )
    chat_turn_wall_seconds_integration: float = Field(
        default=120.0,
        validation_alias=AliasChoices(
            "CHAT_TURN_WALL_SECONDS_INTEGRATION",
            "chat_turn_wall_seconds_integration",
        ),
    )
    chat_turn_wall_seconds_research: float = Field(
        default=600.0,
        validation_alias=AliasChoices("CHAT_TURN_WALL_SECONDS_RESEARCH", "chat_turn_wall_seconds_research"),
    )
    chat_max_rounds_standard: int = Field(
        default=32,
        validation_alias=AliasChoices("CHAT_MAX_ROUNDS_STANDARD", "chat_max_rounds_standard"),
    )
    chat_max_rounds_integration: int = Field(
        default=18,
        validation_alias=AliasChoices("CHAT_MAX_ROUNDS_INTEGRATION", "chat_max_rounds_integration"),
    )
    agent_loop_warn_round_fraction: float = Field(
        default=0.85,
        validation_alias=AliasChoices("AGENT_LOOP_WARN_ROUND_FRACTION", "agent_loop_warn_round_fraction"),
    )
    chat_prefetch_learned_memory: bool = Field(
        default=True,
        validation_alias=AliasChoices("CHAT_PREFETCH_LEARNED_MEMORY", "chat_prefetch_learned_memory"),
    )
    agent_worker_heartbeat_seconds: float = Field(
        default=10.0,
        validation_alias=AliasChoices("AGENT_WORKER_HEARTBEAT_SECONDS", "agent_worker_heartbeat_seconds"),
    )
    agent_llm_stream_heartbeat_seconds: float = Field(
        default=12.0,
        validation_alias=AliasChoices("AGENT_LLM_STREAM_HEARTBEAT_SECONDS", "agent_llm_stream_heartbeat_seconds"),
    )
    max_tool_result_chars: int = 48_000
    temperature: float = 0.5
    top_p: float = 0.85
    top_k: int = 20

    exa_api_key: str = os.environ.get("EXA_API_KEY", os.environ.get("AGENT_EXA_API_KEY", ""))
    firecrawl_api_key: str = os.environ.get("FIRECRAWL_API_KEY", os.environ.get("AGENT_FIRECRAWL_API_KEY", ""))

    composio_api_key: str = ""
    composio_user_id: str = "koraku-local"
    composio_tools_limit: int = 48
    composio_subagent_mode: bool = True
    koraku_dispatcher_mode: bool = Field(
        default=True,
        validation_alias=AliasChoices("KORAKU_DISPATCHER_MODE", "koraku_dispatcher_mode"),
    )
    composio_subagent_max_steps: int = 16
    composio_subagent_max_steps_simple: int = Field(
        default=6,
        validation_alias=AliasChoices("COMPOSIO_SUBAGENT_MAX_STEPS_SIMPLE", "composio_subagent_max_steps_simple"),
    )
    composio_subagent_max_steps_compose: int = Field(
        default=10,
        validation_alias=AliasChoices("COMPOSIO_SUBAGENT_MAX_STEPS_COMPOSE", "composio_subagent_max_steps_compose"),
    )
    composio_subagent_wall_seconds: float = Field(
        default=150.0,
        validation_alias=AliasChoices("COMPOSIO_SUBAGENT_WALL_SECONDS", "composio_subagent_wall_seconds"),
    )
    composio_subagent_wall_seconds_simple: float = Field(
        default=90.0,
        validation_alias=AliasChoices(
            "COMPOSIO_SUBAGENT_WALL_SECONDS_SIMPLE",
            "composio_subagent_wall_seconds_simple",
        ),
    )
    composio_subagent_wall_seconds_compose: float = Field(
        default=120.0,
        validation_alias=AliasChoices(
            "COMPOSIO_SUBAGENT_WALL_SECONDS_COMPOSE",
            "composio_subagent_wall_seconds_compose",
        ),
    )

    enable_bash: bool = True
    enable_web_search: bool = True
    enable_web_fetch: bool = True
    enable_file_ops: bool = True
    web_timeout: int = 15
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )

    agent_name: str = "koraku-agent"
    version: str = "1.0.0"
    chat_quick_max_steps: int = Field(
        default=4,
        validation_alias=AliasChoices("CHAT_QUICK_MAX_STEPS", "chat_quick_max_steps"),
    )

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
