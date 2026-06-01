"""Cloud chat must not fall back to host disk when Blaxel is not fully configured."""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from koraku.integrations import blaxel_runtime as br
from koraku.integrations.cloud_user import (
    effective_cloud_user_id,
    reset_cloud_user_id,
    set_cloud_user_id,
)


def test_cloud_blaxel_block_reason_requires_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(br, "blaxel_sdk_available", lambda: True)
    s = SimpleNamespace(
        blaxel_cloud_sandbox_enabled=True,
        bl_workspace="",
        bl_api_key="secret",
    )
    msg = br.cloud_blaxel_block_reason(s)
    assert msg is not None
    assert "BL_WORKSPACE" in msg


def test_effective_cloud_user_id_requires_authenticated_user() -> None:
    with pytest.raises(RuntimeError, match="Authenticated"):
        effective_cloud_user_id()


def test_effective_cloud_user_id_from_request_context() -> None:
    t = set_cloud_user_id("jwt-sub-uuid")
    try:
        assert effective_cloud_user_id() == "jwt-sub-uuid"
    finally:
        reset_cloud_user_id(t)


def test_cloud_blaxel_block_reason_ok_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(br, "blaxel_sdk_available", lambda: True)
    s = SimpleNamespace(
        blaxel_cloud_sandbox_enabled=True,
        bl_workspace="my-ws",
        bl_api_key="secret",
    )
    assert br.cloud_blaxel_block_reason(s) is None


def test_blaxel_auth_failure_detector_401() -> None:
    class R:
        status_code = 401
        text = ""

    e = Exception("nope")
    e.response = R()  # type: ignore[attr-defined]
    assert br._blaxel_error_looks_like_auth_failure(e)


def test_blaxel_auth_failure_detector_message() -> None:
    assert br._blaxel_error_looks_like_auth_failure(RuntimeError("Authorization failed"))


def test_settings_post_init_exports_blaxel_to_os(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blaxel SDK reads ``os.environ``; Koraku must mirror pydantic-loaded values there."""
    from koraku.core.config import Settings

    monkeypatch.delenv("BL_API_KEY", raising=False)
    monkeypatch.delenv("BL_WORKSPACE", raising=False)
    Settings(bl_api_key="koraku-test-key", bl_workspace="koraku-test-ws")
    assert os.environ["BL_API_KEY"] == "koraku-test-key"
    assert os.environ["BL_WORKSPACE"] == "koraku-test-ws"
