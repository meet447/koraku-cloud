"""Chat session hydration facade — product hooks when registered, else SDK path."""
from __future__ import annotations

from koraku.core.product_hooks import (
    after_turn_memory_ingest,
    fetch_account_personalization,
    hydrate_session_for_turn,
)

__all__ = [
    "after_turn_memory_ingest",
    "fetch_account_personalization",
    "hydrate_session_for_turn",
]
