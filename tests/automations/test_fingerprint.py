from koraku_cloud.automations.fingerprint import outcome_label, summary_fingerprint


def test_summary_fingerprint_stable() -> None:
    a = summary_fingerprint("Hello   world")
    b = summary_fingerprint("hello world")
    assert a == b
    assert len(a) == 16


def test_outcome_label() -> None:
    fp = summary_fingerprint("done")
    assert outcome_label(status="success", fingerprint=fp, last_success_fingerprint=None) == "new"
    assert outcome_label(status="success", fingerprint=fp, last_success_fingerprint=fp) == "unchanged"
    assert outcome_label(status="success", fingerprint=fp, last_success_fingerprint="other") == "changed"
    assert outcome_label(status="failed", fingerprint=fp, last_success_fingerprint=fp) is None
