"""Org credit usage summary for the Koraku Cloud UI."""
from __future__ import annotations

from fastapi import APIRouter, Request

from koraku.core.request_auth import resolve_request_auth
from koraku.credits.service import get_usage_payload

router = APIRouter(tags=["usage"])


@router.get("/api/usage")
async def usage_summary(request: Request):
    resolved = resolve_request_auth(request)
    resolved.require_chat_access()
    return await get_usage_payload(resolved.org_id)
