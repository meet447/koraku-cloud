"""Build onboarding About text from public profile links."""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from koraku.integrations.public_page_fetch import fetch_public_page_text
from koraku.integrations.safe_url import normalize_public_url
from koraku.llm.quick_complete import complete_assistant_text

ProfileLinkKind = Literal["linkedin", "x", "custom"]
LinkFetchStatus = Literal["ok", "failed", "skipped"]

_MAX_LINKS = 5
_FETCH_CONCURRENCY = 2
_EXCERPT_CHARS = 2500

_SYSTEM_PROMPT = """You write concise user profile blurbs for a personal AI assistant.
Return ONLY valid JSON with this shape:
{
  "about": "2-4 sentences in first person (I am / I work on / I help with ...)",
  "link_summaries": [
    {"label": "LinkedIn", "url": "https://...", "summary": "one short sentence or empty string"}
  ]
}
Rules:
- Write the about field as if the user is speaking about themselves (first person: I, my, me).
- Never use second person (you, your) in the about field.
- Use only facts supported by the provided excerpts and additional notes.
- Do not invent employers, titles, or achievements.
- If a link could not be fetched, leave its summary empty.
- Keep the about field practical and under 120 words.
"""


@dataclass(frozen=True)
class ProfileLinkInput:
    kind: ProfileLinkKind
    url: str
    label: str | None = None


@dataclass(frozen=True)
class ProfileLinkResult:
    kind: ProfileLinkKind
    url: str
    label: str
    status: LinkFetchStatus
    summary: str | None
    error: str | None


@dataclass(frozen=True)
class ProfileEnrichResult:
    about: str
    link_results: list[ProfileLinkResult]


def _default_label(kind: ProfileLinkKind, label: str | None) -> str:
    if kind == "linkedin":
        return "LinkedIn"
    if kind == "x":
        return "X"
    cleaned = (label or "").strip()
    return cleaned or "Link"


def normalize_profile_links(raw_links: list[ProfileLinkInput]) -> list[ProfileLinkInput]:
    out: list[ProfileLinkInput] = []
    seen: set[str] = set()
    for item in raw_links:
        normalized = normalize_public_url(item.url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(
            ProfileLinkInput(
                kind=item.kind,
                url=normalized,
                label=item.label,
            )
        )
        if len(out) >= _MAX_LINKS:
            break
    return out


async def _fetch_one(link: ProfileLinkInput) -> tuple[ProfileLinkInput, str, str | None]:
    result = await fetch_public_page_text(link.url, max_chars=_EXCERPT_CHARS)
    if result.ok:
        return link, result.text, None
    return link, "", result.error or "Could not fetch page"


async def enrich_profile_from_links(
    links: list[ProfileLinkInput],
    *,
    user_name: str | None = None,
    existing_about: str | None = None,
    additional_info: str | None = None,
    help_with: list[str] | None = None,
) -> ProfileEnrichResult:
    normalized = normalize_profile_links(links)
    extra = (additional_info or "").strip()
    goals = [g.strip() for g in (help_with or []) if g and g.strip()]
    if not normalized and not extra and not goals:
        raise ValueError("Add public links, additional context, or pick how Koraku should help.")

    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)

    async def guarded_fetch(link: ProfileLinkInput):
        async with sem:
            return await _fetch_one(link)

    fetched = (
        await asyncio.gather(*(guarded_fetch(link) for link in normalized))
        if normalized
        else []
    )

    prompt_parts = [
        f"User name: {(user_name or '').strip() or 'Unknown'}",
        f"Additional notes from the user: {extra or '(none)'}",
        f"Koraku should help with: {', '.join(goals) if goals else '(not specified)'}",
        f"Existing about draft (may be empty): {(existing_about or '').strip()}",
        "",
        "Link excerpts:",
    ]
    link_results: list[ProfileLinkResult] = []
    for link, text, error in fetched:
        label = _default_label(link.kind, link.label)
        if text.strip():
            prompt_parts.append(f"\n[{label}] {link.url}\n{text[:_EXCERPT_CHARS]}")
            link_results.append(
                ProfileLinkResult(
                    kind=link.kind,
                    url=link.url,
                    label=label,
                    status="ok",
                    summary=None,
                    error=None,
                )
            )
        else:
            prompt_parts.append(f"\n[{label}] {link.url}\n(fetch failed: {error or 'unknown'})")
            link_results.append(
                ProfileLinkResult(
                    kind=link.kind,
                    url=link.url,
                    label=label,
                    status="failed",
                    summary=None,
                    error=error or "Could not fetch page",
                )
            )

    raw = await complete_assistant_text(system=_SYSTEM_PROMPT, user="\n".join(prompt_parts))
    parsed = _parse_llm_json(raw)

    about = str(parsed.get("about") or "").strip()
    if not about and (existing_about or "").strip():
        about = (existing_about or "").strip()
    if not about:
        about = _fallback_about(
            link_results,
            user_name=user_name,
            additional_info=additional_info,
        )

    summaries = parsed.get("link_summaries")
    summary_by_url: dict[str, str] = {}
    summary_by_label: dict[str, str] = {}
    if isinstance(summaries, list):
        for row in summaries:
            if not isinstance(row, dict):
                continue
            raw_url = str(row.get("url") or "").strip()
            url = normalize_public_url(raw_url) or raw_url
            label = str(row.get("label") or "").strip()
            summary = str(row.get("summary") or "").strip()
            if url and summary:
                summary_by_url[url] = summary
            if label and summary:
                summary_by_label[label.lower()] = summary

    merged_results: list[ProfileLinkResult] = []
    for row in link_results:
        summary = summary_by_url.get(row.url) or summary_by_label.get(row.label.lower())
        if not summary and row.status == "failed":
            summary = None
        merged_results.append(
            ProfileLinkResult(
                kind=row.kind,
                url=row.url,
                label=row.label,
                status=row.status,
                summary=summary,
                error=row.error,
            )
        )

    return ProfileEnrichResult(about=about, link_results=merged_results)


def _fallback_about(
    results: list[ProfileLinkResult],
    *,
    user_name: str | None,
    additional_info: str | None = None,
) -> str:
    extra = (additional_info or "").strip()
    if extra:
        return extra[:500]
    labels = [r.label for r in results if r.url]
    if labels:
        joined = ", ".join(labels)
        return f"I shared public profile links ({joined}) for context as I get started with Koraku."
    return "I'm getting started with Koraku."


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}
