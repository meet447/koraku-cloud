"""Composio catalog requires auth on Cloud / production-style settings."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from koraku.core.config import Settings, configure, use_settings
from koraku.core.product_hooks import ProductHooks, clear_product_hooks, register_product_hooks
from koraku.server_sdk import create_sdk_app


@pytest.fixture
def client() -> TestClient:
    clear_product_hooks()
    return TestClient(create_sdk_app())


def test_composio_toolkits_requires_auth_when_chat_auth_required(client: TestClient) -> None:
    with use_settings(
        Settings.model_construct(
            require_auth_for_chat=True,
            auth_backend="supabase",
        )
    ):
        r = client.get("/api/composio/toolkits")
    assert r.status_code == 401


def test_composio_toolkits_requires_auth_when_product_hooks_active(client: TestClient) -> None:
    register_product_hooks(ProductHooks())
    try:
        with use_settings(
            Settings.model_construct(
                require_auth_for_chat=False,
                auth_backend="none",
            )
        ):
            r = client.get("/api/composio/toolkits")
        assert r.status_code == 401
    finally:
        clear_product_hooks()


def test_composio_toolkits_open_in_local_demo_mode(client: TestClient) -> None:
    clear_product_hooks()
    with use_settings(
        Settings.model_construct(
            require_auth_for_chat=False,
            auth_backend="none",
        )
    ):
        r = client.get("/api/composio/toolkits")
    assert r.status_code == 200
    body = r.json()
    assert body.get("configured") is False
    assert isinstance(body.get("items"), list)
