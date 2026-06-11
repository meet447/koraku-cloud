from __future__ import annotations

from types import SimpleNamespace

import pytest

from koraku.integrations import composio


def test_primary_connected_account_id_prefers_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        composio,
        "list_connections_summary",
        lambda: [
            {"id": "ca_old", "status": "EXPIRED", "toolkit_slug": "GMAIL", "is_disabled": False},
            {"id": "ca_new", "status": "ACTIVE", "toolkit_slug": "GMAIL", "is_disabled": False},
        ],
    )
    assert composio.primary_connected_account_id("GMAIL") == "ca_new"


def test_connected_account_id_for_tool_execution_uses_toolkit_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        composio,
        "connections_for_toolkit",
        lambda toolkit: [
            {"id": "ca_1", "status": "ACTIVE", "toolkit_slug": "GMAIL", "is_disabled": False},
            {"id": "ca_2", "status": "ACTIVE", "toolkit_slug": "GMAIL", "is_disabled": False},
        ],
    )
    assert composio._connected_account_id_for_tool_execution("GMAIL_FETCH_EMAILS") == "ca_2"


def test_start_toolkit_auth_returns_already_connected_when_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    monkeypatch.setattr(composio, "user_id", lambda: "user-1")
    monkeypatch.setattr(composio, "invalidate_connections_cache", lambda _uid=None: None)
    monkeypatch.setattr(composio, "cleanup_duplicate_toolkit_connections", lambda _slug=None: 0)
    monkeypatch.setattr(
        composio,
        "connections_for_toolkit",
        lambda _slug: [
            {"id": "ca_live", "status": "ACTIVE", "toolkit_slug": "GMAIL", "is_disabled": False},
        ],
    )

    class FailClient:
        class toolkits:
            @staticmethod
            def authorize(**_kwargs):
                raise AssertionError("authorize should not run when already connected")

    monkeypatch.setattr(composio, "_client", lambda: FailClient())

    out = composio.start_toolkit_auth("gmail")
    assert out["already_connected"] is True
    assert out["status"] == "ACTIVE"
    assert out["redirect_url"] is None
    assert out["connection_request_id"] == "ca_live"


def test_start_toolkit_auth_uses_allow_multiple_when_duplicates_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    monkeypatch.setattr(composio, "user_id", lambda: "user-1")
    monkeypatch.setattr(composio, "invalidate_connections_cache", lambda _uid=None: None)
    monkeypatch.setattr(composio, "cleanup_duplicate_toolkit_connections", lambda _slug=None: 0)
    monkeypatch.setattr(
        composio,
        "connections_for_toolkit",
        lambda _slug: [
            {
                "id": "ca_a",
                "status": "INITIATED",
                "toolkit_slug": "GMAIL",
                "is_disabled": False,
                "auth_config_id": "ac_test",
            },
            {
                "id": "ca_b",
                "status": "INITIATED",
                "toolkit_slug": "GMAIL",
                "is_disabled": False,
                "auth_config_id": "ac_test",
            },
        ],
    )

    class Client:
        class toolkits:
            @staticmethod
            def authorize(**_kwargs):
                raise RuntimeError(
                    "Multiple connected accounts found for user. Please use the allow_multiple option."
                )

        class connected_accounts:
            @staticmethod
            def link(*, user_id: str, auth_config_id: str):
                assert user_id == "user-1"
                assert auth_config_id == "ac_test"
                return SimpleNamespace(
                    id="ca_new",
                    status="INITIATED",
                    redirect_url="https://composio.example/oauth",
                )

    monkeypatch.setattr(composio, "_client", lambda: Client())

    out = composio.start_toolkit_auth("GMAIL")
    assert out["already_connected"] is False
    assert out["redirect_url"] == "https://composio.example/oauth"
    assert out["connection_request_id"] == "ca_new"


def test_cleanup_duplicate_toolkit_connections_deletes_stale_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    monkeypatch.setattr(composio, "user_id", lambda: "user-1")
    deleted: list[str] = []

    monkeypatch.setattr(
        composio,
        "list_connections_summary",
        lambda: [
            {
                "id": "ca_stale",
                "status": "INITIATED",
                "toolkit_slug": "GMAIL",
                "is_disabled": False,
            },
            {
                "id": "ca_old_active",
                "status": "ACTIVE",
                "toolkit_slug": "GMAIL",
                "is_disabled": False,
            },
            {
                "id": "ca_keep",
                "status": "ACTIVE",
                "toolkit_slug": "GMAIL",
                "is_disabled": False,
            },
        ],
    )

    class Client:
        class connected_accounts:
            @staticmethod
            def delete(account_id: str) -> None:
                deleted.append(account_id)

    monkeypatch.setattr(composio, "_client", lambda: Client())
    monkeypatch.setattr(composio, "invalidate_connections_cache", lambda _uid=None: None)

    removed = composio.cleanup_duplicate_toolkit_connections("GMAIL")
    assert removed == 2
    assert deleted == ["ca_stale", "ca_old_active"]


def test_execute_composio_tool_passes_connected_account_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    monkeypatch.setattr(composio, "user_id", lambda: "user-1")
    monkeypatch.setattr(
        composio,
        "_connected_account_id_for_tool_execution",
        lambda _slug: "ca_pick",
    )

    captured: dict[str, object] = {}

    class Client:
        class tools:
            @staticmethod
            def get_raw_composio_tool_by_slug(_slug: str):
                return None

            @staticmethod
            def execute(**kwargs):
                captured.update(kwargs)
                return {"successful": True, "data": {"ok": True}}

    monkeypatch.setattr(composio, "_client", lambda: Client())

    out = composio._execute_composio_tool_sync("GMAIL_FETCH_EMAILS", {})
    assert '"ok": true' in out.lower()
    assert captured["connected_account_id"] == "ca_pick"
