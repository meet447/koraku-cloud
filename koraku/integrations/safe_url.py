"""Validate user-supplied HTTP(S) URLs for server-side fetch (SSRF guard)."""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
    }
)

_PRIVATE_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def normalize_public_url(raw: str) -> str | None:
    """Return a normalized https/http URL or ``None`` when invalid."""
    text = (raw or "").strip()
    if not text:
        return None
    if not re.match(r"^https?://", text, flags=re.I):
        text = f"https://{text}"
    try:
        parsed = urlparse(text)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTS or host.endswith(".localhost"):
        return None
    if host == "0.0.0.0" or host.startswith("127."):
        return None
    # Reject userinfo and bare IPs in private ranges without DNS.
    try:
        ip = ipaddress.ip_address(host)
        if any(ip in net for net in _PRIVATE_NETWORKS):
            return None
    except ValueError:
        pass
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host}{port}{path}"


def assert_public_fetch_url(url: str) -> str:
    """Return normalized URL or raise ``ValueError``."""
    normalized = normalize_public_url(url)
    if not normalized:
        raise ValueError(f"URL is not allowed: {url}")
    host = (urlparse(normalized).hostname or "").strip().lower()
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve host: {host}") from e
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if any(ip in net for net in _PRIVATE_NETWORKS):
            raise ValueError(f"URL resolves to a private address: {host}")
    return normalized
