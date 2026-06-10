"""Progressive skills, credit reserves, and automation usage tracking."""
from __future__ import annotations

from koraku.agent.budget import credit_reserve_for_task_class
from koraku.core.config import bind_cloud_settings, configure_sdk, reset_cloud_binding
from koraku.core.product_hooks import ProductHooks, clear_product_hooks, register_product_hooks
from koraku.core.sdk_settings import SdkSettings
from koraku.credits.usage_tracker import RunUsageTracker
from koraku.inert_cloud_settings import CloudSettings
from koraku.tools import skills


def test_credit_reserve_for_task_class() -> None:
    reset_cloud_binding()
    bind_cloud_settings(
        CloudSettings.model_construct(
            credits_min_reserve=500,
            credits_min_reserve_research=2500,
            credits_min_reserve_automation=1500,
        )
    )
    from koraku.core.config import configure_sdk

    configure_sdk(SdkSettings())
    assert credit_reserve_for_task_class("standard") == 500
    assert credit_reserve_for_task_class("research") == 2500
    assert credit_reserve_for_task_class("automation") == 1500
    reset_cloud_binding()


def test_run_usage_tracker_ingests_tool_and_llm_events() -> None:
    tracker = RunUsageTracker()
    tracker.ingest(
        {
            "type": "agent.llm_usage_estimate",
            "data": {"input_tokens": 100, "output_tokens": 50},
        }
    )
    tracker.ingest(
        {
            "type": "tool_execution",
            "data": {"id": "tu_1", "tool": "WebSearch"},
        }
    )
    tracker.ingest(
        {
            "type": "tool_execution",
            "data": {"id": "tu_1", "tool": "WebSearch"},
        }
    )
    assert tracker.usage.estimated_input_tokens == 100
    assert tracker.usage.estimated_output_tokens == 50
    assert tracker.usage.tool_counts.get("WebSearch") == 1


def test_cloud_skill_index_not_full_body() -> None:
    clear_product_hooks()
    skills._skill_catalog_cache.clear()
    register_product_hooks(ProductHooks())
    text = skills.load_skill_prompt_section(
        "/tmp/workspace",
        cloud_skills=[
            {
                "slug": "weekly-plan",
                "name": "Weekly plan",
                "description": "Plan the week",
                "body": "SECRET FULL BODY that should not appear in index",
            }
        ],
    )
    assert "Agent skills (index)" in text
    assert "SkillLoad" in text
    assert "`weekly-plan`" in text
    assert "Plan the week" in text
    assert "SECRET FULL BODY" not in text
    clear_product_hooks()
    skills._skill_catalog_cache.clear()


def test_resolve_skill_body_from_bound_org_skills() -> None:
    token = skills.bind_org_skills(
        [
            {
                "slug": "demo",
                "name": "Demo",
                "description": "Demo skill",
                "body": "Do the demo steps.",
            }
        ]
    )
    try:
        body = skills.resolve_skill_body("demo", "/tmp/ws")
        assert body is not None
        assert "Do the demo steps." in body
    finally:
        skills.reset_org_skills(token)
