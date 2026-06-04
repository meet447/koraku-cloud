from koraku.core.models import AgentMessage
from koraku.credits.calculator import UsageAccumulator, compute_credits
from koraku.credits.token_estimator import (
    count_text,
    estimate_llm_round,
    estimate_messages_tokens,
    normalize_provider_usage,
)


def test_count_text_fallback_non_empty() -> None:
    assert count_text("abcd") >= 1
    assert count_text("") == 0


def test_estimate_messages_tokens_includes_system() -> None:
    msgs = [AgentMessage(role="user", content="hello")]
    base = estimate_messages_tokens(msgs)
    with_system = estimate_messages_tokens(msgs, system_prompt="You are helpful.")
    assert with_system > base


def test_normalize_provider_usage_openai_shape() -> None:
    norm = normalize_provider_usage({"prompt_tokens": 1200, "completion_tokens": 300})
    assert norm["input_tokens"] == 1200
    assert norm["output_tokens"] == 300


def test_compute_credits_uses_estimated_when_provider_missing() -> None:
    usage = UsageAccumulator(estimated_input_tokens=2000, estimated_output_tokens=500)
    assert usage.token_source == "estimated"
    assert usage.billing_input_tokens == 2000
    assert usage.billing_output_tokens == 500
    assert compute_credits(usage) == 5  # 2 + 1 token credits, floored to minimum 5


def test_billing_prefers_provider_over_estimate() -> None:
    usage = UsageAccumulator(
        input_tokens=1000,
        estimated_input_tokens=9000,
        output_tokens=0,
        estimated_output_tokens=4000,
    )
    assert usage.billing_input_tokens == 1000
    assert usage.billing_output_tokens == 4000
    assert usage.token_source == "provider"


def test_estimate_llm_round() -> None:
    est_in, est_out = estimate_llm_round(
        messages=[AgentMessage(role="user", content="ping")],
        system_prompt="sys",
        tool_schemas=None,
        assistant_content=[{"type": "text", "text": "pong"}],
        model="gpt-4",
        native_tools=False,
    )
    assert est_in > 0
    assert est_out > 0
