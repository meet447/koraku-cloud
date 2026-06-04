"""SDK vs Cloud HTTP app surfaces."""
from __future__ import annotations

from fastapi.testclient import TestClient

from koraku_cloud.app import create_cloud_app
from koraku.server_sdk import create_sdk_app


def test_sdk_app_has_stream_not_product_routes() -> None:
    client = TestClient(create_sdk_app())
    assert client.get("/health").status_code == 200
    assert client.post("/runs", json={"msg": "hi"}).status_code == 404
    assert client.get("/api/personalization").status_code == 404


def test_cloud_app_has_product_routes() -> None:
    cloud = create_cloud_app()
    paths = {getattr(r, "path", "") for r in cloud.routes}
    assert "/health" in paths
    assert "/runs" in paths
    assert "/api/personalization" in paths
    client = TestClient(cloud)
    assert client.get("/health").status_code == 200
