"""Resolve authentication + tenant context for HTTP routes."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from koraku.core.auth import AuthResult, auth_error_detail, verify_request_auth
from koraku.core.config import settings
from koraku.core.tenant import TenantContext
from koraku.profiles import is_cloud_profile


@dataclass(frozen=True)
class ResolvedRequestAuth:
    auth: AuthResult
    tenant: TenantContext

    @property
    def sub(self) -> str | None:
        return self.auth.sub

    @property
    def org_id(self) -> str | None:
        return self.tenant.org_id

    @property
    def auth_ok(self) -> bool:
        return self.auth.ok

    def require_chat_access(self) -> None:
        if not settings.require_auth_for_chat:
            return
        if (settings.auth_backend or "").strip().lower() == "none":
            return
        if not self.auth_ok or self.auth.reason == "ok_anonymous":
            raise HTTPException(
                status_code=401,
                detail=auth_error_detail(self.auth.reason),
            )
        if self.auth.reason != "ok":
            return
        if not self.tenant.org_id:
            if is_cloud_profile() and (settings.auth_backend or "").strip().lower() == "supabase":
                raise HTTPException(
                    status_code=403,
                    detail="Organization context is required. Sign in again or contact support.",
                )


def _resolve_org_for_sub(request: Request, sub: str) -> tuple[str | None, str | None]:
    """Resolve org id via Supabase tenant store (cloud + supabase auth only)."""
    if not is_cloud_profile():
        return None, None
    if (settings.auth_backend or "").strip().lower() != "supabase":
        return None, None
    from koraku_cloud.integrations.supabase_tenant import parse_org_header, resolve_org_id_sync

    requested = parse_org_header(request.headers)
    return resolve_org_id_sync(sub, requested)


def resolve_request_auth(request: Request) -> ResolvedRequestAuth:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    auth = verify_request_auth(auth_header)
    org_id: str | None = None
    if auth.sub:
        org_id, reason = _resolve_org_for_sub(request, auth.sub)
        if not org_id and reason is not None:
            if reason == "org_forbidden":
                raise HTTPException(status_code=403, detail="You do not have access to this organization.")
            raise HTTPException(
                status_code=503,
                detail="Tenant service unavailable. Check Supabase configuration.",
            )
    return ResolvedRequestAuth(auth=auth, tenant=TenantContext(org_id=org_id, user_id=auth.sub))
