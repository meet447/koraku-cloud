"""Optional dev server launcher (prefer ``./scripts/run-api.sh`` / uvicorn; not installed as a console script)."""
from __future__ import annotations

import os
import sys

import uvicorn

from koraku.core.config import settings


def _uvicorn_workers() -> int:
    raw = (os.environ.get("WEB_CONCURRENCY") or os.environ.get("UVICORN_WORKERS") or "1").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 1
    return max(1, min(n, 32))


def _uvicorn_reload() -> bool:
    if _uvicorn_workers() > 1:
        return False
    v = (os.environ.get("UVICORN_RELOAD") or "true").strip().lower()
    return v in {"1", "true", "yes", "on"}


def main() -> None:
    """Start the Koraku FastAPI server."""
    print(f"Koraku server Python: {sys.executable}")
    workers = _uvicorn_workers()
    reload = _uvicorn_reload()
    if workers > 1:
        print(
            f"Koraku server: {workers} worker processes (reload off). "
            "Use LB sticky sessions for /stream chat."
        )
    elif reload:
        print(
            "Koraku server: single process + autoreload (dev). "
            "Set WEB_CONCURRENCY=4 and UVICORN_RELOAD=false for load."
        )
    kw: dict = {
        "host": settings.host,
        "port": settings.port,
        "log_level": "info",
    }
    if workers > 1:
        kw["workers"] = workers
    else:
        kw["reload"] = reload
    target = (os.environ.get("KORAKU_SERVER_APP") or "").strip().lower()
    if target == "sdk":
        app_path = "koraku.server_sdk:app"
    elif target == "cloud":
        app_path = "koraku_cloud.app:app"
    else:
        import os

        app_path = (
            "koraku.server_sdk:app"
            if (os.environ.get("KORAKU_SERVER_APP") or "cloud").strip().lower() == "sdk"
            else "koraku_cloud.app:app"
        )
    print(f"Koraku server app: {app_path}")
    uvicorn.run(app_path, **kw)
