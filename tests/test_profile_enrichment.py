"""Profile enrichment from public links."""
from __future__ import annotations

import pytest

from koraku.integrations.public_page_fetch import PublicPageFetchResult
from koraku_cloud.integrations.profile_enrichment import (
    ProfileLinkInput,
    enrich_profile_from_links,
    normalize_profile_links,
)


def test_normalize_profile_links_dedupes_and_caps() -> None:
    links = normalize_profile_links(
        [
            ProfileLinkInput(kind="linkedin", url="https://linkedin.com/in/alex"),
            ProfileLinkInput(kind="linkedin", url="https://linkedin.com/in/alex"),
            ProfileLinkInput(kind="custom", url="https://alex.dev", label="Site"),
        ]
    )
    assert len(links) == 2


@pytest.mark.asyncio
async def test_enrich_profile_from_links_merges_llm_output(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(url: str, *, max_chars: int = 6000) -> PublicPageFetchResult:
        return PublicPageFetchResult(url=url, ok=True, text="Senior engineer building AI tools.")

    async def fake_complete(*, system: str, user: str, model: str | None = None) -> str:
        return (
            '{"about":"I am a senior engineer building AI tools.",'
            '"link_summaries":[{"label":"Portfolio","url":"https://alex.dev","summary":"Senior engineer."}]}'
        )

    monkeypatch.setattr(
        "koraku_cloud.integrations.profile_enrichment.fetch_public_page_text",
        fake_fetch,
    )
    monkeypatch.setattr(
        "koraku_cloud.integrations.profile_enrichment.complete_assistant_text",
        fake_complete,
    )

    result = await enrich_profile_from_links(
        [ProfileLinkInput(kind="custom", url="https://alex.dev", label="Portfolio")],
        user_name="Alex",
    )
    assert "senior engineer" in result.about.lower()
    assert result.link_results[0].status == "ok"
    assert result.link_results[0].summary == "Senior engineer."


@pytest.mark.asyncio
async def test_enrich_profile_from_additional_info_without_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_complete(*, system: str, user: str, model: str | None = None) -> str:
        assert "climate startup" in user
        return '{"about":"I am a product lead at a climate startup.", "link_summaries":[]}'

    monkeypatch.setattr(
        "koraku_cloud.integrations.profile_enrichment.complete_assistant_text",
        fake_complete,
    )

    result = await enrich_profile_from_links(
        [],
        user_name="Alex",
        additional_info="Product lead at a climate startup.",
        help_with=["Organize notes, plans, and decisions"],
    )
    assert "product lead" in result.about.lower()
    assert result.link_results == []
