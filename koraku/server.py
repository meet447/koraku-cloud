"""HTTP entry for this monorepo: Cloud product app (embeds SDK). Use ``KORAKU_SERVER_APP=sdk`` for SDK-only."""
from __future__ import annotations

import os


def create_app():
    override = (os.environ.get("KORAKU_SERVER_APP") or "cloud").strip().lower()
    if override == "sdk":
        from koraku.server_sdk import create_sdk_app

        return create_sdk_app()
    from koraku_cloud.app import create_cloud_app

    return create_cloud_app()


app = create_app()
