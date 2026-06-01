"""SSE payloads with Koraku-branded outer types: ``koraku.*`` and stringified ``koraku.event`` bodies."""
from __future__ import annotations

import json
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from koraku.tools.registry import AVAILABLE_TOOLS


def _now_ms() -> int:
    return int(time.time() * 1000)


def new_pty_session_id() -> str:
    return f"koraku-{_now_ms()}-{secrets.token_hex(3)}"


def new_inner_session_id() -> str:
    return secrets.token_hex(12)


def _koraku_envelope_event(inner: dict[str, Any]) -> dict[str, Any]:
    return {"type": "koraku.event", "data": json.dumps(inner, ensure_ascii=False)}


def route_decision_data(provider_id: str, model: str) -> dict[str, Any]:
    pid = (provider_id or "").strip().lower()
    if pid == "anthropic":
        return {"runtime": "claude", "model": model, "meta": {"isByok": False, "provider": "anthropic"}}
    if pid == "fireworks":
        return {"runtime": "fireworks", "model": model, "meta": {"isByok": False, "provider": "fireworks"}}
    return {"runtime": "custom_openai", "model": model, "meta": {"isByok": False, "provider": pid or "openai_compat"}}


def build_system_init_inner(
    *,
    cwd: str,
    inner_session_id: str,
    model: str,
    koraku: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tools = [t.to_anthropic_schema() for t in AVAILABLE_TOOLS]
    body: dict[str, Any] = {
        "type": "system",
        "subtype": "init",
        "cwd": cwd,
        "session_id": inner_session_id,
        "tools": tools,
        "mcp_servers": [],
        "model": model,
        "permissionMode": "default",
        "slash_commands": [],
        "apiKeySource": "koraku",
        "output_style": "default",
        "uuid": str(uuid.uuid4()),
    }
    if koraku:
        body["koraku"] = koraku
    return body


def _wrap_stream_event(
    raw_event: dict[str, Any],
    inner_session_id: str,
    run_id: str,
    parent_tool_use_id: str | None = None,
) -> dict[str, Any]:
    inner: dict[str, Any] = {
        "type": "stream_event",
        "event": raw_event,
        "run_id": run_id,
        "session_id": inner_session_id,
        "parent_tool_use_id": parent_tool_use_id,
        "uuid": str(uuid.uuid4()),
    }
    return _koraku_envelope_event(inner)


def _json_len(value: Any) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return len(str(value))


def _short_text(value: Any, max_chars: int = 500) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
    text = " ".join(text.split())
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def _tool_event(
    *,
    inner_session_id: str,
    run_id: str,
    phase: str,
    tool_use_id: str,
    tool_name: str,
    tool_input: Any = None,
    mode: str | None = None,
    is_error: bool | None = None,
    output_summary: str | None = None,
    truncated: dict[str, bool] | None = None,
    subagent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = "running" if phase == "started" else ("error" if phase == "failed" else "completed")
    inner: dict[str, Any] = {
        "type": "tool_event",
        "phase": phase,
        "status": status,
        "tool_use_id": tool_use_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "mode": mode,
        "is_error": is_error,
        "output_summary": output_summary,
        "truncated": truncated or {},
        "run_id": run_id,
        "session_id": inner_session_id,
        "parent_tool_use_id": tool_use_id,
        "uuid": str(uuid.uuid4()),
    }
    if subagent:
        inner["subagent"] = subagent
    return _koraku_envelope_event(inner)


def _assistant_message_without_tool_calls(raw_event: dict[str, Any]) -> dict[str, Any] | None:
    message = raw_event.get("message")
    if not isinstance(message, dict):
        return raw_event
    content = message.get("content")
    if not isinstance(content, list):
        return raw_event
    filtered = [
        block
        for block in content
        if not (isinstance(block, dict) and block.get("type") == "tool_use")
    ]
    if not filtered:
        return None
    return {**raw_event, "message": {**message, "content": filtered}}


def _result_inner(
    *,
    inner_session_id: str,
    run_id: str,
    model: str,
    failed: bool,
    stop_reason: str,
    duration_ms: int,
    duration_api_ms: int,
    cancelled: bool = False,
) -> dict[str, Any]:
    subtype = "cancelled" if cancelled else ("error" if failed else "success")
    return {
        "type": "result",
        "subtype": subtype,
        "duration_ms": duration_ms,
        "duration_api_ms": duration_api_ms,
        "is_error": failed,
        "result": "",
        "session_id": inner_session_id,
        "run_id": run_id,
        "uuid": str(uuid.uuid4()),
        "total_cost_usd": 0.0,
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "stop_reason": stop_reason,
        "modelUsage": {
            model: {
                "inputTokens": 0,
                "outputTokens": 0,
                "cacheReadInputTokens": 0,
                "cacheCreationInputTokens": 0,
                "webSearchRequests": 0,
                "costUSD": 0.0,
                "contextWindow": 200000,
            }
        },
    }


def _koraku_completed(
    *,
    pty_session_id: str,
    sandbox_id: str,
    exit_code: int,
    failed: bool,
    error: str | None,
    cancelled: bool = False,
) -> dict[str, Any]:
    return {
        "type": "koraku.completed",
        "data": {
            "ptySessionId": pty_session_id,
            "sandboxId": sandbox_id,
            "exitCode": exit_code,
            "failed": failed,
            "error": error,
            "cancelled": cancelled,
            "postflightBackgrounded": False,
        },
    }


def _koraku_output_marker() -> dict[str, Any]:
    return {"type": "koraku.output", "data": {"marker": "__KORAKU_DONE__:0"}}


def _koraku_trace(trace: str, data: dict[str, Any], inner_session_id: str, run_id: str) -> dict[str, Any]:
    inner = {
        "type": "koraku.trace",
        "trace": trace,
        "data": {**data, "run_id": run_id},
        "session_id": inner_session_id,
        "run_id": run_id,
        "uuid": str(uuid.uuid4()),
    }
    return _koraku_envelope_event(inner)


@dataclass
class KorakuStreamState:
    """Per-request stream envelope ids and timing."""

    pty_session_id: str = field(default_factory=new_pty_session_id)
    sandbox_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    inner_session_id: str = field(default_factory=new_inner_session_id)
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_ms: int = field(default_factory=_now_ms)
    resolved_model: str = ""
    eff_provider: str = ""
    suppressed_tool_block_indexes: set[int] = field(default_factory=set)
    tool_calls_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)

    def started_payload(self, model: str, *, chat_session_id: str | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ptySessionId": self.pty_session_id,
            "sandboxId": self.sandbox_id,
            "model": model,
            "startedAt": self.started_ms,
            "runId": self.run_id,
        }
        if chat_session_id:
            data["chatSessionId"] = chat_session_id
        return {"type": "koraku.started", "data": data}

    def s2_stream_payload(self) -> dict[str, Any]:
        uri = f"s2://koraku/{self.pty_session_id}"
        return {"type": "koraku.s2-stream", "data": {"uri": uri}}

    def route_decision_payload(self) -> dict[str, Any]:
        return {
            "type": "koraku.route_decision",
            "data": route_decision_data(self.eff_provider, self.resolved_model),
        }

    def system_init_payload(self, cwd: str, koraku: dict[str, Any]) -> dict[str, Any]:
        inner = build_system_init_inner(
            cwd=cwd,
            inner_session_id=self.inner_session_id,
            model=self.resolved_model,
            koraku=koraku,
        )
        return _koraku_envelope_event(inner)

    def completion_sequence(
        self,
        data: dict[str, Any] | None,
        *,
        failed: bool,
        error: str | None,
        cancelled: bool = False,
    ) -> list[dict[str, Any]]:
        model = (data or {}).get("model") or self.resolved_model or "auto"
        reason = (data or {}).get("reason") or ("error" if failed else ("cancelled" if cancelled else "end_turn"))
        elapsed = max(0, _now_ms() - self.started_ms)
        out: list[dict[str, Any]] = []
        out.append(_koraku_envelope_event(_result_inner(
            inner_session_id=self.inner_session_id,
            run_id=self.run_id,
            model=model,
            failed=failed and not cancelled,
            stop_reason="cancelled" if cancelled else ("error" if failed else str(reason)),
            duration_ms=elapsed,
            duration_api_ms=elapsed,
            cancelled=cancelled,
        )))
        out.append(_koraku_completed(
            pty_session_id=self.pty_session_id,
            sandbox_id=self.sandbox_id,
            exit_code=130 if cancelled else (1 if failed else 0),
            failed=failed and not cancelled,
            error=error,
            cancelled=cancelled,
        ))
        out.append(_koraku_output_marker())
        return out


_TOOL_INPUT_TRUNC_BYTES = 8_000


def map_koraku_stream_events(event: dict[str, Any], state: KorakuStreamState) -> list[dict[str, Any]]:
    """Translate one Koraku queue event into zero or more outer SSE JSON objects."""
    rid = state.run_id
    et = event.get("type")
    if et == "agent.mode":
        return [_koraku_trace("mode", event.get("data") or {}, state.inner_session_id, rid)]
    if et == "agent.tools":
        return [_koraku_trace("tools", event.get("data") or {}, state.inner_session_id, rid)]
    if et == "agent.context":
        return [_koraku_trace("context", event.get("data") or {}, state.inner_session_id, rid)]
    if et == "agent.history":
        return [_koraku_trace("history", event.get("data") or {}, state.inner_session_id, rid)]
    if et == "tool_execution":
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        tool_use_id = str(data.get("id") or "")
        tool_name = str(data.get("tool") or "tool")
        tool_input = data.get("input")
        if tool_use_id:
            state.tool_calls_by_id[tool_use_id] = {"tool": tool_name, "input": tool_input}
        t_args = _json_len(tool_input) > _TOOL_INPUT_TRUNC_BYTES
        sub_raw = event.get("subagent")
        sub_payload: dict[str, Any] | None = None
        if isinstance(sub_raw, dict) and sub_raw.get("composio"):
            sub_payload = {
                "composio": True,
                "toolkits": [str(x) for x in (sub_raw.get("toolkits") or []) if str(x).strip()],
            }
        return [
            _tool_event(
                inner_session_id=state.inner_session_id,
                run_id=rid,
                phase="started",
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                tool_input=tool_input,
                mode=str(data.get("mode") or "") or None,
                truncated={"args": t_args} if t_args else None,
                subagent=sub_payload,
            )
        ]
    if et == "agent.memory":
        return [_koraku_trace("memory", event.get("data") or {}, state.inner_session_id, rid)]
    if et == "agent.subagent":
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        out_sub: dict[str, Any] = {"phase": str(data.get("phase") or "")}
        tkl = data.get("toolkits")
        if isinstance(tkl, list):
            out_sub["toolkits"] = [str(x) for x in tkl if str(x).strip()]
        sub_raw = event.get("subagent")
        if isinstance(sub_raw, dict) and sub_raw.get("composio"):
            out_sub["composio"] = True
        return [{"type": "koraku.subagent", "data": out_sub}]
    if et == "stream_event":
        raw = event.get("event")
        if not isinstance(raw, dict):
            return []
        sub_raw = event.get("subagent")
        if isinstance(sub_raw, dict) and sub_raw.get("composio"):
            raw = {
                **raw,
                "subagent": {
                    "composio": True,
                    "toolkits": [str(x) for x in (sub_raw.get("toolkits") or []) if str(x).strip()],
                },
            }
        raw_type = str(raw.get("type") or "")
        idx = raw.get("index")
        out: list[dict[str, Any]] = []
        if raw_type == "message_delta":
            usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
            u = usage if isinstance(usage, dict) else {}
            if any((u.get(k) or 0) > 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")):
                out.append({
                    "type": "koraku.turn_usage",
                    "data": {
                        "runId": rid,
                        "innerSessionId": state.inner_session_id,
                        "input_tokens": int(u.get("input_tokens") or 0),
                        "output_tokens": int(u.get("output_tokens") or 0),
                        "cache_creation_input_tokens": int(u.get("cache_creation_input_tokens") or 0),
                        "cache_read_input_tokens": int(u.get("cache_read_input_tokens") or 0),
                    },
                })
        if raw_type == "content_block_start":
            block = raw.get("content_block")
            if isinstance(idx, int) and isinstance(block, dict) and block.get("type") == "tool_use":
                state.suppressed_tool_block_indexes.add(idx)
                return out
        if raw_type == "content_block_delta":
            delta = raw.get("delta")
            if isinstance(idx, int) and idx in state.suppressed_tool_block_indexes:
                return out
            if isinstance(delta, dict) and delta.get("type") == "input_json_delta":
                return out
        if raw_type == "content_block_stop" and isinstance(idx, int) and idx in state.suppressed_tool_block_indexes:
            state.suppressed_tool_block_indexes.discard(idx)
            return out
        if raw_type == "assistant_message":
            safe = _assistant_message_without_tool_calls(raw)
            if safe is None:
                return out
            raw = safe
        out.append(_wrap_stream_event(raw, state.inner_session_id, rid, None))
        return out
    if et == "user":
        msg = event.get("message")
        if not isinstance(msg, dict):
            return []
        out: list[dict[str, Any]] = []
        content = msg.get("content")
        blocks = content if isinstance(content, list) else [content]
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_use_id = str(block.get("tool_use_id") or "")
            call = state.tool_calls_by_id.pop(tool_use_id, {}) if tool_use_id else {}
            is_error = bool(block.get("is_error"))
            raw_content = block.get("content")
            summary = _short_text(raw_content, 500)
            t_res = _json_len(raw_content) > 500
            sub_raw = event.get("subagent")
            sub_payload: dict[str, Any] | None = None
            if isinstance(sub_raw, dict) and sub_raw.get("composio"):
                sub_payload = {
                    "composio": True,
                    "toolkits": [str(x) for x in (sub_raw.get("toolkits") or []) if str(x).strip()],
                }
            out.append(_tool_event(
                inner_session_id=state.inner_session_id,
                run_id=rid,
                phase="failed" if is_error else "completed",
                tool_use_id=tool_use_id,
                tool_name=str(call.get("tool") or "tool"),
                tool_input=call.get("input"),
                is_error=is_error,
                output_summary=summary,
                truncated={"result": t_res} if t_res else None,
                subagent=sub_payload,
            ))
        return out
    if et == "agent.completed":
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        return state.completion_sequence(data, failed=False, error=None)
    if et == "agent.cancelled":
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        merged = {**data, "model": data.get("model") or state.resolved_model, "reason": "cancelled"}
        return state.completion_sequence(merged, failed=False, error=None, cancelled=True)
    if et == "agent.error":
        err = str((event.get("data") or {}).get("error", "unknown error"))
        return state.completion_sequence(None, failed=True, error=err)
    return []
