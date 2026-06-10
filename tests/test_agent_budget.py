"""Agent harness budgets and Composio goal classification."""
from __future__ import annotations

from koraku.agent.budget import (
    LoopTracker,
    classify_composio_goal,
    classify_turn_task,
    composio_max_rounds_for_goal,
    credit_reserve_for_task_class,
    dispatcher_mode_active,
    resolve_turn_limits,
    tools_for_composio_worker,
    tools_for_dispatcher_turn,
)
from koraku.tools.tool_def import Tool


def _fake_tool(name: str) -> Tool:
    return Tool(name=name, description=name, input_schema={"type": "object", "properties": {}}, handler=lambda **_: "")


def test_credit_reserve_for_task_class_research_beats_base(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "credits_min_reserve", 500)
    monkeypatch.setattr(settings, "credits_min_reserve_research", 2500)
    monkeypatch.setattr(settings, "credits_min_reserve_automation", 1500)
    assert credit_reserve_for_task_class("standard") == 500
    assert credit_reserve_for_task_class("research") == 2500
    assert credit_reserve_for_task_class("automation") == 1500


def test_classify_turn_task_standard() -> None:
    assert classify_turn_task("check my gmail and mark as read") == "standard"
    assert classify_turn_task("hello there") == "standard"
    assert (
        classify_turn_task("whats the latest news related to re neet site being hacked")
        == "standard"
    )


def test_classify_turn_task_research() -> None:
    assert classify_turn_task("research the best pricing for " + "x " * 30) == "research"


def test_classify_composio_goal_simple() -> None:
    assert classify_composio_goal("List unread Gmail and mark all as read") == "integration_simple"


def test_classify_composio_goal_compose() -> None:
    assert classify_composio_goal("Draft a reply to the latest thread") == "integration_compose"


def test_composio_simple_fewer_rounds() -> None:
    simple = composio_max_rounds_for_goal("mark inbox as read")
    full = composio_max_rounds_for_goal(
        "Investigate every label in the account and produce a full audit spreadsheet"
    )
    assert simple < full


def test_tools_for_composio_worker_simple_is_composio_only() -> None:
    base = [_fake_tool("WebSearch"), _fake_tool("TodoWrite")]
    comp = [_fake_tool("GMAIL_FETCH_EMAILS")]
    out = tools_for_composio_worker(base, comp, "check unread email")
    assert [t.name for t in out] == ["GMAIL_FETCH_EMAILS"]


def test_loop_tracker_detects_repeat() -> None:
    tr = LoopTracker()
    tu = {"name": "GMAIL_FETCH", "input": {"max_results": 5}}
    tr.record([tu])
    assert not tr.has_repeat()
    tr.record([tu])
    assert tr.has_repeat()


def test_resolve_turn_limits_standard_for_chat() -> None:
    mode, limits = resolve_turn_limits("any unread in my inbox?", None)
    assert mode == "standard"
    assert limits.task_class == "standard"
    assert limits.max_rounds >= 10


def test_dispatcher_never_strips_tools(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "koraku_dispatcher_mode", True)
    monkeypatch.setattr(settings, "composio_subagent_mode", True)
    base = [
        _fake_tool("WebSearch"),
        _fake_tool("MemorySearch"),
        _fake_tool("ComposioRun"),
        _fake_tool("Read"),
    ]
    for task_class in ("standard", "integration", "quick", "research"):
        out = tools_for_dispatcher_turn(base, task_class=task_class)
        assert [t.name for t in out] == ["WebSearch", "MemorySearch", "ComposioRun", "Read"]


def test_dispatcher_mode_requires_subagent_flag(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "koraku_dispatcher_mode", True)
    monkeypatch.setattr(settings, "composio_subagent_mode", False)
    assert dispatcher_mode_active() is False
