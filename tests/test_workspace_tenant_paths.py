"""Workspace API must use the same Blaxel session path as chat (org-scoped user id)."""
from __future__ import annotations

import re
from types import SimpleNamespace

from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.integrations.blaxel_runtime import session_workspace_root_posix
from koraku.integrations.cloud_user import effective_cloud_user_id, reset_cloud_user_id, set_cloud_user_id


def test_session_workspace_differs_with_and_without_tenant_org() -> None:
    settings = SimpleNamespace(blaxel_sandbox_workdir="/tmp")
    org = "21ccb3a7-6567-49ea-9885-094673275af2"
    user = "9c77f10c-fc6a-402f-8749-e3e65779b688"
    sid = "550e8400-e29b-41d4-a716-446655440000"

    cloud_tok = set_cloud_user_id(user)
    org_tok = set_tenant_org_id(org)
    try:
        with_org = session_workspace_root_posix(effective_cloud_user_id(), sid, settings)
    finally:
        reset_tenant_org_id(org_tok)
        reset_cloud_user_id(cloud_tok)

    cloud_tok2 = set_cloud_user_id(user)
    try:
        without_org = session_workspace_root_posix(effective_cloud_user_id(), sid, settings)
    finally:
        reset_cloud_user_id(cloud_tok2)

    user_seg = re.sub(r"[^a-zA-Z0-9_.-]+", "-", f"{org}/{user}".strip())[:64]
    assert with_org == f"/tmp/koraku/users/{user_seg}/sessions/{sid}"
    assert without_org == f"/tmp/koraku/users/{user}/sessions/{sid}"
    assert with_org != without_org
