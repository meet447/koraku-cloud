from koraku.credits.calculator import UsageAccumulator, compute_credits


def test_compute_credits_tokens_and_tools() -> None:
    usage = UsageAccumulator(
        input_tokens=3000,
        output_tokens=800,
        tool_counts={"WebSearch": 1},
    )
    assert compute_credits(usage) == 35  # 3 + 2 + 30 = 35, min 5


def test_compute_credits_images() -> None:
    usage = UsageAccumulator(image_count=2)
    assert compute_credits(usage) == 100  # 50 * 2


def test_compute_credits_empty_run() -> None:
    assert compute_credits(UsageAccumulator()) == 0


def test_compute_credits_estimated_tokens_min_charge() -> None:
    usage = UsageAccumulator(estimated_input_tokens=1500, estimated_output_tokens=400)
    assert compute_credits(usage) == 5
