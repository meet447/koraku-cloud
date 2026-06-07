"""Personalization from Supabase is reflected in the system prompt."""
from __future__ import annotations

from koraku.agent.run import build_system_prompt, format_working_memory_context


def test_build_system_prompt_account_profile_branch() -> None:
    s = build_system_prompt(
        "/tmp/ws",
        account_personalization={
            "agent_name": "HelperX",
            "memory": "User prefers concise answers.",
            "soul": "Warm and direct.",
        },
    )
    assert "HelperX" in s
    assert "User prefers concise answers." in s
    assert "Warm and direct." in s
    assert "Koraku account profile" in s


def test_build_system_prompt_daily_driver_contract() -> None:
    s = build_system_prompt(
        "/tmp/ws",
        account_personalization={"agent_name": "", "memory": "", "soul": ""},
        composio_section="",
    )

    assert "sovereign digital mind" in s
    assert "## Task & Tool Orchestration Modes" in s
    assert "## Memory (explicit + learned)" in s
    assert "**MemorySearch**" in s
    assert "**MemorySave**" in s
    assert "## Strict Behavioral Protocols" in s


def test_working_memory_context_is_bounded_and_recent() -> None:
    memory = [
        {"type": "content", "summary": f"finding {i} " + ("x" * 800)}
        for i in range(12)
    ]

    msg = format_working_memory_context(memory)

    assert msg is not None
    assert msg.role == "user"
    assert isinstance(msg.content, str)
    assert "## Transient Operational Insights (Current Turn)" in msg.content
    assert "finding 11" in msg.content
    assert "finding 0" not in msg.content
    assert len(msg.content) <= 8_500
