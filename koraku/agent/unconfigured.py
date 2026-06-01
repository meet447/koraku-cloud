"""Streams a clear configuration message when no LLM credentials are available."""
from typing import Any, AsyncIterator, Callable

from koraku.agent.run import build_user_message_blocks
from koraku.core.models import SessionState


async def run_unconfigured(
    user_input: str,
    session: SessionState,
    emit: Callable[[dict[str, Any]], None],
    image_parts: list[dict[str, str]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Emit the same stream_event shapes the web UI expects, without calling an LLM."""
    msg = (
        "Koraku is not connected to a language model yet. Set one of the following, then restart:\n\n"
        "• ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic\n"
        "• FIREWORKS_API_KEY and LLM_PROVIDER=fireworks\n"
        "• LLM_OPENAI_COMPAT_IDS=openai,groq (with OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL, …)\n"
        "• Or CUSTOM_BASE_URL alone (registers provider id ``custom``)\n\n"
        "Optional tool keys: EXA_API_KEY (WebSearch), FIRECRAWL_API_KEY (WebFetch)."
    )

    yield _emit(emit, {
        "type": "agent.mode",
        "data": {"mode": "standard", "max_steps": 0, "session_id": session.session_id},
    })
    yield _emit(emit, {"type": "agent.tools", "data": {"tools": [], "count": 0}})
    user_turn = build_user_message_blocks(user_input, list(image_parts or []))
    session.add_message("user", user_turn)

    model = "koraku-unconfigured"
    yield _emit(emit, {"type": "stream_event", "event": {"type": "message_start", "message": {
        "id": "local-unconfigured", "model": model, "role": "assistant",
        "content": [], "stop_reason": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }}})
    yield _emit(emit, {"type": "stream_event", "event": {"type": "content_block_start", "index": 0, "content_block": {
        "type": "text", "text": "",
    }}})

    for word in msg.split():
        yield _emit(emit, {"type": "stream_event", "event": {"type": "content_block_delta", "index": 0, "delta": {
            "type": "text_delta", "text": word + " ",
        }}})

    yield _emit(emit, {"type": "stream_event", "event": {"type": "content_block_stop", "index": 0}})
    yield _emit(emit, {"type": "stream_event", "event": {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {}}})
    yield _emit(emit, {"type": "stream_event", "event": {"type": "message_stop", "message": {}}})
    yield _emit(emit, {"type": "stream_event", "event": {"type": "assistant_message", "message": {
        "id": "local-unconfigured", "model": model, "role": "assistant",
        "content": [{"type": "text", "text": msg}],
        "stop_reason": "end_turn",
        "usage": {},
    }}})

    session.add_message("assistant", [{"type": "text", "text": msg}], model=model, stop_reason="end_turn")
    yield _emit(emit, {"type": "agent.completed", "data": {"reason": "unconfigured", "steps": 0, "mode": "standard"}})


def _emit(emit: Callable[[dict[str, Any]], None], event: dict[str, Any]) -> dict[str, Any]:
    emit(event)
    return event
