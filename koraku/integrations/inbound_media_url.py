"""SSRF-safe validation for inbound iMessage / SendBlue media URLs."""
from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

from koraku.core.config import settings

log = logging.getLogger(__name__)

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google",
        "169.254.169.254",
    }
)


def _host_allowlist() -> tuple[str, ...]:
    raw = (settings.sendblue_inbound_media_host_allowlist or "").strip()
    if not raw:
        return (
            "sendblue.co",
            "sendblue.com",
            "blob.core.windows.net",
            "amazonaws.com",
            "cloudfront.net",
            "googleusercontent.com",
            "storage.googleapis.com",
        )
    return tuple(h.strip().lower() for h in raw.split(",") if h.strip())


def _host_allowed(host: str) -> bool:
    h = host.lower().rstrip(".")
    if h in _BLOCKED_HOSTS:
        return False
    for suffix in _host_allowlist():
        if h == suffix or h.endswith(f".{suffix}"):
            return True
    return False


def _ip_is_blocked(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def validate_inbound_media_url(url: str) -> str | None:
    """
    Return the URL when safe to fetch server-side, else ``None``.

  - HTTPS only
    - Host must match allowlist (SendBlue CDNs by default)
    - Literal IP hosts must be public
    """
    raw = (url or "").strip()
    if not raw or len(raw) > 4096:
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    if parsed.scheme != "https":
        return None
    host = (parsed.hostname or "").strip()
    if not host or host in _BLOCKED_HOSTS:
        return None
    if not _host_allowed(host):
        log.warning("inbound media URL host not allowlisted: %s", host)
        return None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return raw
    if _ip_is_blocked(ip):
        log.warning("inbound media URL blocked private/reserved IP: %s", host)
        return None
    return raw


def validate_redirect_url(url: str) -> str | None:
    """Re-validate each redirect target before following."""
    return validate_inbound_media_url(url)
