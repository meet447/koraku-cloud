from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from koraku.server_core import attach_common_middleware
from koraku.core.config import settings

def test_request_id_middleware_generates_id() -> None:
    app = FastAPI()
    attach_common_middleware(app)

    @app.get("/test")
    def test_route(request: Request):
        return {"id": request.state.request_id}

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    # Check that a UUID was generated
    assert len(data["id"]) > 0
    # Check that the header is set correctly
    assert response.headers.get("X-Request-ID") == data["id"]

def test_request_id_middleware_preserves_id() -> None:
    app = FastAPI()
    attach_common_middleware(app)

    @app.get("/test")
    def test_route(request: Request):
        return {"id": request.state.request_id}

    client = TestClient(app)
    custom_id = "my-custom-request-id-123"
    response = client.get("/test", headers={"x-request-id": custom_id})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == custom_id
    assert response.headers.get("X-Request-ID") == custom_id

def test_body_size_limit_middleware_allowed() -> None:
    app = FastAPI()

    original_max = settings.max_request_body_bytes
    settings.max_request_body_bytes = 100

    try:
        attach_common_middleware(app)

        @app.post("/test")
        def test_route(request: Request):
            return {"status": "ok"}

        client = TestClient(app)
        response = client.post("/test", content=b"x" * 50)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        settings.max_request_body_bytes = original_max

def test_body_size_limit_middleware_exceeded() -> None:
    app = FastAPI()

    original_max = settings.max_request_body_bytes
    settings.max_request_body_bytes = 100

    try:
        attach_common_middleware(app)

        @app.post("/test")
        def test_route(request: Request):
            return {"status": "ok"}

        client = TestClient(app)
        response = client.post("/test", content=b"x" * 150)

        assert response.status_code == 413
        assert "exceeds 100 bytes" in response.json()["detail"]
    finally:
        settings.max_request_body_bytes = original_max

def test_body_size_limit_middleware_invalid_content_length() -> None:
    app = FastAPI()
    attach_common_middleware(app)

    @app.post("/test")
    def test_route(request: Request):
        return {"status": "ok"}

    client = TestClient(app)
    response = client.post("/test", content=b"x" * 50, headers={"content-length": "invalid"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Content-Length"

def test_body_size_limit_middleware_ignored_methods() -> None:
    app = FastAPI()

    original_max = settings.max_request_body_bytes
    settings.max_request_body_bytes = 100

    try:
        attach_common_middleware(app)

        @app.get("/test")
        def test_route(request: Request):
            return {"status": "ok"}

        client = TestClient(app)
        # GET requests shouldn't be blocked even with large content-length
        # (Though technically GETs shouldn't have bodies, the middleware explicitly
        # checks for POST, PUT, PATCH)
        response = client.get("/test", headers={"content-length": "1000"})

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        settings.max_request_body_bytes = original_max
