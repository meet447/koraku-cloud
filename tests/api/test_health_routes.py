import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from koraku.api.health_routes import router

# Create a FastAPI app and include the router for testing
app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_health_check_unconfigured(monkeypatch):
    """
    Test the /health endpoint when the server is in an unconfigured state.
    We mock all dependencies and settings to verify the structure and default values
    of the returned JSON dictionary.
    """
    # Mock settings / core variables used in health_routes
    monkeypatch.setattr("koraku.api.health_routes.settings.agent_name", "test_agent")
    monkeypatch.setattr("koraku.api.health_routes.settings.version", "1.0.0")
    monkeypatch.setattr("koraku.api.health_routes.settings.llm_provider", "test_provider")
    monkeypatch.setattr("koraku.api.health_routes.settings.max_steps", 10)
    monkeypatch.setattr("koraku.api.health_routes.settings.research_max_steps", 20)
    monkeypatch.setattr("koraku.api.health_routes.settings.exa_api_key", "")
    monkeypatch.setattr("koraku.api.health_routes.settings.firecrawl_api_key", "mock_key")
    monkeypatch.setattr("koraku.api.health_routes.settings.session_ttl_hours", 24)
    monkeypatch.setattr("koraku.api.health_routes.settings.session_store_max", 100)
    monkeypatch.setattr("koraku.api.health_routes.settings.agent_llm_stream_timeout_seconds", 30)
    monkeypatch.setattr("koraku.api.health_routes.settings.agent_tool_phase_timeout_seconds", 60)
    monkeypatch.setattr("koraku.api.health_routes.settings.blaxel_cloud_sandbox_enabled", False)
    monkeypatch.setattr("koraku.api.health_routes.settings.automation_scheduler_enabled", True)
    monkeypatch.setattr("koraku.api.health_routes.settings.automation_max_steps", 15)
    monkeypatch.setattr("koraku.api.health_routes.settings.automation_run_timeout_seconds", 120)

    # Mock dynamic functions/integrations check
    monkeypatch.setattr("koraku.api.health_routes.composio_runtime.is_configured", lambda: True)
    monkeypatch.setattr("koraku.api.health_routes.any_llm_configured", lambda: False)
    monkeypatch.setattr("koraku.api.health_routes.configured_provider_ids", lambda: ["test_provider"])
    monkeypatch.setattr("koraku.api.health_routes.default_chat_model", lambda: "test_model")
    monkeypatch.setattr("koraku.api.health_routes.cloud_blaxel_block_reason", lambda _settings: None)
    monkeypatch.setattr("koraku.api.health_routes.automation_scheduler.is_running", lambda: False)
    monkeypatch.setattr("koraku.api.health_routes.automation_scheduler.is_automation_scheduler_leader", lambda: False)
    monkeypatch.setattr("koraku.api.health_routes.supabase_automations_configured", lambda: False)
    monkeypatch.setattr("koraku.api.health_routes.supabase_chat_history_configured", lambda: False)

    monkeypatch.setattr("koraku.api.health_routes.active_session_count", lambda: 0)

    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["agent"] == "test_agent"
    assert data["version"] == "1.0.0"

    # "mode" checks getattr(request.app.state, "server_mode", "unconfigured")
    assert data["mode"] == "unconfigured"

    assert data["composio_configured"] is True
    assert data["llm_configured"] is False
    assert data["llm_provider"] == "test_provider"
    assert data["configured_providers"] == ["test_provider"]
    assert data["default_model"] == "test_model"
    assert data["max_steps_standard"] == 10
    assert data["max_steps_extended"] == 20
    assert data["exa_enabled"] is False
    assert data["firecrawl_enabled"] is True
    assert data["session_ttl_hours"] == 24
    assert data["session_store_max"] == 100
    assert data["agent_llm_stream_timeout_seconds"] == 30
    assert data["agent_tool_phase_timeout_seconds"] == 60
    assert data["active_chat_sessions"] == 0
    assert data["blaxel_cloud_sandbox_enabled"] is False
    assert data["cloud_chat_sandbox_block_reason"] is None
    assert data["automation_scheduler_running"] is False
    assert data["automation_scheduler_leader"] is False
    assert data["automation_scheduler_enabled"] is True
    assert data["automation_max_steps"] == 15
    assert data["automation_run_timeout_seconds"] == 120
    assert data["automations_supabase_configured"] is False
    assert data["chat_history_supabase_configured"] is False


def test_health_check_configured_mode():
    """
    Test the /health endpoint when the server is in a live/configured state.
    We set app.state.server_mode to 'live' to verify the mode is picked up correctly.
    """
    app_live = FastAPI()
    app_live.include_router(router)
    # Set the state manually to simulate server.py's behaviour
    app_live.state.server_mode = "live"

    client_live = TestClient(app_live)

    response = client_live.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "live"
    assert data["status"] == "ok"
