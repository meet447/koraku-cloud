"""Workspace API must use iMessage Blaxel paths for iMessage threads."""
from __future__ import annotations

from types import SimpleNamespace

from koraku.integrations.blaxel_runtime import (
    imessage_workspace_root_posix,
    session_workspace_root_posix,
    workspace_root_posix_for_channel,
)
from koraku.integrations.cloud_user import (
    auth_user_id_from_storage_scope,
    workspace_path_user_id,
)


def test_workspace_root_posix_for_channel_imessage() -> None:
    cfg = SimpleNamespace(blaxel_sandbox_workdir="/tmp")
    uid = "user-abc"
    sid = "550e8400-e29b-41d4-a716-446655440000"
    im_root = workspace_root_posix_for_channel(uid, sid, "imessage", cfg)  # type: ignore[arg-type]
    web_root = workspace_root_posix_for_channel(uid, sid, "web", cfg)  # type: ignore[arg-type]
    assert im_root == imessage_workspace_root_posix(uid, sid, cfg)  # type: ignore[arg-type]
    assert web_root == session_workspace_root_posix(uid, sid, cfg)  # type: ignore[arg-type]
    assert im_root != web_root
    assert "/imessage/" in im_root
    assert "/sessions/" in web_root


def test_auth_user_id_from_org_storage_scope() -> None:
    org = "21ccb3a7-6567-49ea-9885-094673275af2"
    user = "9c77f10c-fc6a-402f-8749-e3e65779b688"
    scope = f"{org}/{user}"
    assert auth_user_id_from_storage_scope(scope) == user
    assert auth_user_id_from_storage_scope(user) == user


def test_workspace_path_user_id_imessage_uses_auth_sub_only() -> None:
    org = "21ccb3a7-6567-49ea-9885-094673275af2"
    user = "9c77f10c-fc6a-402f-8749-e3e65779b688"
    scope = f"{org}/{user}"
    cfg = SimpleNamespace(blaxel_sandbox_workdir="/tmp")
    sid = "9680ab8a-bc4b-4e5e-bd4e-9a30ea8ec7a3"
    path_uid = workspace_path_user_id(scope, "imessage")
    assert path_uid == user
    agent_root = imessage_workspace_root_posix(user, sid, cfg)  # type: ignore[arg-type]
    panel_root = workspace_root_posix_for_channel(path_uid, sid, "imessage", cfg)  # type: ignore[arg-type]
    assert panel_root == agent_root
    web_uid = workspace_path_user_id(scope, "web")
    assert web_uid == scope
    assert web_uid != path_uid
