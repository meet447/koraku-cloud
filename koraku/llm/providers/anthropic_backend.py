"""Anthropic Messages API → normalized stream events."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from anthropic import APIStatusError, AsyncAnthropic

from koraku.core.config import settings
from koraku.llm.canonical import CanonicalChatRequest
from koraku.llm.openai_delta import _retryable_http_status


class AnthropicMessagesBackend:
    def __init__(self, client: AsyncAnthropic) -> None:
        self._client = client

    async def stream(self, req: CanonicalChatRequest) -> AsyncIterator[dict[str, Any]]:
        kwargs = req.anthropic_stream_kwargs()
        attempts = settings.llm_max_retries + 1
        last_error: str | None = None
        for attempt in range(attempts):
            try:
                async with self._client.messages.stream(**kwargs) as stream:
                    assistant_content: list[dict[str, Any]] = []
                    current_block_type = None
                    current_json = ""

                    async for event in stream:
                        if event.type == "message_start":
                            yield {"type": "message_start", "message": {
                                "id": event.message.id, "model": event.message.model,
                                "role": event.message.role, "content": [],
                                "stop_reason": None,
                                "usage": {"input_tokens": event.message.usage.input_tokens, "output_tokens": event.message.usage.output_tokens},
                            }}

                        elif event.type == "content_block_start":
                            current_block_type = event.content_block.type
                            block = {"type": event.content_block.type}
                            if event.content_block.type == "thinking":
                                block["thinking"] = ""
                                block["signature"] = ""
                            elif event.content_block.type == "tool_use":
                                block["id"] = event.content_block.id
                                block["name"] = event.content_block.name
                                block["input"] = {}
                            elif event.content_block.type == "text":
                                block["text"] = ""
                            assistant_content.append(block)
                            yield {"type": "content_block_start", "index": event.index, "content_block": block}

                        elif event.type == "content_block_delta":
                            delta: dict[str, Any] = {"type": event.delta.type}
                            if event.delta.type == "thinking_delta":
                                delta["thinking"] = event.delta.thinking
                            elif event.delta.type == "signature_delta":
                                delta["signature"] = event.delta.signature
                            elif event.delta.type == "text_delta":
                                delta["text"] = event.delta.text
                            elif event.delta.type == "input_json_delta":
                                delta["partial_json"] = event.delta.partial_json
                                current_json += event.delta.partial_json
                            yield {"type": "content_block_delta", "index": event.index, "delta": delta}

                        elif event.type == "content_block_stop":
                            if current_block_type == "tool_use" and current_json:
                                try:
                                    parsed = json.loads(current_json)
                                    if assistant_content and assistant_content[-1]["type"] == "tool_use":
                                        assistant_content[-1]["input"] = parsed
                                except json.JSONDecodeError:
                                    pass
                            yield {"type": "content_block_stop", "index": event.index}
                            current_block_type = None
                            current_json = ""

                        elif event.type == "message_delta":
                            delta = {}
                            if event.delta.stop_reason:
                                delta["stop_reason"] = event.delta.stop_reason
                            usage = {}
                            if event.usage:
                                usage = {"input_tokens": event.usage.input_tokens, "output_tokens": event.usage.output_tokens}
                            yield {"type": "message_delta", "delta": delta, "usage": usage}

                        elif event.type == "message_stop":
                            yield {"type": "message_stop", "message": {}}

                    final = await stream.get_final_message()
                    assembled = {
                        "id": final.id, "model": final.model, "role": final.role,
                        "content": [], "stop_reason": final.stop_reason,
                        "usage": {"input_tokens": final.usage.input_tokens, "output_tokens": final.usage.output_tokens},
                    }
                    for block in final.content:
                        if block.type == "text":
                            assembled["content"].append({"type": "text", "text": block.text})
                        elif block.type == "thinking":
                            assembled["content"].append({"type": "thinking", "thinking": block.thinking, "signature": block.signature})
                        elif block.type == "tool_use":
                            assembled["content"].append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                    yield {"type": "assistant_message", "message": assembled}
                return
            except APIStatusError as e:
                last_error = f"{e.status_code}: {e!s}"
                if _retryable_http_status(e.status_code) and attempt < attempts - 1:
                    delay = settings.llm_retry_base_seconds * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                yield {"type": "message_stop", "message": {}}
                yield {"type": "assistant_message", "message": {
                    "content": [{"type": "text", "text": f"LLM request failed: {last_error}"}],
                    "stop_reason": "end_turn",
                    "usage": {},
                }}
                return
            except Exception as e:
                yield {"type": "message_stop", "message": {}}
                yield {"type": "assistant_message", "message": {
                    "content": [{"type": "text", "text": f"LLM request failed: {e}"}],
                    "stop_reason": "end_turn",
                    "usage": {},
                }}
                return
