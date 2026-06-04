"""Automation webhook idempotency and rate-limit helpers."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from koraku_cloud.automations import webhook_guard as wg


def test_claim_idempotency_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wg, "_seen_idempotency", {})
    assert wg.claim_idempotency("k1") is True
    assert wg.claim_idempotency("k1") is False


def test_reject_duplicate_webhook_raises_409() -> None:
    with pytest.raises(HTTPException) as exc:
        wg.reject_duplicate_webhook()
    assert exc.value.status_code == 409
