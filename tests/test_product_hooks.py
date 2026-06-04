"""Product hooks: SDK default vs Cloud registration."""
from __future__ import annotations

import pytest

from koraku.api.sdk_session_hydration import hydrate_sdk_session_for_turn
from koraku.core.config import reset_cloud_binding
from koraku.core.models import AgentMessage, SessionState
from koraku.core.product_hooks import clear_product_hooks, hydrate_session_for_turn, product_hooks_active
from koraku_cloud.bootstrap import bootstrap_cloud


@pytest.mark.asyncio
async def test_sdk_hydration_without_product_hooks() -> None:
    reset_cloud_binding()
    clear_product_hooks()
    session = SessionState(session_id="s1")
    report = await hydrate_session_for_turn(
        session,
        incoming_user_text="hi",
        auth_sub=None,
    )
    assert report.reason == "sdk_empty"
    assert not product_hooks_active()


@pytest.mark.asyncio
async def test_bootstrap_registers_product_hooks() -> None:
    reset_cloud_binding()
    clear_product_hooks()
    bootstrap_cloud()
    assert product_hooks_active()


def test_bootstrap_registers_health_and_tool_hooks() -> None:
    reset_cloud_binding()
    clear_product_hooks()
    bootstrap_cloud()
    from koraku.core.product_hooks import health_detail_extras, extra_agent_tools

    extras = health_detail_extras()
    assert "automations_supabase_configured" in extras
    names = {t.name for t in extra_agent_tools()}
    assert "AutomationsList" in names


@pytest.mark.asyncio
async def test_sdk_module_unchanged_for_embedders() -> None:
    session = SessionState(session_id="s2")
    session.messages.append(
        AgentMessage(role="user", content=[{"type": "text", "text": "prior"}])
    )
    report = await hydrate_sdk_session_for_turn(
        session,
        incoming_user_text="next",
        auth_sub=None,
    )
    assert report.reason == "warm"
    assert report.messages_loaded == 1
