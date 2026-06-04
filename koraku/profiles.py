"""Runtime mode helpers (SDK vs Cloud product layer)."""
from __future__ import annotations

from koraku.core.product_hooks import product_hooks_active


def is_cloud_profile() -> bool:
    """True when Cloud product hooks are registered (SaaS server after ``bootstrap_cloud()``)."""
    return product_hooks_active()
