"""Load chat-parity context (org, profile, memory, sandbox) for automation runs."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from koraku.core.config import settings
from koraku.integrations.blaxel_runtime import cloud_blaxel_block_reason, ensure_chat_sandbox
from koraku.integrations.cloud_user import effective_cloud_user_id
from koraku.integrations.supabase_personalization import (
    fetch_personalization_sync,
    supabase_personalization_configured,
)
from koraku.integrations.supabase_tenant import ensure_personal_org_sync
from koraku.integrations.supermemory_client import fetch_learned_context_sync, supermemory_configured
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id

log = logging.getLogger(__name__)


async def prepare_automation_agent_context(
    user_id: str,
    session_id: str,
    *,
    spec_query: str | None = None,
) -> tuple[
    str | None,
    dict[str, str] | None,
    str | None,
    Any | None,
    Any | None,
]:
    """
    Returns ``(org_id, account_personalization, learned_memory_section, cloud_sandbox, tenant_token)``.

    ``tenant_token`` must be reset via ``reset_tenant_org_id`` in a ``finally`` block.
    """
    org_id = await asyncio.to_thread(ensure_personal_org_sync, user_id)
    tenant_token = set_tenant_org_id(org_id) if org_id else None

    account_p: dict[str, str] | None = None
    if supabase_personalization_configured():
        fetched = await asyncio.to_thread(fetch_personalization_sync, user_id)
        account_p = (
            fetched if fetched is not None else {"agent_name": "", "memory": "", "soul": ""}
        )

    learned_memory_section: str | None = None
    if supermemory_configured():
        section = await asyncio.to_thread(
            fetch_learned_context_sync,
            user_id,
            org_id=org_id,
            query=(spec_query or "").strip() or None,
        )
        learned_memory_section = section.strip() or None

    cloud_sandbox: Any | None = None
    if not cloud_blaxel_block_reason(settings):
        try:
            ready_timeout = max(5.0, float(settings.blaxel_sandbox_ready_timeout_seconds))
            cloud_sandbox = await asyncio.wait_for(
                ensure_chat_sandbox(
                    session_id,
                    settings,
                    user_id=effective_cloud_user_id(),
                ),
                timeout=ready_timeout,
            )
        except Exception as e:
            log.warning("automation sandbox unavailable session=%s: %s", session_id, e)

    return org_id, account_p, learned_memory_section, cloud_sandbox, tenant_token


def reset_automation_tenant(tenant_token: Any | None) -> None:
    if tenant_token is not None:
        reset_tenant_org_id(tenant_token)
