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
from fastapi.testclient import TestClient
from koraku.server_core import attach_index_route

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
