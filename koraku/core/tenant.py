"""Per-request tenant (organization) context."""
from __future__ import annotations

import contextvars
from contextvars import Token
from dataclasses import dataclass

_tenant_org: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "koraku_tenant_org_id",
    default=None,
)

ORG_ID_HEADER = "x-koraku-org-id"


@dataclass(frozen=True)
class TenantContext:
    """Resolved organization + user for a single HTTP/agent request."""

    org_id: str | None
    user_id: str | None

    @property
    def is_complete(self) -> bool:
        return bool(self.org_id and self.user_id)

    def storage_scope_id(self) -> str:
        """Blaxel paths and other tenant-scoped storage keys."""
        if self.org_id and self.user_id:
            return f"{self.org_id}/{self.user_id}"
        if self.user_id:
            return self.user_id
        raise RuntimeError("Authenticated user required for tenant-scoped storage.")


def set_tenant_org_id(org_id: str | None) -> Token | None:
    if not org_id or not str(org_id).strip():
        return None
    return _tenant_org.set(str(org_id).strip())


def reset_tenant_org_id(token: Token | None) -> None:
    if token is not None:
        _tenant_org.reset(token)


def effective_tenant_org_id() -> str | None:
    ctx = _tenant_org.get()
    if ctx and str(ctx).strip():
        return str(ctx).strip()
    return None
