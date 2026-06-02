"""Load chat-parity context (org, profile, sandbox) for automation runs."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from koraku.integrations.supabase_personalization import (
    fetch_personalization_sync,
    supabase_personalization_configured,
)
from koraku.integrations.supabase_tenant import ensure_personal_org_sync
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id

log = logging.getLogger(__name__)


async def prepare_automation_agent_context(
    user_id: str,
    *,
    spec_query: str | None = None,
) -> tuple[str | None, dict[str, str] | None, Any | None]:
    """
    Returns ``(org_id, account_personalization, tenant_token)``.

    Blaxel and Supermemory are lazy (tools attach / search on demand).

    ``tenant_token`` must be reset via ``reset_tenant_org_id`` in a ``finally`` block.
    """
    _ = spec_query
    org_id = await asyncio.to_thread(ensure_personal_org_sync, user_id)
    tenant_token = set_tenant_org_id(org_id) if org_id else None

    account_p: dict[str, str] | None = None
    if supabase_personalization_configured():
        fetched = await asyncio.to_thread(
            fetch_personalization_sync, user_id, org_id=org_id
        )
        account_p = (
            fetched if fetched is not None else {"agent_name": "", "memory": "", "soul": ""}
        )

    return org_id, account_p, tenant_token


def reset_automation_tenant(tenant_token: Any | None) -> None:
    if tenant_token is not None:
        reset_tenant_org_id(tenant_token)
