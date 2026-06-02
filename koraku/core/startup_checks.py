"""Production startup validation (Redis, etc.)."""
from __future__ import annotations

import logging
import os

from koraku.core.config import settings
from koraku.core import redis_client

log = logging.getLogger(__name__)


def _worker_count() -> int:
    raw = (os.environ.get("WEB_CONCURRENCY") or os.environ.get("UVICORN_WORKERS") or "1").strip()
    try:
        return max(1, min(int(raw), 32))
    except ValueError:
        return 1


def _requires_shared_redis() -> bool:
    backend = (settings.session_store_backend or "").strip().lower()
    detached = (settings.detached_run_store_backend or "auto").strip().lower()
    if backend == "redis":
        return True
    if detached == "redis":
        return True
    if detached == "auto" and redis_client.is_configured():
        return True
    return False


def assert_redis_for_multi_worker() -> None:
    """Raise when multiple workers need Redis but it is missing or unreachable."""
    if _worker_count() <= 1:
        return
    if not _requires_shared_redis():
        return
    if not redis_client.is_configured():
        raise RuntimeError(
            "WEB_CONCURRENCY > 1 requires REDIS_URL for session store and/or detached runs. "
            "Set REDIS_URL or run a single worker (WEB_CONCURRENCY=1)."
        )
    if redis_client.get_client() is None:
        raise RuntimeError(
            "REDIS_URL is set but Redis is unreachable. "
            "Fix connectivity before starting multiple API workers."
        )
    log.info("Redis connectivity verified for %s workers", _worker_count())
