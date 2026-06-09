"""Fetch readable text from a public web page for profile enrichment."""
from __future__ import annotations

from dataclasses import dataclass

from koraku.integrations.safe_url import assert_public_fetch_url


@dataclass(frozen=True)
class PublicPageFetchResult:
    url: str
    ok: bool
    text: str
    error: str | None = None


async def fetch_public_page_text(url: str, *, max_chars: int = 6000) -> PublicPageFetchResult:
    """Fetch page text via Jina Reader with Exa fallback."""
    try:
        safe_url = assert_public_fetch_url(url)
    except ValueError as e:
        return PublicPageFetchResult(url=url, ok=False, text="", error=str(e))

    from koraku.tools.registry import _exa_fetch_page, _jina_fetch_page

    ok, body = await _jina_fetch_page(safe_url, max_chars=max_chars)
    if ok:
        return PublicPageFetchResult(url=safe_url, ok=True, text=_extract_content(body))

    err = body
    ok, body = await _exa_fetch_page(safe_url, max_chars=max_chars)
    if ok:
        return PublicPageFetchResult(url=safe_url, ok=True, text=_extract_content(body))

    if err and body:
        err = f"{err}; {body}"
    elif body:
        err = body
    return PublicPageFetchResult(url=safe_url, ok=False, text="", error=err or "Could not fetch page")


def _extract_content(body: str) -> str:
    marker = "--- Content ---"
    if marker in body:
        return body.split(marker, 1)[1].strip()
    return body.strip()
