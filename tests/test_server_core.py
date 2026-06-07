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
from koraku.server_core import assert_workspace_safe

def test_post() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/test")
    async def test_get() -> dict[str, str]:
        return {"status": "ok"}

    attach_common_middleware(app)
    return TestClient(app)

def test_body_size_limit_valid_size(app_client: TestClient) -> None:
    # Within limits, should pass through and return 200
    headers = {"Content-Length": str(settings.max_request_body_bytes - 1)}
    response = app_client.post("/test", headers=headers, json={"a": "b"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_body_size_limit_invalid_size(app_client: TestClient) -> None:
    # Invalid Content-Length, should return 400
    headers = {"Content-Length": "not-an-int"}
    response = app_client.post("/test", headers=headers)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Content-Length"}

def test_body_size_limit_exceeds_size(app_client: TestClient) -> None:
    # Exceeds max_request_body_bytes, should return 413
    headers = {"Content-Length": str(settings.max_request_body_bytes + 1)}
    response = app_client.post("/test", headers=headers)
    assert response.status_code == 413
    assert response.json() == {
        "detail": f"Request body exceeds {settings.max_request_body_bytes} bytes."
    }

def test_body_size_limit_no_content_length(app_client: TestClient) -> None:
    # No Content-Length provided, should pass through and return 200
    response = app_client.post("/test")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_body_size_limit_get_method(app_client: TestClient) -> None:
    # Middleware only checks POST/PUT/PATCH, GET should pass even with big content length
    headers = {"Content-Length": str(settings.max_request_body_bytes + 1)}
    response = app_client.get("/test", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

from fastapi import FastAPI, Request

def test_request_id_middleware():
    app = FastAPI()
    attach_common_middleware(app)

    @app.get("/")
    async def root(request: Request):
        return {"rid": getattr(request.state, "request_id", None)}

    client = TestClient(app)

    # Test without an existing request ID header
    response = client.get("/")
    assert response.status_code == 200
    res_json = response.json()
    assert "rid" in res_json
    rid = res_json["rid"]
    assert rid is not None
    assert len(rid) > 0
    assert response.headers.get("x-request-id") == rid

    # Test with an existing request ID header
    custom_rid = "test-custom-id-123"
    response2 = client.get("/", headers={"x-request-id": custom_rid})
    assert response2.status_code == 200
    res_json2 = response2.json()
    assert res_json2.get("rid") == custom_rid
    assert response2.headers.get("x-request-id") == custom_rid

from unittest.mock import patch
from koraku.server_core import assert_workspace_safe

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
