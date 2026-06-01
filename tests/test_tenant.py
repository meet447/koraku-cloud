"""Tenant context helpers."""
from __future__ import annotations

from koraku.core.tenant import TenantContext


def test_tenant_storage_scope() -> None:
    ctx = TenantContext(
        org_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        user_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    assert ctx.storage_scope_id() == (
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    )
