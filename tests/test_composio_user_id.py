"""Composio user id must not silently share koraku-local when Composio is configured."""
from __future__ import annotations

import pytest

from koraku.integrations import composio


def test_user_id_uses_request_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    tok = composio.set_composio_request_user("user-abc")
    try:
        assert composio.user_id() == "user-abc"
    finally:
        composio.reset_composio_request_user(tok)


def test_user_id_allows_explicit_single_tenant_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    monkeypatch.setenv("COMPOSIO_USER_ID", "tenant-embed-1")
    assert composio.user_id() == "tenant-embed-1"


def test_user_id_rejects_shared_fallback_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    monkeypatch.delenv("COMPOSIO_USER_ID", raising=False)
    with pytest.raises(RuntimeError, match="per-request user id"):
        composio.user_id()


def test_user_id_koraku_local_when_composio_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: False)
    monkeypatch.delenv("COMPOSIO_USER_ID", raising=False)
    assert composio.user_id() == "koraku-local"
