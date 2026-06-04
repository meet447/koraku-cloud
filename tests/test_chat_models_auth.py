"""Chat model catalog requires auth when REQUIRE_AUTH_FOR_CHAT is enabled."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from koraku.core.config import Settings, configure, use_settings
from koraku.server_sdk import create_sdk_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_sdk_app())


def test_chat_models_requires_auth(client: TestClient) -> None:
    with use_settings(
        Settings.model_construct(
            require_auth_for_chat=True,
            auth_backend="supabase",
        )
    ):
        r = client.get("/api/chat-models")
    assert r.status_code == 401


def test_chat_models_allows_demo_mode(client: TestClient) -> None:
    with use_settings(
        Settings.model_construct(
            require_auth_for_chat=False,
            auth_backend="none",
        )
    ):
        r = client.get("/api/chat-models")
    assert r.status_code == 200
    assert "providers" in r.json()
