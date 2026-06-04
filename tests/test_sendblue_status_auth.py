"""SendBlue status must not be public on Cloud deployments."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from koraku.core.config import Settings, configure, use_settings
from koraku.core.product_hooks import ProductHooks, clear_product_hooks, register_product_hooks


@pytest.fixture
def cloud_client() -> TestClient:
    from koraku_cloud.app import create_cloud_app

    clear_product_hooks()
    register_product_hooks(ProductHooks())
    return TestClient(create_cloud_app())


def test_sendblue_status_requires_auth_on_cloud(cloud_client: TestClient) -> None:
    with use_settings(
        Settings.model_construct(
            require_auth_for_chat=True,
            auth_backend="supabase",
        )
    ):
        r = cloud_client.get("/sendblue/status")
    assert r.status_code == 401
