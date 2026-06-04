"""Shared Cloud Supabase auth scope dependency."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from koraku.core.config import reset_cloud_binding
from koraku.core.product_hooks import clear_product_hooks
from koraku_cloud.api.auth_scope import _resolve_authenticated_org


def test_resolve_org_forbidden_returns_403(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_cloud_binding()
    clear_product_hooks()

    class _Req:
        headers: dict[str, str] = {"X-Koraku-Org-Id": "00000000-0000-0000-0000-000000000099"}

    monkeypatch.setattr(
        "koraku_cloud.api.auth_scope.verify_request_auth",
        lambda _auth: type("R", (), {"ok": True, "sub": "user-1", "reason": "ok"})(),
    )
    monkeypatch.setattr(
        "koraku_cloud.api.auth_scope.resolve_org_id_sync",
        lambda _uid, _req: (None, "org_forbidden"),
    )

    with pytest.raises(HTTPException) as exc:
        _resolve_authenticated_org(_Req(), "Bearer x")
    assert exc.value.status_code == 403
