"""Automation agent context uses the automation row org, not only personal org."""
from __future__ import annotations

import pytest

from koraku.core.tenant import effective_tenant_org_id, reset_tenant_org_id
from koraku_cloud.automations.run_context import (
    prepare_automation_agent_context,
    reset_automation_tenant,
)


@pytest.mark.asyncio
async def test_prepare_automation_context_uses_row_org_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _should_not_run(_uid: str) -> str:
        raise AssertionError("ensure_personal_org_sync must not run when org_id is set")

    monkeypatch.setattr(
        "koraku_cloud.automations.run_context.ensure_personal_org_sync",
        _should_not_run,
    )
    monkeypatch.setattr(
        "koraku_cloud.automations.run_context.supabase_personalization_configured",
        lambda: False,
    )

    org_id, _account_p, org_skills, tenant_tok = await prepare_automation_agent_context(
        "user-1",
        org_id="21ccb3a7-6567-49ea-9885-094673275af2",
    )
    assert org_skills == []
    try:
        assert org_id == "21ccb3a7-6567-49ea-9885-094673275af2"
        assert effective_tenant_org_id() == "21ccb3a7-6567-49ea-9885-094673275af2"
    finally:
        reset_automation_tenant(tenant_tok)
