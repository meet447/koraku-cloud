"""Workspace API must use iMessage Blaxel paths for iMessage threads."""
from __future__ import annotations

from types import SimpleNamespace

from koraku.integrations.blaxel_runtime import (
    imessage_workspace_root_posix,
    session_workspace_root_posix,
    workspace_root_posix_for_channel,
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
