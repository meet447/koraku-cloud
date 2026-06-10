"""Workhorse delegate tools and credit estimate guards."""
from __future__ import annotations

from koraku.credits.calculator import UsageAccumulator
from koraku.integrations.workhorse_prompt import workhorse_dispatcher_prompt_section
from koraku.tools.parallel_delegate_tool import PARALLEL_RUN_TOOL
from koraku.tools.workhorse_delegate_tool import WORKHORSE_RUN_TOOLS


def test_workhorse_tools_registered() -> None:
    names = {t.name for t in WORKHORSE_RUN_TOOLS}
    assert names == {"ResearchRun", "CodeRun", "VerifyGoal"}
    assert PARALLEL_RUN_TOOL.name == "ParallelRun"


def test_workhorse_prompt_section_mentions_delegates() -> None:
    text = workhorse_dispatcher_prompt_section()
    assert "ResearchRun" in text
    assert "CodeRun" in text
    assert "VerifyGoal" in text
    assert "ParallelRun" in text
    assert "Multi-deliverable playbook" in text
    assert "document" in text
    assert "presentation" in text


def test_add_estimated_round_skips_when_provider_usage_present() -> None:
    usage = UsageAccumulator()
    usage.add_turn_usage({"input_tokens": 100, "output_tokens": 50})
    usage.add_estimated_round(input_tokens=9000, output_tokens=4000)
    assert usage.estimated_input_tokens == 0
    assert usage.estimated_output_tokens == 0
    assert usage.billing_input_tokens == 100
    assert usage.billing_output_tokens == 50
