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

from typing import Any
from fastapi import FastAPI
from fastapi.testclient import TestClient
from koraku.server_core import attach_common_middleware
from koraku.core.config import settings
from fastapi import FastAPI, Request
from unittest.mock import patch
from koraku.agent import Agent
from koraku.server_core import resolve_server_mode
from unittest.mock import AsyncMock
from koraku.server_core import make_lifespan
from koraku.server_core import assert_workspace_safe
from koraku.server_core import attach_index_route
import logging
from koraku.core.config import use_settings
from koraku.core.sdk_settings import SdkSettings
from koraku.server_core import assert_cors_safe
from unittest.mock import MagicMock
from koraku.server_core import warn_startup_profile

@patch("koraku.server_core.any_llm_configured")
def test_resolve_server_mode_configured(mock_any_llm_configured) -> None:
    mock_any_llm_configured.return_value = True
    agent, mode = resolve_server_mode()
    assert isinstance(agent, Agent)
    assert mode == "live"

@patch("koraku.server_core.any_llm_configured")
def test_resolve_server_mode_unconfigured(mock_any_llm_configured) -> None:
    mock_any_llm_configured.return_value = False
    agent, mode = resolve_server_mode()
    assert agent is None
    assert mode == "unconfigured"

@patch("koraku.server_core.workspace_dir")
def test_assert_workspace_safe_valid(mock_workspace_dir):
    mock_workspace_dir.return_value = "/valid/path"
    assert_workspace_safe()

@patch("koraku.server_core.workspace_dir")
def test_assert_workspace_safe_root(mock_workspace_dir):
    mock_workspace_dir.return_value = "/"
    with pytest.raises(RuntimeError, match="Refusing to start: workspace_dir\\(\\) resolved to filesystem root"):
        assert_workspace_safe()

@patch("koraku.server_core.workspace_dir")
def test_assert_workspace_safe_empty(mock_workspace_dir):
    mock_workspace_dir.return_value = ""
    with pytest.raises(RuntimeError, match="Refusing to start: workspace_dir\\(\\) resolved to filesystem root"):
        assert_workspace_safe()

def test_attach_index_route_cloud(monkeypatch):
    monkeypatch.setattr("koraku.server_core.settings.agent_name", "test_agent")
    monkeypatch.setattr("koraku.server_core.settings.version", "1.0.0")
    monkeypatch.setattr("koraku.server_core.runtime_mode_label", lambda: "cloud")

    app = FastAPI()
    attach_index_route(app, variant="cloud")
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "test_agent"
    assert data["version"] == "1.0.0"
    assert data["runtime"] == "cloud"
    assert data["health"] == "/health"
    assert data["ui"] == "Run the Next.js app from the web/ directory for the browser UI."

def test_attach_index_route_sdk(monkeypatch):
    monkeypatch.setattr("koraku.server_core.settings.agent_name", "test_agent")
    monkeypatch.setattr("koraku.server_core.settings.version", "1.0.0")
    monkeypatch.setattr("koraku.server_core.runtime_mode_label", lambda: "sdk")

    app = FastAPI()
    attach_index_route(app, variant="sdk")
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "test_agent"
    assert data["version"] == "1.0.0"
    assert data["runtime"] == "sdk"
    assert data["health"] == "/health"
    assert data["ui"] == "Embed via Koraku Python SDK or POST /stream from your own UI."

def test_assert_cors_safe_not_live(caplog: pytest.LogCaptureFixture) -> None:
    """It does nothing if mode is not 'live', even if origin is *."""
    with use_settings(SdkSettings(cors_allowed_origins="*")):
        with caplog.at_level(logging.WARNING):
            assert_cors_safe("unconfigured")
        assert not caplog.records

def test_assert_cors_safe_empty_origins(caplog: pytest.LogCaptureFixture) -> None:
    """It logs a warning if mode is 'live' and no origins are specified."""
    with use_settings(SdkSettings(cors_allowed_origins="")):
        with caplog.at_level(logging.WARNING):
            assert_cors_safe("live")
        assert len(caplog.records) == 1
        assert "CORS_ALLOWED_ORIGINS is empty" in caplog.records[0].message

def test_assert_cors_safe_valid_origins(caplog: pytest.LogCaptureFixture) -> None:
    """It does nothing if mode is 'live' and origins are explicit."""
    with use_settings(SdkSettings(cors_allowed_origins="https://app.example.com")):
        with caplog.at_level(logging.WARNING):
            assert_cors_safe("live")
        assert not caplog.records

def test_assert_cors_safe_star_origin() -> None:
    """It raises RuntimeError if mode is 'live' and origin is *."""
    with use_settings(SdkSettings(cors_allowed_origins="*")):
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='*'"):
            assert_cors_safe("live")

def test_assert_cors_safe_star_origin_with_spaces() -> None:
    """It raises RuntimeError if mode is 'live' and origin is * with spaces."""
    with use_settings(SdkSettings(cors_allowed_origins=" * ")):
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='*'"):
            assert_cors_safe("live")

def test_assert_cors_safe_multiple_with_star_origin() -> None:
    """It raises RuntimeError if mode is 'live' and any origin is *."""
    with use_settings(SdkSettings(cors_allowed_origins="https://app.example.com,*")):
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='*'"):
            assert_cors_safe("live")

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

from koraku.server_core import make_lifespan

import pytest
from fastapi import FastAPI
from unittest.mock import AsyncMock

from koraku.server_core import make_lifespan

@pytest.mark.asyncio
async def test_make_lifespan_defaults(monkeypatch):
    monkeypatch.setattr("koraku.server_core.run_startup_checks", lambda: (None, "unconfigured"))

    app = FastAPI()
    lifespan = make_lifespan(enable_automation_scheduler=False)

    async with lifespan(app) as _:
        assert app.state.server_mode == "unconfigured"
        assert app.state.koraku_agent is None

@pytest.mark.asyncio
async def test_make_lifespan_explicit_mode():
    app = FastAPI()
    lifespan = make_lifespan(
        agent="mock_agent",
        mode="live",
        enable_automation_scheduler=False
    )

    async with lifespan(app) as _:
        assert app.state.server_mode == "live"
        assert app.state.koraku_agent == "mock_agent"

@pytest.mark.asyncio
async def test_make_lifespan_with_automation(monkeypatch):
    app = FastAPI()

    class MockAutomationScheduler:
        def __init__(self):
            self.configure_called = False
            self.start_called = False
            self.shutdown_called = False

        def configure_automation_scheduler(self, agent):
            self.configure_called = True

        def start_automation_scheduler(self):
            self.start_called = True

        def shutdown_automation_scheduler(self):
            self.shutdown_called = True

    mock_scheduler = MockAutomationScheduler()

    # We also need to mock ensure_project_webhook_subscription since it gets called when enable_automation_scheduler=True
    monkeypatch.setattr(
        "koraku.server_core.asyncio.to_thread",
        AsyncMock(return_value=None)
    )

    # Mocking koraku_cloud imports can be tricky, so let's mock it through sys.modules or monkeypatch
    import sys
    from unittest.mock import MagicMock

    mock_koraku_cloud = MagicMock()
    mock_koraku_cloud.automations.scheduler = mock_scheduler

    monkeypatch.setitem(sys.modules, "koraku_cloud.automations", mock_koraku_cloud.automations)
    monkeypatch.setitem(sys.modules, "koraku_cloud.automations.scheduler", mock_scheduler)

    mock_composio = MagicMock()
    monkeypatch.setitem(sys.modules, "koraku_cloud.integrations.composio_webhooks", mock_composio)

    lifespan = make_lifespan(
        agent="mock_agent",
        mode="live",
        enable_automation_scheduler=True
    )

    async with lifespan(app) as _:
        assert app.state.server_mode == "live"
        assert app.state.koraku_agent == "mock_agent"
        assert mock_scheduler.configure_called is True
        assert mock_scheduler.start_called is True

    assert mock_scheduler.shutdown_called is True
