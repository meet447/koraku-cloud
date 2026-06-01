"""Detached agent runs: POST /runs + GET /runs/{id}/stream."""

from __future__ import annotations

import asyncio
import re
import time

import pytest
from fastapi.testclient import TestClient

from koraku.api import detached_runs
from koraku.core import detached_run_store
from koraku.server import app


@pytest.fixture(autouse=True)
def _detached_runs_test_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    detached_run_store.reset_detached_run_store()
    monkeypatch.setattr(detached_run_store, "_DETACHED_GC_SEC", 0.05, raising=False)
    monkeypatch.setattr(detached_run_store.settings, "detached_run_store_backend", "memory", raising=False)
    detached_run_store.reset_detached_run_store()
    monkeypatch.setattr("koraku.api.detached_runs.settings.require_auth_for_chat", False, raising=False)

    async def _fake_stream(*_a: object, **_kw: object):
        yield 'data: {"type": "koraku.started", "data": {"chatSessionId": "1234567890123456789012345678"}}\n\n'
        yield "event: done\n\n"

    monkeypatch.setattr("koraku.api.detached_runs._stream_agent_sse", _fake_stream, raising=False)


def test_runs_post_requires_auth_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("koraku.api.detached_runs.settings.require_auth_for_chat", True, raising=False)
    client = TestClient(app)
    resp = client.post("/runs", json={"msg": "hello"})
    assert resp.status_code == 401


def test_runs_post_returns_run_id() -> None:
    client = TestClient(app)
    resp = client.post("/runs", json={"msg": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        data["run_id"],
        re.I,
    )


def test_runs_subscribe_unknown_404() -> None:
    client = TestClient(app)
    rid = "00000000-0000-4000-8000-000000000000"
    resp = client.get(f"/runs/{rid}/stream", params={"after": -1})
    assert resp.status_code == 404


def test_runs_status_not_found() -> None:
    client = TestClient(app)
    rid = "00000000-0000-4000-8000-000000000001"
    r = client.get(f"/runs/{rid}/status")
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == rid
    assert data["state"] == "not_found"
    assert data["last_event_id"] == -1


def test_runs_status_completed_after_stream() -> None:
    client = TestClient(app)
    start = client.post("/runs", json={"msg": "hello"})
    rid = start.json()["run_id"]
    with client.stream("GET", f"/runs/{rid}/stream", params={"after": -1}) as r:
        assert r.status_code == 200
        _ = "".join(r.iter_text())
    time.sleep(0.02)
    st = client.get(f"/runs/{rid}/status")
    assert st.status_code == 200
    body = st.json()
    assert body["run_id"] == rid
    assert body["state"] in ("completed", "not_found")


def test_runs_subscribe_streams_sse() -> None:
    client = TestClient(app)
    start = client.post("/runs", json={"msg": "hello"})
    assert start.status_code == 200
    run_id = start.json()["run_id"]
    with client.stream("GET", f"/runs/{run_id}/stream", params={"after": -1}) as r:
        assert r.status_code == 200
        buf = "".join(r.iter_text())
    assert "koraku.started" in buf
    assert "event: done" in buf


def test_runs_post_accepts_client_turn_id() -> None:
    client = TestClient(app)
    tid = "00000000-0000-4000-8000-000000000003"
    resp = client.post("/runs", json={"msg": "hello", "turn_id": tid})
    assert resp.status_code == 200
    assert resp.json()["run_id"] == tid


def test_runs_post_idempotent_turn_id() -> None:
    client = TestClient(app)
    tid = "00000000-0000-4000-8000-000000000004"
    r1 = client.post("/runs", json={"msg": "hello", "turn_id": tid})
    r2 = client.post("/runs", json={"msg": "hello", "turn_id": tid})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["run_id"] == tid
    assert r2.json()["run_id"] == tid


def test_runs_post_rejects_invalid_turn_id() -> None:
    client = TestClient(app)
    resp = client.post("/runs", json={"msg": "hello", "turn_id": "not-a-uuid"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_run_buffer_disconnects_slow_subscriber(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(detached_run_store, "_SUBSCRIBER_QUEUE_MAX", 1, raising=False)
    buf = detached_run_store.MemoryRunBuffer(owner_sub=None)
    q: asyncio.Queue[object] = asyncio.Queue(maxsize=1)
    buf.subscribers.append(q)

    await buf.append("data: one\n\n")
    await buf.append("data: two\n\n")

    assert q not in buf.subscribers
