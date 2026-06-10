"""Accumulate billable usage from agent queue events (chat SSE or automations)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from koraku.credits.calculator import UsageAccumulator


@dataclass
class RunUsageTracker:
    usage: UsageAccumulator = field(default_factory=UsageAccumulator)
    started_tool_use_ids: set[str] = field(default_factory=set)

    def ingest(self, event: dict[str, Any]) -> None:
        if not isinstance(event, dict):
            return
        et = event.get("type")
        if et == "agent.llm_usage_estimate":
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            est_in = int(data.get("input_tokens") or 0)
            est_out = int(data.get("output_tokens") or 0)
            if est_in > 0 or est_out > 0:
                if self.usage.input_tokens <= 0 and self.usage.output_tokens <= 0:
                    self.usage.add_estimated_round(input_tokens=est_in, output_tokens=est_out)
            return
        if et == "tool_execution":
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            tool_use_id = str(data.get("id") or data.get("execution_id") or "").strip()
            tool_name = str(data.get("tool") or data.get("target_capability") or "tool").strip() or "tool"
            if tool_use_id and tool_use_id not in self.started_tool_use_ids:
                self.started_tool_use_ids.add(tool_use_id)
                self.usage.record_tool(tool_name)
            return
        if et != "stream_event":
            return
        raw = event.get("event")
        if not isinstance(raw, dict):
            return
        raw_type = str(raw.get("type") or "")
        if raw_type == "message_delta":
            usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
            u = usage if isinstance(usage, dict) else {}
            if any(
                (u.get(k) or 0) > 0
                for k in (
                    "input_tokens",
                    "output_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                )
            ):
                self.usage.add_turn_usage(
                    {
                        "input_tokens": int(u.get("input_tokens") or 0),
                        "output_tokens": int(u.get("output_tokens") or 0),
                        "cache_creation_input_tokens": int(u.get("cache_creation_input_tokens") or 0),
                        "cache_read_input_tokens": int(u.get("cache_read_input_tokens") or 0),
                    }
                )
            return
        if raw_type == "tool_use_pending":
            tool_use_id = str(raw.get("tool_use_id") or "").strip()
            tool_name = str(raw.get("name") or "tool").strip() or "tool"
            if tool_use_id and tool_use_id not in self.started_tool_use_ids:
                self.started_tool_use_ids.add(tool_use_id)
                self.usage.record_tool(tool_name)
