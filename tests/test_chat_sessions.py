"""In-memory chat session continuity."""

from __future__ import annotations

import importlib
import uuid

import pytest

_sess = importlib.import_module("koraku.agent.sessions")


@pytest.fixture(autouse=True)
def _clear_sessions() -> None:
    from koraku.core.session_store import MemorySessionStore, get_session_store, reset_session_store

    reset_session_store()
    store = get_session_store()
    if isinstance(store, MemorySessionStore):
        store.sessions.clear()
    yield
    reset_session_store()


def test_get_or_create_uses_client_uuid_as_session_key() -> None:
    tid = str(uuid.uuid4())
    a = _sess.get_or_create_chat_session(tid)
    assert a.session_id == tid
    from koraku.core.session_store import MemorySessionStore, get_session_store

    store = get_session_store()
    assert isinstance(store, MemorySessionStore)
    assert store.sessions[tid] is a
    b = _sess.get_or_create_chat_session(tid)
    assert b is a


def test_get_or_create_no_id_is_random_each_time() -> None:
    a = _sess.get_or_create_chat_session(None)
    b = _sess.get_or_create_chat_session("")
    assert a.session_id != b.session_id


def test_get_or_create_huge_string_truncates_and_ignores() -> None:
    huge_str = "A" * 300
    a = _sess.get_or_create_chat_session(huge_str)
    # The string is >255 chars, so it should be truncated, fail UUID parsing, and create a new valid UUID.
    assert a.session_id != huge_str
    assert a.session_id != huge_str[:255]
    # Verify it generated a valid UUID since it failed the UUID test and rs became ""
    parsed_uuid = uuid.UUID(a.session_id)
    assert str(parsed_uuid) == a.session_id


def test_get_or_create_rejects_other_user_session_id() -> None:
    """A session created by user A must never be returned to user B (or to anon)."""
    tid = str(uuid.uuid4())
    a = _sess.get_or_create_chat_session(tid, owner_sub="user-a")
    a.add_message("user", "hello from a")
    assert a.session_id == tid

    # Different authenticated user passes the same session_id.
    b = _sess.get_or_create_chat_session(tid, owner_sub="user-b")
    assert b is not a
    assert b.messages == []
    # The store now belongs to user-b under the same id (a was evicted).
    from koraku.core.session_store import MemorySessionStore, get_session_store

    store = get_session_store()
    assert isinstance(store, MemorySessionStore)
    assert store.sessions[tid].owner_sub == "user-b"


def test_get_or_create_anon_cannot_resume_authed_session() -> None:
    tid = str(uuid.uuid4())
    a = _sess.get_or_create_chat_session(tid, owner_sub="user-a")
    a.add_message("user", "hello from a")
    anon = _sess.get_or_create_chat_session(tid, owner_sub=None)
    assert anon is not a
    assert anon.messages == []
