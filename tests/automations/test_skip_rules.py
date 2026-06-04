from koraku_cloud.automations.skip_rules import evaluate_skip


def test_skip_when_run_in_progress() -> None:
    auto = {"status": "active", "consecutive_failures": 0}
    reason = evaluate_skip(auto, has_running_run=True, lock_busy=False)
    assert reason and "in progress" in reason


def test_skip_after_consecutive_failures() -> None:
    auto = {"status": "active", "consecutive_failures": 3, "max_failures_before_pause": 3}
    reason = evaluate_skip(auto, has_running_run=False, lock_busy=False)
    assert reason and "consecutive failures" in reason
