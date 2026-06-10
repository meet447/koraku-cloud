"""Credit enforcement helpers for API routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import HTTPException

from koraku.credits.calculator import UsageAccumulator, compute_credits
from koraku.credits.store import (
    UsageSummary,
    credits_configured,
    fetch_activity_sync,
    fetch_summary_sync,
    pre_check_sync,
    settle_sync,
)


class OrgSuspendedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            detail={
                "code": "org_suspended",
                "message": "This workspace is suspended. Contact support.",
            },
        )


class CreditsExhaustedError(HTTPException):
    def __init__(self, summary: UsageSummary | None) -> None:
        detail: dict[str, Any] = {
            "code": "credits_exhausted",
            "message": "Monthly credit limit reached. Usage resets at the start of next month.",
        }
        if summary:
            detail["credits_used"] = summary.credits_used
            detail["credits_limit"] = summary.credits_limit
            detail["resets_in_days"] = summary.resets_in_days
            detail["period_end"] = summary.period_end
        super().__init__(status_code=402, detail=detail)


async def pre_check_org(org_id: str | None, *, reserve: int | None = None) -> UsageSummary | None:
    oid = (org_id or "").strip()
    if not oid or not credits_configured():
        return None
    allowed, summary = await asyncio.to_thread(pre_check_sync, oid, reserve=reserve)
    if not allowed:
        from koraku.credits.store import _org_suspended_sync

        if await asyncio.to_thread(_org_suspended_sync, oid):
            raise OrgSuspendedError()
        raise CreditsExhaustedError(summary)
    return summary


async def settle_run(
    org_id: str | None,
    *,
    run_id: str,
    usage: UsageAccumulator,
    kind: str = "chat",
    model: str = "",
    provider: str = "",
) -> dict[str, Any] | None:
    oid = (org_id or "").strip()
    rid = (run_id or "").strip()
    if not oid or not rid or not credits_configured():
        return None
    credits = compute_credits(usage)
    if credits <= 0:
        return None
    metadata = usage.to_metadata(run_id=rid, model=model, provider=provider)
    settled, summary = await asyncio.to_thread(
        settle_sync,
        oid,
        idempotency_key=f"run:{rid}",
        credits=credits,
        kind=kind,
        metadata=metadata,
    )
    if summary is None:
        return None
    return {
        "settled": settled,
        "credits_deducted": credits if settled else 0,
        "credits_used": summary.credits_used,
        "credits_limit": summary.credits_limit,
        "credits_remaining": summary.credits_remaining,
        "percent_used": summary.percent_used,
        "resets_in_days": summary.resets_in_days,
    }


async def get_usage_payload(org_id: str | None) -> dict[str, Any]:
    oid = (org_id or "").strip()
    if not oid or not credits_configured():
        return {
            "configured": False,
            "plan": "free",
            "credits_limit": 100_000,
            "credits_used": 0,
            "credits_remaining": 100_000,
            "percent_used": 0.0,
            "resets_in_days": 0,
            "activity": [],
        }
    summary = await asyncio.to_thread(fetch_summary_sync, oid)
    activity = await asyncio.to_thread(fetch_activity_sync, oid)
    if summary is None:
        return {
            "configured": True,
            "plan": "free",
            "credits_limit": 100_000,
            "credits_used": 0,
            "credits_remaining": 100_000,
            "percent_used": 0.0,
            "resets_in_days": 0,
            "activity": activity,
        }
    return {
        "configured": True,
        "plan": summary.plan,
        "credits_limit": summary.credits_limit,
        "credits_used": summary.credits_used,
        "credits_remaining": summary.credits_remaining,
        "percent_used": summary.percent_used,
        "period_start": summary.period_start,
        "period_end": summary.period_end,
        "resets_in_days": summary.resets_in_days,
        "activity": activity,
    }


def credits_summary_event(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    return {"type": "koraku.credits", "data": payload}
