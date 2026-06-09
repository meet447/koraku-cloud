"""Profile enrichment for onboarding (public links → About summary)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from koraku.core.auth import auth_error_detail
from koraku.core.request_auth import resolve_request_auth
from koraku_cloud.integrations.profile_enrichment import (
    ProfileLinkInput,
    enrich_profile_from_links,
)

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileLinkBody(BaseModel):
    kind: Literal["linkedin", "x", "custom"]
    url: str = Field(min_length=1, max_length=2048)
    label: str | None = Field(default=None, max_length=80)


class ProfileEnrichBody(BaseModel):
    user_name: str | None = Field(default=None, max_length=120)
    existing_about: str | None = Field(default=None, max_length=8000)
    additional_info: str | None = Field(default=None, max_length=4000)
    help_with: list[str] = Field(default_factory=list, max_length=12)
    links: list[ProfileLinkBody] = Field(default_factory=list, max_length=5)


def _auth_401(reason: str) -> HTTPException:
    return HTTPException(status_code=401, detail=auth_error_detail(reason))


@router.post("/enrich")
async def profile_enrich(request: Request, body: ProfileEnrichBody):
    """Fetch public links and draft an About blurb (preview only; not persisted)."""
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok:
        raise _auth_401(resolved.auth.reason)
    resolved.require_chat_access()

    links = [
        ProfileLinkInput(kind=item.kind, url=item.url, label=item.label)
        for item in body.links
    ]
    help_with = [item.strip() for item in body.help_with if item and item.strip()]
    try:
        result = await enrich_profile_from_links(
            links,
            user_name=body.user_name,
            existing_about=body.existing_about,
            additional_info=body.additional_info,
            help_with=help_with,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Profile enrichment failed: {e}") from e

    return {
        "about": result.about,
        "link_results": [
            {
                "kind": row.kind,
                "url": row.url,
                "label": row.label,
                "status": row.status,
                "summary": row.summary,
                "error": row.error,
            }
            for row in result.link_results
        ],
    }
