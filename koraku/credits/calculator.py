"""Map token and tool usage to Koraku credits."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# Flat credits per tool invocation (first start per tool_use_id in a run).
TOOL_CREDITS: dict[str, int] = {
    "WebSearch": 30,
    "web_search": 30,
    "FirecrawlScrape": 40,
    "firecrawl_scrape": 40,
    "composio": 25,
}

DEFAULT_TOOL_CREDITS = 10
IMAGE_ATTACHMENT_CREDITS = 50
MIN_TURN_CREDITS = 5


@dataclass
class UsageAccumulator:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    tool_counts: dict[str, int] = field(default_factory=dict)
    image_count: int = 0

    def add_turn_usage(self, data: dict[str, Any]) -> None:
        self.input_tokens += int(data.get("input_tokens") or 0)
        self.output_tokens += int(data.get("output_tokens") or 0)
        self.cache_creation_input_tokens += int(data.get("cache_creation_input_tokens") or 0)
        self.cache_read_input_tokens += int(data.get("cache_read_input_tokens") or 0)

    def add_estimated_round(self, *, input_tokens: int, output_tokens: int) -> None:
        self.estimated_input_tokens += max(0, int(input_tokens))
        self.estimated_output_tokens += max(0, int(output_tokens))

    @property
    def billing_input_tokens(self) -> int:
        if self.input_tokens > 0:
            return self.input_tokens
        return self.estimated_input_tokens

    @property
    def billing_output_tokens(self) -> int:
        if self.output_tokens > 0:
            return self.output_tokens
        return self.estimated_output_tokens

    @property
    def token_source(self) -> str:
        if self.input_tokens > 0 or self.output_tokens > 0:
            return "provider"
        if self.estimated_input_tokens > 0 or self.estimated_output_tokens > 0:
            return "estimated"
        return "none"

    def record_tool(self, tool_name: str) -> None:
        name = (tool_name or "tool").strip() or "tool"
        key = name.split(":")[0] if ":" in name else name
        self.tool_counts[key] = self.tool_counts.get(key, 0) + 1

    def to_metadata(self, *, run_id: str, model: str, provider: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "model": model,
            "provider": provider,
            "token_source": self.token_source,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "billing_input_tokens": self.billing_input_tokens,
            "billing_output_tokens": self.billing_output_tokens,
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "tool_counts": dict(self.tool_counts),
            "image_count": self.image_count,
        }


def _tool_credits(tool_name: str) -> int:
    name = (tool_name or "").strip()
    if not name:
        return DEFAULT_TOOL_CREDITS
    if name in TOOL_CREDITS:
        return TOOL_CREDITS[name]
    prefix = name.split(":")[0]
    if prefix in TOOL_CREDITS:
        return TOOL_CREDITS[prefix]
    lower = name.lower()
    for key, val in TOOL_CREDITS.items():
        if key.lower() in lower or lower in key.lower():
            return val
    return DEFAULT_TOOL_CREDITS


def compute_credits(usage: UsageAccumulator) -> int:
    """Return billable credits for one settled run."""
    in_credits = math.ceil(max(0, usage.billing_input_tokens) / 1000)
    out_credits = math.ceil(max(0, usage.billing_output_tokens) / 500)
    cache_read = math.ceil(max(0, usage.cache_read_input_tokens) / 1000 * 0.1)
    cache_write = math.ceil(max(0, usage.cache_creation_input_tokens) / 1000 * 1.25)
    tool_credits = sum(_tool_credits(name) * count for name, count in usage.tool_counts.items())
    image_credits = usage.image_count * IMAGE_ATTACHMENT_CREDITS
    total = in_credits + out_credits + cache_read + cache_write + tool_credits + image_credits
    if total <= 0 and not usage.tool_counts and usage.image_count == 0:
        return 0
    return max(MIN_TURN_CREDITS, total) if total > 0 else 0
