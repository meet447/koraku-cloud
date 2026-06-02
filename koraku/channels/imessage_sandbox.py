"""Blaxel workspace provisioning for iMessage / SMS turns."""
from __future__ import annotations

import logging
from typing import Any

from koraku.core.config import Settings, settings
from koraku.integrations.blaxel_runtime import (
    cloud_blaxel_block_reason,
    ensure_imessage_sandbox,
    imessage_workspace_root_posix,
)

log = logging.getLogger(__name__)


def imessage_blaxel_available(cfg: Settings | None = None) -> bool:
    return cloud_blaxel_block_reason(cfg or settings) is None


def imessage_workspace_root(user_id: str, thread_id: str, cfg: Settings | None = None) -> str:
    return imessage_workspace_root_posix(user_id, thread_id, cfg or settings)


async def prepare_imessage_sandbox(
    user_id: str,
    thread_id: str,
    cfg: Settings | None = None,
) -> tuple[Any | None, str | None]:
    """Eagerly attach the user's VM and dedicated iMessage folder. Returns (sandbox, root) or (None, None)."""
    cfg = cfg or settings
    if not imessage_blaxel_available(cfg):
        return None, None
    try:
        sb, root = await ensure_imessage_sandbox(thread_id, cfg, user_id=user_id)
        log.info(
            "imessage sandbox ready user=%s thread=%s root=%s",
            user_id[:12] if user_id else "",
            thread_id[:12] if thread_id else "",
            root,
        )
        return sb, root
    except Exception as e:
        log.warning(
            "imessage sandbox ensure failed user=%s thread=%s: %s",
            user_id[:12] if user_id else "",
            thread_id[:12] if thread_id else "",
            e,
        )
        return None, None
