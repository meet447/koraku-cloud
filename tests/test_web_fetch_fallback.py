"""WebFetch: Exa Contents primary, Firecrawl fallback."""

from __future__ import annotations

import pytest

from koraku.tools import registry as reg


@pytest.mark.asyncio
async def test_web_fetch_uses_exa_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "exa-test")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "fc-test")

    async def exa_ok(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = kwargs
        return True, f"URL: {url}\n(source: Exa Contents)\n\n--- Content ---\nSchedule here"

    async def firecrawl_fail(*_a: object, **_k: object) -> str:
        raise AssertionError("Firecrawl should not run when Exa succeeds")

    monkeypatch.setattr(reg, "_exa_fetch_page", exa_ok)
    monkeypatch.setattr(reg, "_firecrawl_fetch_page", firecrawl_fail)

    out = await reg._web_page("https://example.com/schedule")
    assert "Exa Contents" in out
    assert "Schedule here" in out


@pytest.mark.asyncio
async def test_web_fetch_falls_back_to_firecrawl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "exa-test")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "fc-test")

    async def exa_fail(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = url, kwargs
        return False, "timeout"

    async def firecrawl_ok(url: str, **kwargs: object) -> str:
        _ = kwargs
        return f"URL: {url}\n(source: Firecrawl)\n\n--- Content ---\nFull article"

    monkeypatch.setattr(reg, "_exa_fetch_page", exa_fail)
    monkeypatch.setattr(reg, "_firecrawl_fetch_page", firecrawl_ok)

    out = await reg._web_page("https://sportstar.example/article")
    assert "Firecrawl" in out
    assert "Full article" in out
    assert "Exa: timeout" in out


@pytest.mark.asyncio
async def test_web_fetch_exa_only_without_firecrawl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "exa-test")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "")

    async def exa_ok(url: str, **kwargs: object) -> tuple[bool, str]:
        _ = kwargs
        return True, f"URL: {url}\n\n--- Content ---\nOK"

    monkeypatch.setattr(reg, "_exa_fetch_page", exa_ok)

    out = await reg._web_page("https://example.com")
    assert "OK" in out


def test_web_fetch_available_with_either_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg.settings, "exa_api_key", "x")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "")
    assert reg.web_fetch_available() is True

    monkeypatch.setattr(reg.settings, "exa_api_key", "")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "y")
    assert reg.web_fetch_available() is True

    monkeypatch.setattr(reg.settings, "exa_api_key", "")
    monkeypatch.setattr(reg.settings, "firecrawl_api_key", "")
    assert reg.web_fetch_available() is False
