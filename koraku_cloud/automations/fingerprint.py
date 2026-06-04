"""Stable fingerprints for automation run summaries (diff vs last success)."""
from __future__ import annotations

import hashlib
import re


def normalize_summary_for_fingerprint(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t[:8000]


def summary_fingerprint(text: str) -> str:
    norm = normalize_summary_for_fingerprint(text)
    if not norm:
        return ""
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def outcome_label(
    *,
    status: str,
    fingerprint: str,
    last_success_fingerprint: str | None,
) -> str | None:
    if status != "success" or not fingerprint:
        return None
    prev = (last_success_fingerprint or "").strip()
    if not prev:
        return "new"
    if fingerprint == prev:
        return "unchanged"
    return "changed"
