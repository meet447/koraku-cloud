"""Runtime settings: SDK layer + optional Cloud product layer (monorepo)."""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Any, Iterator

from koraku.core.sdk_settings import SdkSettings

_default_sdk: SdkSettings | None = None
_cloud_bound: bool = False
_cloud_settings: Any = None
_inert_cloud: Any = None
_settings_override: contextvars.ContextVar[Any] = contextvars.ContextVar(
    "koraku_settings",
    default=None,
)
_default_merged: _MergedSettings | None = None

_CLOUD_OVERRIDE_FIELDS = frozenset(
    {
        "default_execution_target",
        "memory_backend",
        "session_store_backend",
        "detached_run_store_backend",
        "require_auth_for_chat",
        "auth_backend",
        "redis_url",
        "koraku_api_key",
        "health_detail_token",
        "chat_rate_limit_per_minute",
        "automation_rate_limit_per_minute",
        "automation_manual_run_concurrency_per_user",
        "supabase_jwt_secret",
        "supabase_url",
        "supabase_service_role_key",
        "supermemory_api_key",
        "supermemory_context_max_chars",
        "personalization_cache_ttl_seconds",
        "learned_memory_cache_ttl_seconds",
        "chat_learned_memory_timeout_seconds",
        "tenant_org_membership_cache_ttl_seconds",
        "automation_scheduler_enabled",
        "automation_scheduler_resync_seconds",
        "automation_max_steps",
        "automation_run_timeout_seconds",
        "blaxel_cloud_sandbox_enabled",
        "bl_workspace",
        "bl_api_key",
        "blaxel_sandbox_image",
        "blaxel_sandbox_region",
        "blaxel_sandbox_memory_mb",
        "blaxel_sandbox_workdir",
        "blaxel_sandbox_ready_timeout_seconds",
        "blaxel_sandbox_cache_ttl_seconds",
        "sendblue_api_key",
        "sendblue_api_secret",
        "sendblue_from_number",
        "sendblue_webhook_secret",
        "sendblue_api_base",
        "sendblue_inbound_media_host_allowlist",
        "imessage_voice_transcription_enabled",
        "voice_transcription_base_url",
        "voice_transcription_model",
        "chat_defer_blaxel_provision",
    }
)

_SDK_FIELD_NAMES = frozenset(SdkSettings.model_fields)


def _cloud_field_names() -> frozenset[str]:
    from koraku_cloud.cloud_settings import CloudSettings

    return frozenset(CloudSettings.model_fields)


def _get_cloud_layer() -> Any:
    global _inert_cloud
    if _cloud_bound and _cloud_settings is not None:
        return _cloud_settings
    if _inert_cloud is None:
        from koraku_cloud.cloud_settings import inert_cloud_settings

        _inert_cloud = inert_cloud_settings()
    return _inert_cloud


def _update_cloud_layer(**kwargs: Any) -> None:
    global _cloud_settings, _inert_cloud, _default_merged
    layer = _get_cloud_layer()
    updated = layer.model_copy(update=kwargs)
    if _cloud_bound:
        _cloud_settings = updated
    else:
        _inert_cloud = updated
    _default_merged = None


def is_cloud_configured() -> bool:
    return _cloud_bound


def bind_cloud_settings(cloud: Any) -> None:
    global _cloud_bound, _cloud_settings, _default_merged
    _cloud_bound = True
    _cloud_settings = cloud
    _default_merged = None


def reset_cloud_binding() -> None:
    """Clear Cloud layer (tests and SDK-only servers)."""
    global _cloud_bound, _cloud_settings, _inert_cloud, _default_merged
    _cloud_bound = False
    _cloud_settings = None
    _inert_cloud = None
    _default_merged = None


def get_sdk_settings() -> SdkSettings:
    override = _settings_override.get()
    if override is not None:
        return override.sdk
    global _default_sdk
    if _default_sdk is None:
        _default_sdk = SdkSettings()
    return _default_sdk


def configure_sdk(settings_obj: SdkSettings | None = None, **kwargs: Any) -> SdkSettings:
    from koraku.core.auth import reset_auth_verifier
    from koraku.plugins.memory import reset_memory_backend_cache

    global _default_sdk, _default_merged
    if settings_obj is not None:
        _default_sdk = settings_obj
    elif kwargs:
        _default_sdk = get_sdk_settings().model_copy(update=kwargs)
    else:
        _default_sdk = SdkSettings()
    _default_merged = None
    reset_memory_backend_cache()
    reset_auth_verifier()
    return _default_sdk


class _MergedSettings:
    """Merged view: SDK agent config + Cloud product config when bound."""

    __slots__ = ("_sdk",)

    def __init__(self, sdk: SdkSettings) -> None:
        self._sdk = sdk

    @property
    def sdk(self) -> SdkSettings:
        return self._sdk

    @property
    def cloud(self) -> Any:
        return _get_cloud_layer()

    def __getattr__(self, name: str) -> Any:
        cloud_fields = _cloud_field_names()
        if is_cloud_configured() and name in _CLOUD_OVERRIDE_FIELDS:
            return getattr(_get_cloud_layer(), name)
        if name in _SDK_FIELD_NAMES or hasattr(type(self._sdk), name):
            return getattr(self._sdk, name)
        if name in cloud_fields:
            return getattr(_get_cloud_layer(), name)
        raise AttributeError(name)

    def model_copy(self, *, update: dict[str, Any] | None = None, deep: bool = False) -> _MergedSettings:
        update = dict(update or {})
        sdk_keys = {k: v for k, v in update.items() if k in _SDK_FIELD_NAMES}
        cloud_keys = {k: v for k, v in update.items() if k in _cloud_field_names()}
        sdk = self._sdk.model_copy(update=sdk_keys) if sdk_keys else self._sdk
        if cloud_keys:
            _update_cloud_layer(**cloud_keys)
        return _MergedSettings(sdk)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        out = self._sdk.model_dump(**kwargs)
        out.update(_get_cloud_layer().model_dump(**kwargs))
        return out

    @classmethod
    def model_construct(cls, **_kwargs: Any) -> _MergedSettings:
        cloud_fields = _cloud_field_names()
        sdk_kwargs = {k: v for k, v in _kwargs.items() if k in _SDK_FIELD_NAMES}
        cloud_kwargs = {k: v for k, v in _kwargs.items() if k in cloud_fields}
        sdk = SdkSettings.model_construct(**sdk_kwargs)
        if cloud_kwargs:
            from koraku_cloud.cloud_settings import CloudSettings

            bind_cloud_settings(CloudSettings.model_construct(**cloud_kwargs))
        return cls(sdk)

    def __repr__(self) -> str:
        mode = "cloud" if is_cloud_configured() else "sdk"
        return f"Settings(mode={mode!r}, sdk={self._sdk!r})"


class _SettingsMeta(type):
    def __call__(cls, *args: Any, **kwargs: Any) -> _MergedSettings:
        if len(args) == 1 and isinstance(args[0], SdkSettings) and not kwargs:
            return _MergedSettings(args[0])
        if not args and not kwargs:
            return _merged_default()
        cloud_fields = _cloud_field_names()
        sdk_kwargs = {k: v for k, v in kwargs.items() if k in _SDK_FIELD_NAMES}
        cloud_kwargs = {k: v for k, v in kwargs.items() if k in cloud_fields}
        sdk = SdkSettings(**sdk_kwargs) if sdk_kwargs else SdkSettings()
        if cloud_kwargs:
            from koraku_cloud.cloud_settings import CloudSettings

            bind_cloud_settings(CloudSettings(**cloud_kwargs))
        return _MergedSettings(sdk)

    def __instancecheck__(cls, instance: object) -> bool:
        return isinstance(instance, _MergedSettings)


class Settings(_MergedSettings, metaclass=_SettingsMeta):
    """Backward-compatible name for merged SDK + Cloud settings."""


def _merged_default() -> Settings:
    global _default_merged
    if _default_merged is None:
        _default_merged = Settings(get_sdk_settings())
    return _default_merged


def get_settings() -> Settings:
    override = _settings_override.get()
    if override is not None:
        return override
    return _merged_default()


class _SettingsProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        if name in _cloud_field_names():
            _update_cloud_layer(**{name: value})
            return
        configure(get_settings().model_copy(update={name: value}))

    def __repr__(self) -> str:
        return repr(get_settings())


settings = _SettingsProxy()


def configure(settings_obj: SdkSettings | Settings | None = None, **kwargs: Any) -> Settings:
    from koraku.core.auth import reset_auth_verifier
    from koraku.plugins.memory import reset_memory_backend_cache

    global _default_merged, _default_sdk
    if isinstance(settings_obj, SdkSettings):
        _default_sdk = settings_obj
        _default_merged = None
    elif isinstance(settings_obj, Settings):
        _default_sdk = settings_obj.sdk
        _default_merged = settings_obj
    elif kwargs:
        merged = get_settings().model_copy(update=kwargs)
        _default_sdk = merged.sdk
        _default_merged = merged
    else:
        _default_sdk = SdkSettings()
        _default_merged = None
    reset_memory_backend_cache()
    reset_auth_verifier()
    return get_settings()


@contextmanager
def use_settings(settings_obj: Settings | SdkSettings) -> Iterator[Settings]:
    if isinstance(settings_obj, SdkSettings):
        wrapped: Settings = Settings(settings_obj)  # type: ignore[call-arg]
    else:
        wrapped = settings_obj
    token = _settings_override.set(wrapped)
    try:
        yield wrapped
    finally:
        _settings_override.reset(token)
