"""Cloud-shaped settings schema (SDK wheel + ``koraku_cloud`` re-export).

Edit fields here; ``koraku_cloud.cloud_settings`` imports this module.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _strip_env_str(v: object, *, strip_quotes: bool = False) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if strip_quotes and len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


class CloudSettings(BaseSettings):
    """Product-layer settings schema; defaults are SDK-safe when Cloud is not bound."""

    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    redis_url: str = Field(
        default="",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    require_auth_for_chat: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "REQUIRE_AUTH_FOR_CHAT",
            "__koraku_require_auth_for_chat",
        ),
    )
    default_execution_target: str = Field(
        default="cloud",
        validation_alias=AliasChoices("DEFAULT_EXECUTION_TARGET", "default_execution_target"),
    )
    memory_backend: str = Field(
        default="composite",
        validation_alias=AliasChoices("MEMORY_BACKEND", "memory_backend"),
    )
    auth_backend: str = Field(
        default="supabase",
        validation_alias=AliasChoices("AUTH_BACKEND", "KORAKU_AUTH_BACKEND", "auth_backend"),
    )
    koraku_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("KORAKU_API_KEY", "koraku_api_key"),
    )
    health_detail_token: str = Field(
        default="",
        validation_alias=AliasChoices("HEALTH_DETAIL_TOKEN", "health_detail_token"),
    )
    session_store_backend: str = Field(
        default="redis",
        validation_alias=AliasChoices(
            "SESSION_STORE_BACKEND",
            "KORAKU_SESSION_STORE",
            "session_store_backend",
        ),
    )
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
    credits_free_monthly_limit: int = Field(
        default=100_000,
        validation_alias=AliasChoices(
            "CREDITS_FREE_MONTHLY_LIMIT",
            "credits_free_monthly_limit",
        ),
    )
    credits_min_reserve: int = Field(
        default=500,
        validation_alias=AliasChoices("CREDITS_MIN_RESERVE", "credits_min_reserve"),
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

    supabase_jwt_secret: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_JWT_SECRET", "supabase_jwt_secret"),
    )
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

    automation_scheduler_enabled: bool = True
    automation_scheduler_resync_seconds: int = 60
    automation_max_steps: int = 12
    automation_run_timeout_seconds: float = 180.0

    blaxel_cloud_sandbox_enabled: bool = False
    bl_workspace: str = Field(default="", validation_alias=AliasChoices("BL_WORKSPACE", "bl_workspace"))
    bl_api_key: str = Field(default="", validation_alias=AliasChoices("BL_API_KEY", "bl_api_key"))
    blaxel_sandbox_image: str = "blaxel/base-image:latest"
    blaxel_sandbox_region: str = "us-pdx-1"
    blaxel_sandbox_memory_mb: int = 512
    blaxel_sandbox_workdir: str = "/tmp"
    blaxel_sandbox_ready_timeout_seconds: float = 120.0
    blaxel_sandbox_cache_ttl_seconds: float = Field(
        default=600.0,
        validation_alias=AliasChoices(
            "BLAXEL_SANDBOX_CACHE_TTL_SECONDS",
            "blaxel_sandbox_cache_ttl_seconds",
        ),
    )

    sendblue_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("SENDBLUE_API_KEY", "sendblue_api_key"),
    )
    sendblue_api_secret: str = Field(
        default="",
        validation_alias=AliasChoices("SENDBLUE_API_SECRET", "sendblue_api_secret"),
    )
    sendblue_from_number: str = Field(
        default="",
        validation_alias=AliasChoices("SENDBLUE_FROM_NUMBER", "sendblue_from_number"),
    )
    sendblue_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices("SENDBLUE_WEBHOOK_SECRET", "sendblue_webhook_secret"),
    )
    sendblue_api_base: str = Field(
        default="https://api.sendblue.co/api",
        validation_alias=AliasChoices("SENDBLUE_API_BASE", "sendblue_api_base"),
    )
    sendblue_inbound_media_host_allowlist: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SENDBLUE_INBOUND_MEDIA_HOST_ALLOWLIST",
            "sendblue_inbound_media_host_allowlist",
        ),
    )
    imessage_voice_transcription_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "IMESSAGE_VOICE_TRANSCRIPTION_ENABLED",
            "imessage_voice_transcription_enabled",
        ),
    )
    voice_transcription_base_url: str = Field(
        default="https://audio-prod.api.fireworks.ai/v1",
        validation_alias=AliasChoices("VOICE_TRANSCRIPTION_BASE_URL", "voice_transcription_base_url"),
    )
    voice_transcription_model: str = Field(
        default="whisper-large-v3",
        validation_alias=AliasChoices("VOICE_TRANSCRIPTION_MODEL", "voice_transcription_model"),
    )
    koraku_public_api_url: str = Field(
        default="",
        validation_alias=AliasChoices("KORAKU_PUBLIC_API_URL", "koraku_public_api_url"),
    )
    composio_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices("COMPOSIO_WEBHOOK_SECRET", "composio_webhook_secret"),
    )
    composio_webhook_auto_setup: bool = Field(
        default=False,
        validation_alias=AliasChoices("COMPOSIO_WEBHOOK_AUTO_SETUP", "composio_webhook_auto_setup"),
    )
    chat_defer_blaxel_provision: bool = Field(
        default=True,
        validation_alias=AliasChoices("CHAT_DEFER_BLAXEL_PROVISION", "chat_defer_blaxel_provision"),
    )

    @field_validator("supabase_jwt_secret", mode="before")
    @classmethod
    def _strip_supabase_jwt_secret(cls, v: object) -> str:
        return _strip_env_str(v, strip_quotes=True)

    @field_validator("bl_workspace", "bl_api_key", mode="before")
    @classmethod
    def _strip_blaxel_credentials(cls, v: object) -> str:
        return _strip_env_str(v)

    def model_post_init(self, __context: Any) -> None:
        key = (self.bl_api_key or "").strip()
        ws = (self.bl_workspace or "").strip()
        if key:
            os.environ["BL_API_KEY"] = key
        if ws:
            os.environ["BL_WORKSPACE"] = ws


def inert_cloud_settings() -> CloudSettings:
    """Safe defaults when only the SDK layer is active (no product package)."""
    return CloudSettings.model_construct(
        require_auth_for_chat=False,
        auth_backend="none",
        default_execution_target="local",
        memory_backend="filesystem",
        session_store_backend="memory",
        detached_run_store_backend="memory",
        blaxel_cloud_sandbox_enabled=False,
    )
