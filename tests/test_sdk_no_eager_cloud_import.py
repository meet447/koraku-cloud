"""SDK package must not require koraku_cloud at import time."""
from __future__ import annotations

import sys


def _purge_koraku_cloud() -> None:
    for name in list(sys.modules):
        if name == "koraku_cloud" or name.startswith("koraku_cloud."):
            del sys.modules[name]


def test_request_auth_import_without_koraku_cloud() -> None:
    _purge_koraku_cloud()
    sys.modules.pop("koraku.core.request_auth", None)
    import koraku.core.request_auth  # noqa: F401

    assert "koraku_cloud" not in sys.modules
