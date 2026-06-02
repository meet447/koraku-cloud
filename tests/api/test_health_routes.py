import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from koraku.api.health_routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_health_check_minimal(monkeypatch):
    monkeypatch.setattr("koraku.api.health_routes.settings.agent_name", "test_agent")
    monkeypatch.setattr("koraku.api.health_routes.settings.version", "1.0.0")
    monkeypatch.setattr("koraku.api.health_routes.settings.llm_provider", "test_provider")
    monkeypatch.setattr("koraku.api.health_routes.any_llm_configured", lambda: False)

    class _FakeStore:
        pass

    monkeypatch.setattr(
        "koraku.api.health_routes.get_detached_run_store",
        lambda: _FakeStore(),
    )
    monkeypatch.setattr(
        "koraku.api.health_routes.RedisDetachedRunStore",
        type("RedisDetachedRunStore", (), {}),
    )

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["agent"] == "test_agent"
    assert data["version"] == "1.0.0"
    assert data["mode"] == "unconfigured"
    assert data["llm_configured"] is False
    assert data["llm_provider"] == "test_provider"
    assert "detached_runs_redis" in data
    assert "redis_connected" not in data


def test_health_check_configured_mode():
    app_live = FastAPI()
    app_live.include_router(router)
    app_live.state.server_mode = "live"
    client_live = TestClient(app_live)

    response = client_live.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "live"
    assert data["status"] == "ok"


def test_health_detail_requires_token(monkeypatch):
    monkeypatch.setattr("koraku.api.health_routes.settings.health_detail_token", "secret-token")
    response = client.get("/health/detail")
    assert response.status_code == 401

    response = client.get(
        "/health/detail",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "redis_connected" in data
