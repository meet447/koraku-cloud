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

from fastapi import FastAPI
from unittest.mock import AsyncMock
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
