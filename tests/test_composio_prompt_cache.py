"""Composio system-prompt slice caching and task-class variants."""

from __future__ import annotations

import time

import pytest

from koraku.integrations import composio as comp


@pytest.fixture(autouse=True)
def _clear_composio_prompt_cache() -> None:
    comp._prompt_section_cache.clear()
    comp._connections_cache.clear()
    yield
    comp._prompt_section_cache.clear()
    comp._connections_cache.clear()


def test_composio_prompt_section_for_turn_uses_quick_for_standard(monkeypatch) -> None:
    monkeypatch.setattr(comp, "is_configured", lambda: True)
    monkeypatch.setattr(comp.settings, "composio_subagent_mode", True)
    monkeypatch.setattr(comp, "user_id", lambda: "user-a")
    calls = {"quick": 0, "full": 0}

    def quick() -> str:
        calls["quick"] += 1
        return "QUICK\n"

    def full() -> str:
        calls["full"] += 1
        return "FULL\n"

    monkeypatch.setattr(comp, "composio_dispatcher_prompt_section_quick", quick)
    monkeypatch.setattr(comp, "composio_dispatcher_prompt_section", full)

    assert comp.composio_prompt_section_for_turn("standard") == "QUICK\n"
    assert comp.composio_prompt_section_for_turn("standard") == "QUICK\n"
    assert calls["quick"] == 1
    assert calls["full"] == 0

    assert comp.composio_prompt_section_for_turn("research") == "FULL\n"
    assert calls["full"] == 1


def test_composio_prompt_cache_invalidates_when_connection_cache_updates(monkeypatch) -> None:
    monkeypatch.setattr(comp, "is_configured", lambda: True)
    monkeypatch.setattr(comp.settings, "composio_subagent_mode", True)
    monkeypatch.setattr(comp, "user_id", lambda: "user-b")
    monkeypatch.setattr(comp, "composio_dispatcher_prompt_section_quick", lambda: "A\n")

    assert comp.composio_prompt_section_for_turn("standard") == "A\n"
    assert "user-b:quick" in comp._prompt_section_cache

    # Mirror invalidation in list_connections_summary after a fresh fetch.
    comp._connections_cache["user-b"] = (time.monotonic(), [])
    for suffix in ("quick", "full", "flat"):
        comp._prompt_section_cache.pop(f"user-b:{suffix}", None)

    monkeypatch.setattr(comp, "composio_dispatcher_prompt_section_quick", lambda: "B\n")
    assert comp.composio_prompt_section_for_turn("standard") == "B\n"
