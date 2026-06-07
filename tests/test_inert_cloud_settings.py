import os
import pytest
from koraku.inert_cloud_settings import CloudSettings, inert_cloud_settings

def test_inert_cloud_settings_defaults():
    settings = inert_cloud_settings()
    assert settings.require_auth_for_chat is False
    assert settings.auth_backend == "none"
    assert settings.default_execution_target == "local"
    assert settings.memory_backend == "filesystem"
    assert settings.session_store_backend == "memory"
    assert settings.detached_run_store_backend == "memory"
    assert settings.blaxel_cloud_sandbox_enabled is False

def test_cloud_settings_post_init_sets_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BL_API_KEY", raising=False)
    monkeypatch.delenv("BL_WORKSPACE", raising=False)

    CloudSettings(
        bl_api_key="test_key",
        bl_workspace="test_ws",
    )

    assert os.environ.get("BL_API_KEY") == "test_key"
    assert os.environ.get("BL_WORKSPACE") == "test_ws"

def test_cloud_settings_post_init_ignores_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BL_API_KEY", raising=False)
    monkeypatch.delenv("BL_WORKSPACE", raising=False)

    CloudSettings(
        bl_api_key="  ",
        bl_workspace="",
    )

    assert "BL_API_KEY" not in os.environ
    assert "BL_WORKSPACE" not in os.environ
