"""Cloud chat must not fall back to host disk when Blaxel is not fully configured."""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from koraku.integrations import blaxel_runtime as br
from koraku.integrations.cloud_user import (
    effective_auth_user_sub,
    effective_cloud_user_id,
    reset_cloud_user_id,
    set_cloud_user_id,
)
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id


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


def test_effective_auth_user_sub_ignores_org_storage_scope() -> None:
    """Supabase rows use auth sub; Blaxel paths use org/user — do not mix them."""
    t = set_cloud_user_id("9c77f10c-fc6a-402f-8749-e3e65779b688")
    org_t = set_tenant_org_id("21ccb3a7-6567-49ea-9885-094673275af2")
    try:
        assert (
            effective_cloud_user_id()
            == "21ccb3a7-6567-49ea-9885-094673275af2/9c77f10c-fc6a-402f-8749-e3e65779b688"
        )
        assert effective_auth_user_sub() == "9c77f10c-fc6a-402f-8749-e3e65779b688"
    finally:
        reset_tenant_org_id(org_t)
        reset_cloud_user_id(t)


def test_automation_agent_tools_uid_uses_auth_sub() -> None:
    from koraku_cloud.automations import agent_tools

    t = set_cloud_user_id("user-uuid")
    org_t = set_tenant_org_id("org-uuid")
    try:
        assert agent_tools._uid() == "user-uuid"
    finally:
        reset_tenant_org_id(org_t)
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


@pytest.mark.asyncio
async def test_cloud_file_tool_block_when_blaxel_required(monkeypatch: pytest.MonkeyPatch) -> None:
    from koraku.agent.runtime_context import bind_execution_target, reset_execution_target
    from koraku.integrations.blaxel_lazy import cloud_file_tool_block_reason

    async def _no_ensure() -> bool:
        return False

    monkeypatch.setattr(
        "koraku.integrations.blaxel_lazy.settings",
        SimpleNamespace(blaxel_cloud_sandbox_enabled=True),
    )
    monkeypatch.setattr(
        "koraku.integrations.blaxel_lazy.get_active_blaxel_sandbox",
        lambda: None,
    )
    monkeypatch.setattr(
        "koraku.integrations.blaxel_lazy.ensure_blaxel_for_file_tool",
        _no_ensure,
    )
    monkeypatch.setattr(
        "koraku.integrations.blaxel_lazy.cloud_blaxel_block_reason",
        lambda _s: None,
    )
    monkeypatch.setattr(
        "koraku.integrations.blaxel_lazy.cloud_file_tools_use_blaxel",
        lambda: True,
    )
    tok = bind_execution_target("cloud")
    try:
        msg = await cloud_file_tool_block_reason(try_ensure=True)
    finally:
        reset_execution_target(tok)
    assert msg is not None
    assert "Blaxel sandbox" in msg


@pytest.mark.asyncio
async def test_cloud_file_tool_block_even_when_blaxel_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sandbox mode (execution_target=cloud) must never fall back to host disk."""
    from koraku.agent.runtime_context import bind_execution_target, reset_execution_target
    from koraku.integrations.blaxel_lazy import cloud_file_tool_block_reason

    monkeypatch.setattr(
        "koraku.integrations.blaxel_lazy.settings",
        SimpleNamespace(blaxel_cloud_sandbox_enabled=False),
    )
    monkeypatch.setattr(
        "koraku.integrations.blaxel_lazy.cloud_blaxel_block_reason",
        lambda _s: "Sandbox mode uses a Blaxel VM only.",
    )
    tok = bind_execution_target("cloud")
    try:
        msg = await cloud_file_tool_block_reason(try_ensure=False)
    finally:
        reset_execution_target(tok)
    assert msg is not None
    assert "Blaxel" in msg


def test_settings_post_init_exports_blaxel_to_os(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blaxel SDK reads ``os.environ``; Koraku must mirror pydantic-loaded values there."""
    from koraku.core.config import Settings

    monkeypatch.delenv("BL_API_KEY", raising=False)
    monkeypatch.delenv("BL_WORKSPACE", raising=False)
    Settings(bl_api_key="koraku-test-key", bl_workspace="koraku-test-ws")
    assert os.environ["BL_API_KEY"] == "koraku-test-key"
    assert os.environ["BL_WORKSPACE"] == "koraku-test-ws"
