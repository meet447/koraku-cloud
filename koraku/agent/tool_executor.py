"""Tool execution mixin for the Koraku agent."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Callable

from koraku.core.config import settings
from koraku.core.redact import redact_secrets
from koraku.tools.policy import tool_stdout_indicates_error
from koraku.tools.tool_def import Tool
from koraku.agent.events import _emit_worker_status

log = logging.getLogger(__name__)

_TOOL_RUN_SEMAPHORE = asyncio.Semaphore(max(1, int(settings.tool_concurrency_limit)))


def _resolve_tool_from_active(tool_name: str, active_tools: list[Any]) -> Tool | None:
    resolved = "WebFetch" if tool_name == "WebPage" else tool_name
    for t in active_tools:
        if t.name == resolved:
            return t
    return None


class ToolExecutionMixin:
    async def _execute_tools_parallel(
        self,
        tool_uses: list[dict[str, Any]],
        emit: Callable[[dict[str, Any]], None],
        active_tools: list[Any],
    ) -> list[dict[str, Any]]:
        for tool_use in tool_uses:
            exec_event = {
                "type": "tool_execution",
                "data": {
                    "target_capability": tool_use["name"],
                    "evaluation_parameters": tool_use["input"],
                    "execution_id": tool_use["id"],
                    "processing_topology": "parallel" if len(tool_uses) > 1 else "sequential",
                },
            }
            emit(exec_event)

        names = [str(tu.get("name") or "driver") for tu in tool_uses]
        primary_tool = names[0] if names else None
        hb_iv = max(3.0, float(settings.agent_worker_heartbeat_seconds))
        stop_hb = asyncio.Event()

        async def _tool_heartbeat() -> None:
            while not stop_hb.is_set():
                try:
                    await asyncio.wait_for(stop_hb.wait(), timeout=hb_iv)
                except asyncio.TimeoutError:
                    if len(names) == 1:
                        msg = f"Evaluating system execution target: {names[0]}..."
                    else:
                        msg = f"Processing validation matrix across {len(names)} targets..."
                    _emit_worker_status(emit, msg, tool_name=primary_tool, phase="subroutine_execution")

        hb_task = asyncio.create_task(_tool_heartbeat())
        try:
            if len(tool_uses) == 1:
                return [await self._execute_single_tool(tool_uses[0], active_tools)]

            async def run_one(tu: dict[str, Any]) -> dict[str, Any]:
                return await self._execute_single_tool(tu, active_tools)

            results = await asyncio.gather(*[run_one(tu) for tu in tool_uses], return_exceptions=True)
            processed: list[dict[str, Any]] = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed.append({
                        "type": "tool_result",
                        "tool_use_id": tool_uses[i]["id"],
                        "content": f"Execution exception: {result}",
                        "is_error": True,
                    })
                else:
                    processed.append(result)
            return processed
        finally:
            stop_hb.set()
            hb_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await hb_task

    async def _execute_single_tool(
        self,
        tool_use: dict[str, Any],
        active_tools: list[Any],
        max_retries: int = 2,
    ) -> dict[str, Any]:
        tool_name = tool_use["name"]
        tool_input = tool_use["input"]
        tool_id = tool_use["id"]

        if isinstance(tool_input, dict) and "_partial_json" in tool_input:
            hint = ""
            if tool_name == "Write":
                hint = (
                    " Write smaller chunks (~4KB) with mode=append, or use Bash: "
                    "`cat <<'EOF' > file.py` … `EOF`."
                )
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": (
                    f"Execution failure: Driver argument structure for '{tool_name}' arrived truncated. "
                    "Reduce operational parameter sizing layouts or split multi-tier targets into sequential steps."
                    f"{hint}"
                ),
                "is_error": True,
            }

        tool = _resolve_tool_from_active(tool_name, active_tools)
        if tool is None:
            return {
                "type": "tool_result", "tool_use_id": tool_id,
                "content": f"Execution failure: Specified routing target '{tool_name}' not found inside environment mapping maps.", "is_error": True,
            }

        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                async with _TOOL_RUN_SEMAPHORE:
                    result_text = await tool.run(**tool_input)
                is_error = tool_stdout_indicates_error(result_text, tool_name=tool_name)
                if not is_error:
                    return {"type": "tool_result", "tool_use_id": tool_id, "content": result_text, "is_error": False}
                last_error = result_text
            except Exception as e:
                last_error = str(e)

            if attempt < max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))

        return {
            "type": "tool_result", "tool_use_id": tool_id,
            "content": f"{last_error} (Process dropped after {max_retries + 1} processing verification loops)", "is_error": True,
        }
