"""Runtime mode helpers (SDK vs Cloud product layer)."""
from __future__ import annotations

from koraku.core.config import is_cloud_configured


def is_cloud_profile(settings: object | None = None) -> bool:
    """True when the Cloud product settings layer is bound."""
    return is_cloud_configured()
