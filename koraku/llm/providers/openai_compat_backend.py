"""OpenAI-compatible chat completions (SSE) → normalized stream events."""
from __future__ import annotations

import asyncio
import json
import re
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


def _strip_markdown(text: str) -> str:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text


def _normalize_ruby_style_tool_json(blob: str) -> str:
    t = blob.strip()
    t = re.sub(r"\[TOOL_CALL\]\s*", "", t, flags=re.IGNORECASE)
    t = re.split(r"\[/TOOL_CALL", t, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    t = re.sub(r"{\s*tool\s*=>", '{"tool":', t)
    t = re.sub(r",\s*parameters\s*=>", ', "parameters":', t)
    return t.strip()


def _parse_tool_calls_from_text(text: str) -> list[dict[str, Any]]:
    """Extract tool calls from model text (compact-tool mode)."""
    blocks: list[dict[str, Any]] = []
    tool_calls = []

    clean_text = _strip_markdown(text)

    for m in re.finditer(
        r"\[TOOL_CALL\]\s*(\{[\s\S]*?\})\s*\[/TOOL_CALL\]",
        clean_text,
        re.IGNORECASE,
    ):
        raw_blob = m.group(1)
        normalized = _normalize_ruby_style_tool_json(raw_blob)
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, dict) and isinstance(parsed.get("tool"), str):
                tool_calls.append({"start": m.start(), "end": m.end(), "data": parsed})
        except json.JSONDecodeError:
            pass
    for m in re.finditer(
        r"<tool_call>\s*\[([A-Za-z][A-Za-z0-9_]*)\]\s*(\{[\s\S]*?\})\s*</tool_call>",
        clean_text,
        re.IGNORECASE,
    ):
        try:
            params = json.loads(m.group(2))
            if isinstance(params, dict):
                tool_calls.append({
                    "start": m.start(),
                    "end": m.end(),
                    "data": {"tool": m.group(1), "parameters": params},
                })
        except json.JSONDecodeError:
            pass
    if not tool_calls and ("tool" in clean_text.lower() and "=>" in clean_text):
        normalized = _normalize_ruby_style_tool_json(clean_text)
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, dict) and isinstance(parsed.get("tool"), str):
                tool_calls.append({"start": 0, "end": len(clean_text), "data": parsed})
        except json.JSONDecodeError:
            pass

    for pattern in [
        r'\{[^{}]*"tool"[^{}]*\}',
        r'\{(?:[^{}]|\{[^{}]*\})*"tool"(?:[^{}]|\{[^{}]*\})*\}',
    ]:
        for match in re.finditer(pattern, clean_text, re.DOTALL if "(?:" in pattern else 0):
            try:
                parsed = json.loads(match.group(0))
                if "tool" in parsed and isinstance(parsed["tool"], str):
                    inside = any(t["start"] <= match.start() < t["end"] for t in tool_calls)
                    if not inside:
                        tool_calls.append({"start": match.start(), "end": match.end(), "data": parsed})
            except json.JSONDecodeError:
                pass

    for match in re.finditer(
        r"\[Call\s+([A-Za-z][A-Za-z0-9_]*)\]\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})",
        clean_text,
        re.DOTALL,
    ):
        try:
            tool_name = match.group(1)
            params = json.loads(match.group(2))
            already = any(t["start"] == match.start() for t in tool_calls)
            if not already:
                tool_calls.append({
                    "start": match.start(),
                    "end": match.end(),
                    "data": {"tool": tool_name, "parameters": params},
                })
        except (json.JSONDecodeError, IndexError):
            pass

    if not tool_calls:
        if text.strip():
            blocks.append({"type": "text", "text": text})
        return blocks

    tool_calls.sort(key=lambda x: x["start"])
    last_end = 0
    for i, tc in enumerate(tool_calls):
        before = clean_text[last_end:tc["start"]]
        if before.strip():
            blocks.append({"type": "text", "text": before.strip()})
        params = tc["data"].get("parameters", tc["data"].get("input", tc["data"].get("args", {})))
        blocks.append({
            "type": "tool_use",
            "id": f"tool_{i}",
            "name": tc["data"]["tool"],
            "input": params if isinstance(params, dict) else {},
        })
        last_end = tc["end"]

    after = clean_text[last_end:]
    if after.strip():
        blocks.append({"type": "text", "text": after.strip()})
    return blocks



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
        compact_blocks = _parse_tool_calls_from_text(self.accumulated_text)

        if native_blocks:
            # Native ``tool_calls`` come from API slots; prose is only in ``accumulated_text``.
            # Do not rebuild text from ``_parse_tool_calls_from_text`` here — that regex pass can
            # treat benign markdown/JSON inside long replies (e.g. email digests) as inline tools
            # and shrink ``assistant_message`` to a short tail while deltas showed the full body.
            body = self.accumulated_text.strip()
            if body:
                content_blocks = [{"type": "text", "text": body}, *native_blocks]
            else:
                text_parts = [b for b in compact_blocks if b.get("type") == "text"]
                content_blocks = (text_parts if text_parts else [{"type": "text", "text": ""}]) + native_blocks
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
