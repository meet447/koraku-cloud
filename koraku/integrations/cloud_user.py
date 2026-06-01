"""Resolved cloud user id for Blaxel workspace layout (tenant-scoped when org context is set)."""
from __future__ import annotations

import contextvars
from contextvars import Token

from koraku.core.tenant import TenantContext, effective_tenant_org_id

_cloud_uid: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "koraku_cloud_uid",
    default=None,
)


def set_cloud_user_id(user_id: str | None) -> Token | None:
    """Bind Blaxel workspace paths to a signed-in user for the current async context."""
    if not user_id or not str(user_id).strip():
        return None
    return _cloud_uid.set(str(user_id).strip())


def reset_cloud_user_id(token: Token | None) -> None:
    if token is not None:
        _cloud_uid.reset(token)


def effective_auth_user_sub() -> str:
    """Raw Supabase ``sub`` for the current request (not the Blaxel storage scope)."""
    ctx = _cloud_uid.get()
    if not ctx or not str(ctx).strip():
        raise RuntimeError("Authenticated user required.")
    return str(ctx).strip()


def effective_cloud_user_id() -> str:
    """Per-request storage scope (``org_id/user_id``) for sandbox paths."""
    org = effective_tenant_org_id()
    uid = effective_auth_user_sub()
    if org:
        return TenantContext(org_id=org, user_id=uid).storage_scope_id()
    return uid
