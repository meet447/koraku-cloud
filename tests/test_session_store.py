"""Session store backends (memory + Redis)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from koraku.core.config import Settings, configure, use_settings
from koraku.core.models import SessionState
from koraku.core import redis_client
from koraku.core.session_store import (
    MemorySessionStore,
    RedisSessionStore,
    build_session_store,
    get_session_store,
    reset_session_store,
)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    reset_session_store()
    yield
    reset_session_store()


def test_memory_store_get_or_create_roundtrip() -> None:
    store = MemorySessionStore()
    tid = str(uuid.uuid4())
    a = store.get_or_create(tid, owner_sub="user-a")
    assert a.session_id == tid
    b = store.get_or_create(tid, owner_sub="user-a")
    assert b is a


def test_memory_store_rejects_other_owner() -> None:
    store = MemorySessionStore()
    tid = str(uuid.uuid4())
    store.get_or_create(tid, owner_sub="user-a").add_message("user", "hi")
    b = store.get_or_create(tid, owner_sub="user-b")
    assert b.owner_sub == "user-b"
    assert b.messages == []


def test_build_session_store_redis_fallback_without_url() -> None:
    redis_client.reset_client()
    with use_settings(Settings(session_store_backend="redis", redis_url="")):
        store = build_session_store()
        assert isinstance(store, MemorySessionStore)


def test_redis_store_save_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    bucket: dict[str, str] = {}

    def fake_get(key: str) -> str | None:
        return bucket.get(key)

    def fake_setex(key: str, value: str, ttl: int) -> bool:
        bucket[key] = value
        return True

    def fake_delete(key: str) -> None:
        bucket.pop(key, None)

    monkeypatch.setattr(redis_client, "get", fake_get)
    monkeypatch.setattr(redis_client, "setex", fake_setex)
    monkeypatch.setattr(redis_client, "delete", fake_delete)
    monkeypatch.setattr(redis_client, "is_configured", lambda: True)
    monkeypatch.setattr(redis_client, "get_client", lambda: MagicMock())

    with use_settings(
        Settings(
            session_store_backend="redis",
            redis_url="redis://127.0.0.1:6379/0",
        )
    ):
        store = RedisSessionStore()
        session = SessionState(session_id=str(uuid.uuid4()), owner_sub="u1")
        session.add_message("user", "hello")
        store.save(session)
        loaded = store.get(session.session_id)
        assert loaded is not None
        assert loaded.owner_sub == "u1"
        assert len(loaded.messages) == 1


def test_get_session_store_singleton() -> None:
    configure(Settings(session_store_backend="memory", redis_url=""))
    reset_session_store()
    assert get_session_store() is get_session_store()
