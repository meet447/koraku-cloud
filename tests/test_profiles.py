"""SDK vs Cloud settings layers."""
from __future__ import annotations

from koraku.core.config import Settings, configure_sdk, is_cloud_configured, reset_cloud_binding
from koraku.plugins.memory import get_memory_backend, reset_memory_backend_cache
from koraku.sdk import KorakuConfig
from koraku_cloud.bootstrap import bootstrap_cloud


def test_cloud_settings_defaults() -> None:
    reset_cloud_binding()
    bootstrap_cloud()
    s = Settings()
    assert s.default_execution_target == "cloud"
    assert s.memory_backend == "composite"
    assert s.require_auth_for_chat is True
    assert s.session_store_backend == "redis"
    assert is_cloud_configured()


def test_koraku_config_is_sdk_local_first() -> None:
    cfg = KorakuConfig(fireworks_api_key="x")
    sdk = cfg.to_sdk_settings()
    assert sdk.llm_provider == "fireworks"
    assert sdk.default_execution_target == "local"
    assert sdk.memory_backend == "filesystem"


def test_sdk_memory_backend_registers_local_tools() -> None:
    reset_cloud_binding()
    reset_memory_backend_cache()
    configure_sdk(KorakuConfig().to_sdk_settings())
    backend = get_memory_backend()
    assert backend.name == "filesystem"
    names = {t.name for t in backend.agent_tools()}
    assert "MemorySearch" in names
    assert "MemorySave" in names


def test_cloud_layer_construct() -> None:
    reset_cloud_binding()
    s = Settings.model_construct(
        default_execution_target="cloud",
        require_auth_for_chat=True,
        auth_backend="supabase",
        session_store_backend="redis",
    )
    assert s.default_execution_target == "cloud"
    assert is_cloud_configured()
