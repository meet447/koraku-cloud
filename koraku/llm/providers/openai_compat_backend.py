"""OpenAI-compatible chat completions (SSE) → normalized stream events."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Iterator

import httpx

from koraku.core.config import settings
from koraku.llm.canonical import CanonicalChatRequest
from koraku.llm.openai_delta import (
    _accumulate_openai_tool_call_deltas,
    _retryable_http_status,
    _tool_call_slots_to_blocks,
    openai_delta_content_to_str,
)
from koraku.llm.sanitize import VisibleToolJsonFilter
from koraku.llm.tool_call_parse import parse_tool_calls_from_text


def _parse_tool_calls_from_text(text: str) -> list[dict[str, Any]]:
    """Backward-compatible alias for tests and legacy imports."""
    return parse_tool_calls_from_text(text)



class _OpenAIStreamHandler:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.accumulated_text = ""
        self.message_id = ""
        self.visible_tool_filter = VisibleToolJsonFilter()
        self.native_tool_slots: dict[int, dict[str, str]] = {}
        self.text_block_started = False
        self.thinking_idx = 0
        self.thinking_started = False
        self.thinking_stopped = False
        self.text_stream_index: int | None = None

    def close_thinking_if_needed(self) -> Iterator[dict[str, Any]]:
        if self.thinking_started and not self.thinking_stopped:
            yield {"type": "content_block_stop", "index": self.thinking_idx}
            self.thinking_stopped = True

    def emit_reasoning_delta(self, chunk: str) -> Iterator[dict[str, Any]]:
        if not chunk:
            return
        if self.text_block_started:
            yield from self.iter_text_stream(chunk)
            return
        if not self.thinking_started:
            self.thinking_started = True
            yield {
                "type": "content_block_start",
                "index": self.thinking_idx,
                "content_block": {"type": "thinking", "thinking": "", "signature": ""},
            }
        yield {
            "type": "content_block_delta",
            "index": self.thinking_idx,
            "delta": {"type": "thinking_delta", "thinking": chunk},
        }

    def ensure_text_stream_index(self) -> int:
        if self.text_stream_index is None:
            self.text_stream_index = 1 if self.thinking_started else 0
        return self.text_stream_index

    def iter_text_stream(self, chunk: str) -> Iterator[dict[str, Any]]:
        if not chunk:
            return
        yield from self.close_thinking_if_needed()
        tidx = self.ensure_text_stream_index()
        if not self.text_block_started:
            self.text_block_started = True
            yield {
                "type": "content_block_start",
                "index": tidx,
                "content_block": {"type": "text", "text": ""},
            }
        self.accumulated_text += chunk
        for safe in self.visible_tool_filter.feed(chunk):
            if not safe:
                continue
            yield {
                "type": "content_block_delta",
                "index": tidx,
                "delta": {"type": "text_delta", "text": safe},
            }

    def process_line(self, line: str) -> Iterator[dict[str, Any]]:
        if not line.startswith("data: "):
            return
        data = line[6:]
        if data == "[DONE]":
            return
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return
        choices = parsed.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            return
        choice0 = choices[0] if isinstance(choices[0], dict) else {}
        delta = choice0.get("delta")
        if not isinstance(delta, dict):
            delta = {}
        msg_obj = choice0.get("message")
        if isinstance(msg_obj, dict):
            mtc = msg_obj.get("tool_calls")
            if isinstance(mtc, list) and mtc:
                _accumulate_openai_tool_call_deltas(self.native_tool_slots, mtc)

        raw_tcs = delta.get("tool_calls")
        if isinstance(raw_tcs, list) and raw_tcs:
            _accumulate_openai_tool_call_deltas(self.native_tool_slots, raw_tcs)

        reasoning_raw = delta.get("reasoning_content")
        if not isinstance(reasoning_raw, str) or not reasoning_raw:
            r2 = delta.get("reasoning")
            reasoning_raw = r2 if isinstance(r2, str) else ""
        if isinstance(reasoning_raw, str) and reasoning_raw:
            yield from self.emit_reasoning_delta(reasoning_raw)

        content = openai_delta_content_to_str(delta.get("content"))
        if not content.strip() and isinstance(delta.get("text"), str) and delta["text"].strip():
            content = delta["text"]
        if not self.message_id and parsed.get("id"):
            self.message_id = parsed["id"]
        if content:
            yield from self.iter_text_stream(content)

    def flush(self) -> Iterator[dict[str, Any]]:
        yield from self.close_thinking_if_needed()

        for tail in self.visible_tool_filter.flush():
            if not tail:
                continue
            yield from self.close_thinking_if_needed()
            tidx = self.ensure_text_stream_index()
            if not self.text_block_started:
                self.text_block_started = True
                yield {
                    "type": "content_block_start",
                    "index": tidx,
                    "content_block": {"type": "text", "text": ""},
                }
            yield {
                "type": "content_block_delta",
                "index": tidx,
                "delta": {"type": "text_delta", "text": tail},
            }

        if self.text_block_started:
            yield {"type": "content_block_stop", "index": self.ensure_text_stream_index()}

    def get_final_messages(self) -> Iterator[dict[str, Any]]:
        native_blocks = _tool_call_slots_to_blocks(self.native_tool_slots)
        compact_blocks = parse_tool_calls_from_text(self.accumulated_text)

        if native_blocks:
            # Native ``tool_calls`` are authoritative; keep streamed prose as-is (do not compact-parse
            # the body — that can mis-read benign JSON inside long replies such as email digests).
            body = self.accumulated_text.strip()
            if body:
                content_blocks = [{"type": "text", "text": body}, *native_blocks]
            else:
                text_parts = [b for b in compact_blocks if b.get("type") == "text"]
                content_blocks = (text_parts if text_parts else []) + native_blocks
        else:
            content_blocks = compact_blocks

        if not content_blocks:
            content_blocks = [{
                "type": "text",
                "text": (
                    "The model returned an empty completion (no text and no parsed tool calls). "
                    "If you were expecting tools, the upstream stream may use a format this client "
                    "does not yet map — try again or switch model/provider."
                ),
            }]

        stop_reason = "tool_use" if any(b.get("type") == "tool_use" for b in content_blocks) else "end_turn"

        yield {"type": "message_delta", "delta": {"stop_reason": stop_reason}, "usage": {}}
        yield {"type": "message_stop", "message": {}}
        yield {"type": "assistant_message", "message": {
            "id": self.message_id or "unknown", "model": self.model_id, "role": "assistant",
            "content": content_blocks, "stop_reason": stop_reason, "usage": {},
        }}

class OpenAICompatBackend:
    def __init__(self, *, base_url: str, api_key: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def stream(self, req: CanonicalChatRequest) -> AsyncIterator[dict[str, Any]]:
        payload = req.openai_chat_completions_body()
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": settings.user_agent,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            err_text = ""
            attempts = settings.llm_max_retries + 1
            for attempt in range(attempts):
                try:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as r:
                        if r.status_code < 400:
                            async for event in self._process_openai_stream(r, req.model_id):
                                yield event
                            return

                        body = await r.aread()
                        err_text = body.decode("utf-8", errors="replace")[:800]
                except httpx.RequestError as e:
                    err_text = str(e)
                    if attempt < attempts - 1:
                        await asyncio.sleep(settings.llm_retry_base_seconds * (2**attempt))
                        continue
                    yield {"type": "message_stop", "message": {}}
                    yield {"type": "assistant_message", "message": {
                        "content": [{"type": "text", "text": f"Connection error after {attempts} attempts: {err_text}"}],
                    }}
                    return
                if _retryable_http_status(r.status_code) and attempt < attempts - 1:
                    await asyncio.sleep(settings.llm_retry_base_seconds * (2**attempt))
                    continue
                yield {"type": "message_stop", "message": {}}
                yield {"type": "assistant_message", "message": {
                    "content": [{"type": "text", "text": f"API error {r.status_code}: {err_text}"}],
                }}
                return

            yield {"type": "message_stop", "message": {}}
            yield {"type": "assistant_message", "message": {
                "content": [{"type": "text", "text": f"API request failed after {attempts} attempts: {err_text}"}],
            }}

    async def _process_openai_stream(
        self,
        resp: httpx.Response,
        model_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "message_start", "message": {
            "id": "", "model": model_id, "role": "assistant",
            "content": [], "stop_reason": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }}

        handler = _OpenAIStreamHandler(model_id)
        buffer = ""
        async for chunk in resp.aiter_text():
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()

                if line.startswith("data: ") and line[6:] == "[DONE]":
                    break

                for ev in handler.process_line(line):
                    yield ev

        for ev in handler.flush():
            yield ev

        for ev in handler.get_final_messages():
            yield ev
