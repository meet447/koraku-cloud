"""Shared FastAPI dependency: Supabase JWT + org membership + request context."""
from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from fastapi import Header, HTTPException, Request

from koraku.core.auth import auth_error_detail, verify_request_auth
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id
from koraku_cloud.integrations.supabase_tenant import parse_org_header, resolve_org_id_sync

PreCheck = Callable[[], None]


@dataclass(frozen=True)
class CloudUserScope:
    user_id: str
    org_id: str


def _raise_org_resolution_failure(*, reason: str | None) -> None:
    if reason == "org_forbidden":
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this organization.",
        )
    raise HTTPException(
        status_code=503,
        detail="Tenant service unavailable. Check Supabase configuration.",
    )


def _resolve_authenticated_org(
    request: Request,
    authorization: str | None,
) -> CloudUserScope:
    jwt_res = verify_request_auth(authorization)
    if not jwt_res.ok or not jwt_res.sub:
        status = 503 if jwt_res.reason == "no_secret" else 401
        detail = auth_error_detail(jwt_res.reason)
        raise HTTPException(
            status_code=status,
            detail=f"{detail} (code={jwt_res.reason})",
        )
    uid = jwt_res.sub
    requested_org = parse_org_header(request.headers)
    org_id, reason = resolve_org_id_sync(uid, requested_org)
    if not org_id:
        _raise_org_resolution_failure(reason=reason)
    return CloudUserScope(user_id=uid, org_id=org_id)


async def cloud_supabase_user_scope(
    request: Request,
    authorization: str | None = Header(None),
    *,
    pre_check: PreCheck | None = None,
) -> AsyncGenerator[CloudUserScope, None]:
    """Verify JWT, resolve org, bind cloud user + tenant for the request lifetime."""
    if pre_check is not None:
        pre_check()
    scope = _resolve_authenticated_org(request, authorization)
    cloud_tok = set_cloud_user_id(scope.user_id)
    tenant_tok = set_tenant_org_id(scope.org_id)
    try:
        yield scope
    finally:
        reset_tenant_org_id(tenant_tok)
        reset_cloud_user_id(cloud_tok)
