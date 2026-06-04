"""SDK settings layer (no Koraku Cloud package required)."""
from __future__ import annotations

from koraku.core.config import Settings, configure_sdk, is_cloud_configured, reset_cloud_binding
from koraku.core.sdk_settings import SdkSettings
from koraku.plugins.memory import get_memory_backend, reset_memory_backend_cache
from koraku.sdk import KorakuConfig


def test_sdk_settings_defaults() -> None:
    reset_cloud_binding()
    configure_sdk(
        SdkSettings.model_construct(
            default_execution_target="local",
            memory_backend="filesystem",
            session_store_backend="memory",
        )
    )
    reset_memory_backend_cache()
    s = Settings()
    assert s.default_execution_target == "local"
    assert s.memory_backend == "filesystem"
    assert s.require_auth_for_chat is False
    assert s.session_store_backend == "memory"
    assert s.blaxel_cloud_sandbox_enabled is False
    assert not is_cloud_configured()
    assert get_memory_backend(s) is not None


def test_koraku_config_matches_sdk_surface() -> None:
    cfg = KorakuConfig(execution_target="local", memory_backend="filesystem")
    sdk = cfg.to_sdk_settings()
    assert sdk.default_execution_target == "local"
    assert sdk.memory_backend == "filesystem"
