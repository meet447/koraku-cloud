"""Phase A/B: reliability settings, health visibility, log redaction."""
from __future__ import annotations

from fastapi.testclient import TestClient

from koraku.core.config import settings
from koraku.server import app


def test_settings_has_agent_timeout_fields() -> None:
    assert settings.agent_llm_stream_timeout_seconds >= 30
    assert settings.agent_tool_phase_timeout_seconds >= 30
    assert settings.require_auth_for_chat is True
    assert settings.chat_rate_limit_per_minute > 0
    assert settings.cors_origins_list


def test_health_includes_reliability_and_sandbox_fields() -> None:
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "agent_llm_stream_timeout_seconds" in data
    assert "agent_tool_phase_timeout_seconds" in data
    assert "blaxel_cloud_sandbox_enabled" in data
    assert "cloud_chat_sandbox_block_reason" in data


def test_request_id_header_is_returned() -> None:
    client = TestClient(app)
    r = client.get("/health", headers={"x-request-id": "req-test-123"})
    assert r.status_code == 200
    assert r.headers["x-request-id"] == "req-test-123"


def test_stream_requires_auth_by_default() -> None:
    client = TestClient(app)
    r = client.post("/stream", json={"msg": "hi"})
    assert r.status_code == 401
