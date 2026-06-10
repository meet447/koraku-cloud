"""Detached run checkpoint save/load."""
from __future__ import annotations

import pytest

from koraku.core.models import AgentMessage, SessionState
from koraku.core.run_checkpoint import (
    load_checkpoint,
    mark_checkpoint_completed,
    reset_checkpoint_store,
    restore_session,
    save_checkpoint,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_checkpoint_store()
    yield
    reset_checkpoint_store()


@pytest.mark.asyncio
async def test_checkpoint_round_trip() -> None:
    session = SessionState(session_id="chat-1")
    session.add_message("user", "hello")
    session.step_count = 2
    await save_checkpoint(
        run_id="run-1",
        session=session,
        owner_sub="user-a",
        owner_org_id="org-1",
    )
    cp = await load_checkpoint("run-1", owner_org_id="org-1")
    assert cp is not None
    restored = restore_session(cp)
    assert restored.session_id == "chat-1"
    assert restored.step_count == 2
    assert len(restored.messages) == 1


@pytest.mark.asyncio
async def test_completed_checkpoint_not_loaded() -> None:
    session = SessionState(session_id="chat-1")
    await save_checkpoint(
        run_id="run-2",
        session=session,
        owner_sub=None,
        owner_org_id=None,
    )
    await mark_checkpoint_completed("run-2", owner_org_id=None)
    assert await load_checkpoint("run-2", owner_org_id=None) is None
