"""Chat latency heuristics."""
from __future__ import annotations

from koraku.api.chat_latency import should_defer_blaxel_provision
from koraku.agent.run import _step_budget
from koraku.core.config import Settings


def test_defer_blaxel_for_hello() -> None:
    assert should_defer_blaxel_provision(message="hello", has_images=False) is True
    assert should_defer_blaxel_provision(message="hi there!", has_images=False) is True


def test_no_defer_when_saving_files() -> None:
    assert (
        should_defer_blaxel_provision(
            message="create automation-ideas.md and save to my workspace",
            has_images=False,
        )
        is False
    )


def test_step_budget_standard_for_greeting() -> None:
    mode, steps = _step_budget("hello")
    assert mode == "standard"
    assert steps >= 10
