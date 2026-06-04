"""Safe path joins for session workspaces (SDK + embedders)."""
from __future__ import annotations

import posixpath

from fastapi import HTTPException


def safe_join_under_session_root(root: str, rel: str) -> str:
    """Resolve ``rel`` under ``root``; raises ``HTTPException`` if path escapes."""
    root = root.rstrip("/") or "/"
    rel = (rel or "").strip().replace("\\", "/").lstrip("/")
    if not rel:
        return root
    candidate = posixpath.normpath(posixpath.join(root, rel))
    prefix = root if root.endswith("/") else root + "/"
    if candidate == root or candidate.startswith(prefix):
        return candidate
    raise HTTPException(status_code=400, detail="path must stay under the session workspace")
