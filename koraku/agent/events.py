"""SSE and tracing event emitters for the Koraku agent."""
from __future__ import annotations

from typing import Any, Callable

from koraku.core.models import AgentMessage
from koraku.credits.token_estimator import (
    estimate_llm_round,
    native_tools_for_provider,
)


def _emit_llm_usage_estimate(
    emit: Callable[[dict[str, Any]], None],
    *,
    messages: list[AgentMessage],
    system_prompt: str,
    tool_schemas: list[Any],
    assistant_content: list[dict[str, Any]] | str,
    model: str,
    provider: str,
) -> dict[str, Any]:
    est_in, est_out = estimate_llm_round(
        messages=messages,
        system_prompt=system_prompt,
        tool_schemas=tool_schemas,
        assistant_content=assistant_content,
        model=model,
        native_tools=native_tools_for_provider(provider, tool_schemas),
    )
    event = {
        "type": "agent.llm_usage_estimate",
        "data": {
            "input_tokens": est_in,
            "output_tokens": est_out,
            "model": model,
            "provider": provider,
        },
    }
    emit(event)
    return event


def _emit_worker_status(
    emit: Callable[[dict[str, Any]], None],
    message: str,
    *,
    tool_name: str | None = None,
    phase: str | None = None,
) -> None:
    data: dict[str, Any] = {"trace": "operational_status", "message": message}
    if tool_name:
        data["active_tool"] = tool_name
    if phase:
        data["execution_phase"] = phase
    emit({"type": "agent.trace", "data": data})
