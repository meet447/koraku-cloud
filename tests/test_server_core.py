from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from koraku.server_core import run_startup_checks


def test_run_startup_checks_orchestration(mocker: MockerFixture) -> None:
    m_workspace = mocker.patch("koraku.server_core.assert_workspace_safe")
    m_resolve = mocker.patch("koraku.server_core.resolve_server_mode")
    m_cors = mocker.patch("koraku.server_core.assert_cors_safe")
    m_warn = mocker.patch("koraku.server_core.warn_startup_profile")
    m_redis = mocker.patch("koraku.server_core.assert_redis_for_multi_worker")

    m_resolve.return_value = ("mock_agent", "mock_mode")

    agent, mode = run_startup_checks()

    assert agent == "mock_agent"
    assert mode == "mock_mode"

    m_workspace.assert_called_once()
    m_resolve.assert_called_once()
    m_cors.assert_called_once_with("mock_mode")
    m_warn.assert_called_once()
    m_redis.assert_called_once()


def test_run_startup_checks_propagates_errors(mocker: MockerFixture) -> None:
    mocker.patch(
        "koraku.server_core.assert_workspace_safe", side_effect=RuntimeError("Workspace unsafe")
    )
    m_resolve = mocker.patch("koraku.server_core.resolve_server_mode")

    with pytest.raises(RuntimeError, match="Workspace unsafe"):
        run_startup_checks()

    m_resolve.assert_not_called()

from unittest.mock import MagicMock
from koraku.server_core import warn_startup_profile

def test_warn_startup_profile_sdk_mode(mocker):
    # Mock product_hooks_active to return False
    mocker.patch("koraku.server_core.product_hooks_active", return_value=False)
    mock_log = mocker.patch("koraku.server_core.log")

    warn_startup_profile()

    mock_log.info.assert_called_once_with(
        "Koraku SDK HTTP server (no Supabase product routes). "
        "Run koraku_cloud.app for Koraku Cloud."
    )
    mock_log.warning.assert_not_called()

def test_warn_startup_profile_missing_koraku_cloud(mocker, monkeypatch):
    # Mock product_hooks_active to return True
    mocker.patch("koraku.server_core.product_hooks_active", return_value=True)
    mock_log = mocker.patch("koraku.server_core.log")

    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "koraku_cloud.integrations.supabase_tenant":
            raise ImportError("No module named 'koraku_cloud'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    warn_startup_profile()

    mock_log.info.assert_not_called()
    mock_log.warning.assert_called_once_with(
        "koraku_cloud is not installed — Cloud product routes require the monorepo or koraku-cloud package."
    )

def test_warn_startup_profile_missing_supabase_config(mocker, monkeypatch):
    mocker.patch("koraku.server_core.product_hooks_active", return_value=True)
    mock_log = mocker.patch("koraku.server_core.log")

    import builtins
    original_import = builtins.__import__

    # We need to mock the import of koraku_cloud.integrations.supabase_tenant
    # so that it successfully imports but returns False for supabase_tenant_configured
    mock_supabase_tenant = MagicMock()
    mock_supabase_tenant.supabase_tenant_configured.return_value = False

    def mock_import(name, *args, **kwargs):
        if name == "koraku_cloud.integrations.supabase_tenant":
            return mock_supabase_tenant
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    # also mock settings so it doesn't trigger the next warning
    monkeypatch.setattr("koraku.server_core.settings.default_execution_target", "local", raising=False)

    warn_startup_profile()

    mock_log.info.assert_not_called()
    mock_log.warning.assert_any_call(
        "Supabase tenant storage is not configured (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY). "
        "Chat and personalization require a signed-in user with an organization."
    )

def test_warn_startup_profile_missing_blaxel(mocker, monkeypatch):
    import koraku.server_core
    mocker.patch("koraku.server_core.product_hooks_active", return_value=True)
    mock_log = mocker.patch("koraku.server_core.log")

    import builtins
    original_import = builtins.__import__

    mock_supabase_tenant = MagicMock()
    mock_supabase_tenant.supabase_tenant_configured.return_value = True

    def mock_import(name, *args, **kwargs):
        if name == "koraku_cloud.integrations.supabase_tenant":
            return mock_supabase_tenant
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    # `settings` is a _SettingsProxy, to patch properties, patch the underlying class property
    # but the simplest way is to mock it entirely since the proxy intercepts getattr
    mock_settings = MagicMock()
    mock_settings.default_execution_target = "cloud"
    mock_settings.blaxel_cloud_sandbox_enabled = False
    mock_settings.cors_origins_list = []
    mocker.patch("koraku.server_core.settings", mock_settings)

    warn_startup_profile()

    mock_log.info.assert_not_called()
    mock_log.warning.assert_any_call(
        "Cloud execution requires Blaxel (BLAXEL_CLOUD_SANDBOX_ENABLED=true, BL_WORKSPACE, BL_API_KEY). "
        "File and shell tools are sandbox-only — host disk is not used."
    )
