"""iMessage Blaxel workspace paths."""
from __future__ import annotations

from types import SimpleNamespace

from koraku.channels.imessage_sandbox import imessage_workspace_root
from koraku.integrations.blaxel_runtime import imessage_workspace_root_posix


def test_imessage_workspace_root_separate_from_web_sessions() -> None:
    cfg = SimpleNamespace(blaxel_sandbox_workdir="/tmp")
    uid = "user-abc"
    thread = "550e8400-e29b-41d4-a716-446655440000"
    root = imessage_workspace_root_posix(uid, thread, cfg)  # type: ignore[arg-type]
    assert root == "/tmp/koraku/users/user-abc/imessage/550e8400-e29b-41d4-a716-446655440000"
    assert "/sessions/" not in root
    assert imessage_workspace_root(uid, thread, cfg) == root  # type: ignore[arg-type]
