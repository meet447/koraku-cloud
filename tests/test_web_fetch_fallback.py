"""WebFetch: Jina Reader primary, Exa Contents second, Firecrawl fallback."""

from __future__ import annotations

import pytest

from koraku.tools import registry as reg


@pytest.mark.asyncio
async def test_web_fetch_uses_jina_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "exa-test")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "fc-test")

    import socket
    def mock_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)

    async def jina_ok(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = kwargs
        return True, f"URL: {url}\n(source: Jina Reader)\n\n--- Content ---\nSchedule here"

    async def exa_fail(*_a: object, **_k: object) -> tuple[bool, str]:
        raise AssertionError("Exa should not run when Jina succeeds")

    async def firecrawl_fail(*_a: object, **_k: object) -> str:
        raise AssertionError("Firecrawl should not run when Jina succeeds")

    monkeypatch.setattr(reg, "_jina_fetch_page", jina_ok)
    monkeypatch.setattr(reg, "_exa_fetch_page", exa_fail)
    monkeypatch.setattr(reg, "_firecrawl_fetch_page", firecrawl_fail)

    out = await reg._web_page("https://example.com/schedule")
    assert "Jina Reader" in out
    assert "Schedule here" in out


@pytest.mark.asyncio
async def test_web_fetch_falls_back_to_exa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "exa-test")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "fc-test")

    import socket
    def mock_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)

    async def jina_fail(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = url, kwargs
        return False, "timeout"

    async def exa_ok(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = kwargs
        return True, f"URL: {url}\n(source: Exa Contents)\n\n--- Content ---\nSchedule here"

    async def firecrawl_fail(*_a: object, **_k: object) -> str:
        raise AssertionError("Firecrawl should not run when Exa succeeds")

    monkeypatch.setattr(reg, "_jina_fetch_page", jina_fail)
    monkeypatch.setattr(reg, "_exa_fetch_page", exa_ok)
    monkeypatch.setattr(reg, "_firecrawl_fetch_page", firecrawl_fail)

    out = await reg._web_page("https://example.com/schedule")
    assert "Exa Contents" in out
    assert "Schedule here" in out


@pytest.mark.asyncio
async def test_web_fetch_falls_back_to_firecrawl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "exa-test")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "fc-test")

    async def jina_fail(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = url, kwargs
        return False, "blocked"

    async def exa_fail(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = url, kwargs
        return False, "timeout"

    async def firecrawl_ok(url: str, **kwargs: object) -> str:
        _ = kwargs
        return f"URL: {url}\n(source: Firecrawl)\n\n--- Content ---\nFull article"

    monkeypatch.setattr(reg, "_jina_fetch_page", jina_fail)
    monkeypatch.setattr(reg, "_exa_fetch_page", exa_fail)
    monkeypatch.setattr(reg, "_firecrawl_fetch_page", firecrawl_ok)

    # Mock socket.getaddrinfo to prevent assert_public_fetch_url from failing DNS resolution
    import socket
    def mock_getaddrinfo(*args, **kwargs):
        # Return a mock IPv4 address tuple for the public host
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)

    out = await reg._web_page("https://sportstar.example/article")
    assert "Firecrawl" in out
    assert "Full article" in out
    assert "Jina: blocked" in out
    assert "Exa: timeout" in out


@pytest.mark.asyncio
async def test_web_fetch_jina_only_without_premium_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "")

    import socket
    def mock_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)

    async def jina_ok(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = kwargs
        return True, f"URL: {url}\n\n--- Content ---\nOK"

    monkeypatch.setattr(reg, "_jina_fetch_page", jina_ok)

    out = await reg._web_page("https://example.com")
    assert "OK" in out


def test_web_fetch_available_without_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "")
    assert reg.web_fetch_available() is True


def test_jina_reader_url() -> None:
    assert reg._jina_reader_url("https://example.com/path") == "https://r.jina.ai/https://example.com/path"
