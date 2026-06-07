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

    # ensure subsequent functions are not called
    m_resolve.assert_not_called()

from unittest.mock import patch, MagicMock
import koraku.server_core
from koraku.server_core import assert_workspace_safe, resolve_server_mode, assert_cors_safe
from koraku.agent import Agent
import logging
from koraku.server_core import warn_startup_profile

def test_assert_workspace_safe():
    with patch("koraku.server_core.workspace_dir", return_value=""):
        with pytest.raises(RuntimeError, match="Refusing to start: workspace_dir\\(\\) resolved to filesystem root"):
            assert_workspace_safe()

    with patch("koraku.server_core.workspace_dir", return_value="/"):
        with pytest.raises(RuntimeError, match="Refusing to start: workspace_dir\\(\\) resolved to filesystem root"):
            assert_workspace_safe()

    with patch("koraku.server_core.workspace_dir", return_value="/tmp/workspace"):
        assert_workspace_safe()  # should not raise

def test_resolve_server_mode():
    with patch("koraku.server_core.any_llm_configured", return_value=True):
        agent, mode = resolve_server_mode()
        assert isinstance(agent, Agent)
        assert mode == "live"

    with patch("koraku.server_core.any_llm_configured", return_value=False):
        agent, mode = resolve_server_mode()
        assert agent is None
        assert mode == "unconfigured"

def test_assert_cors_safe(caplog):
    # Test non-live mode
    assert_cors_safe("unconfigured")  # should return early without doing anything

    # We need to mock settings directly since it's a _SettingsProxy that translates attribute accesses
    with patch("koraku.server_core.settings") as mock_settings:
        mock_settings.cors_origins_list = []
        with caplog.at_level(logging.WARNING):
            assert_cors_safe("live")
            assert "CORS_ALLOWED_ORIGINS is empty" in caplog.text

        mock_settings.cors_origins_list = ["*"]
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='\\*'"):
            assert_cors_safe("live")

        mock_settings.cors_origins_list = [" * "]
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='\\*'"):
            assert_cors_safe("live")

        mock_settings.cors_origins_list = ["https://example.com"]
        assert_cors_safe("live")  # should pass without exception

def test_warn_startup_profile(caplog):
    # Test not active
    with patch("koraku.server_core.product_hooks_active", return_value=False):
        with caplog.at_level(logging.INFO):
            warn_startup_profile()
            assert "Koraku SDK HTTP server" in caplog.text

    caplog.clear()

    # Test active but koraku_cloud missing (simulate ImportError)
    with patch("koraku.server_core.product_hooks_active", return_value=True):
        with patch("builtins.__import__", side_effect=ImportError("No module named 'koraku_cloud'")):
            with caplog.at_level(logging.WARNING):
                warn_startup_profile()
                assert "koraku_cloud is not installed" in caplog.text

    caplog.clear()

    # Test active, koraku_cloud present but tenant not configured
    # We patch settings again to test the blaxel warning
    with patch("koraku.server_core.product_hooks_active", return_value=True):
        import sys
        # Need to mock the import of koraku_cloud.integrations.supabase_tenant
        mock_module = MagicMock()
        mock_module.supabase_tenant_configured.return_value = False
        sys.modules['koraku_cloud.integrations.supabase_tenant'] = mock_module

        with patch("koraku.server_core.settings") as mock_settings:
            mock_settings.default_execution_target = "cloud"
            mock_settings.blaxel_cloud_sandbox_enabled = False

            with caplog.at_level(logging.WARNING):
                warn_startup_profile()
                assert "Supabase tenant storage is not configured" in caplog.text
                assert "Cloud execution requires Blaxel" in caplog.text

        # Clean up
        del sys.modules['koraku_cloud.integrations.supabase_tenant']

    caplog.clear()

    # Test active, configured, and blaxel enabled (should log no warnings)
    with patch("koraku.server_core.product_hooks_active", return_value=True):
        import sys
        mock_module = MagicMock()
        mock_module.supabase_tenant_configured.return_value = True
        sys.modules['koraku_cloud.integrations.supabase_tenant'] = mock_module

        with patch("koraku.server_core.settings") as mock_settings:
            mock_settings.default_execution_target = "cloud"
            mock_settings.blaxel_cloud_sandbox_enabled = True

            with caplog.at_level(logging.WARNING):
                warn_startup_profile()
                assert "Supabase tenant storage is not configured" not in caplog.text
                assert "Cloud execution requires Blaxel" not in caplog.text

        del sys.modules['koraku_cloud.integrations.supabase_tenant']

def test_run_startup_checks():
    mock_agent = MagicMock(spec=Agent)
    mock_mode = "live"

    with patch("koraku.server_core.assert_workspace_safe") as mock_ws_safe, \
         patch("koraku.server_core.resolve_server_mode", return_value=(mock_agent, mock_mode)) as mock_resolve, \
         patch("koraku.server_core.assert_cors_safe") as mock_cors_safe, \
         patch("koraku.server_core.warn_startup_profile") as mock_warn_profile, \
         patch("koraku.server_core.assert_redis_for_multi_worker") as mock_redis:

        agent, mode = run_startup_checks()

        # Check all functions were called in order
        mock_ws_safe.assert_called_once()
        mock_resolve.assert_called_once()
        mock_cors_safe.assert_called_once_with(mock_mode)
        mock_warn_profile.assert_called_once()
        mock_redis.assert_called_once()

        # Verify return value
        assert agent is mock_agent
        assert mode == mock_mode
