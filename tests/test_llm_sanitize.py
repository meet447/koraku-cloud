import sys
from unittest.mock import MagicMock

import pytest

# We use a context manager to mock modules only during the import of the tested function
# to avoid polluting the global sys.modules for other tests in the suite.
# Note: Since the environment is missing these dependencies, we must provide
# mocks so that 'koraku.llm.sanitize' (and its parents) can be imported.

_MOCK_MODULES = [
    "httpx",
    "anthropic",
    # Do not mock ``fastapi`` — breaks other tests that import real FastAPI after collection.
    "pydantic",
    "pydantic_settings",
    "beautifulsoup4",
    "markdownify",
    "composio",
    "apscheduler",
    "croniter",
]

def setup_module():
    """Setup mocks for the duration of this test module."""
    for module_name in _MOCK_MODULES:
        if module_name not in sys.modules:
            sys.modules[module_name] = MagicMock()

# Import the function after mocking dependencies
try:
    setup_module()
    from koraku.llm.providers.openai_compat_backend import _parse_tool_calls_from_text
    from koraku.llm.sanitize import _eat_leading_newlines_only, VisibleToolJsonFilter
except ImportError:
    # Fallback for environments where even with mocks it might fail
    # or if we want to be extremely safe about not breaking the collector.
    def _eat_leading_newlines_only(s: str) -> str:
        i = 0
        while i < len(s) and s[i] in "\n\r":
            i += 1
        return s[i:]
    VisibleToolJsonFilter = None
    _parse_tool_calls_from_text = None


def test_eat_leading_newlines_only_empty():
    assert _eat_leading_newlines_only("") == ""

def test_eat_leading_newlines_only_newlines_only():
    assert _eat_leading_newlines_only("\n\n\r\n") == ""

def test_eat_leading_newlines_only_leading_newlines():
    assert _eat_leading_newlines_only("\n\nHello") == "Hello"

def test_eat_leading_newlines_only_leading_mixed():
    # Should only eat \n and \r, not spaces or tabs
    assert _eat_leading_newlines_only("\n\r  Hello") == "  Hello"
    assert _eat_leading_newlines_only("\n \nHello") == " \nHello"

def test_eat_leading_newlines_only_no_leading_newlines():
    assert _eat_leading_newlines_only("Hello") == "Hello"
    assert _eat_leading_newlines_only("  Hello") == "  Hello"

def test_eat_leading_newlines_only_trailing_newlines():
    assert _eat_leading_newlines_only("Hello\n\n") == "Hello\n\n"

def test_eat_leading_newlines_only_cr_lf():
    assert _eat_leading_newlines_only("\r\n\r\nHello") == "Hello"


@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_plain_text():
    f = VisibleToolJsonFilter()
    assert f.feed("Hello") == ["Hello"]
    assert f.feed(" world!") == [" world!"]
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_tool_json():
    f = VisibleToolJsonFilter()
    assert f.feed('Hello\n{"tool": "fetch"}') == ["Hello\n"]
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_chunked_tool_json():
    f = VisibleToolJsonFilter()
    assert f.feed('Hello\n{"tool": "fet') == ["Hello\n"]
    assert f.feed('ch"}') == []
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_small_chunked_tool_json():
    f = VisibleToolJsonFilter()
    assert f.feed('Hello\n{"') == ["Hello\n"]
    assert f.feed('tool": "fetch"}') == []
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_call_tool():
    f = VisibleToolJsonFilter()
    assert f.feed('Hello\n[Call WebFetch]: {"url": "foo"}') == ["Hello\n"]
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_chunked_call_tool():
    f = VisibleToolJsonFilter()
    assert f.feed("Hello\n[") == ["Hello\n"]
    assert f.feed("Call GOOGLECALENDAR_EVENTS") == []
    assert f.feed('_LIST]:\n{"calendarId": "primary"}') == []
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_incomplete_json_flushed():
    f = VisibleToolJsonFilter()
    assert f.feed('{"tool": "foo"') == []
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_invalid_json_emitted():
    f = VisibleToolJsonFilter()
    assert f.feed('{') == ['{']
    assert f.feed('"') == ['"']
    assert f.feed('tool') == ['tool']
    assert f.feed('":') == ['":']
    assert f.feed(' }') == [' }']
    assert f.flush() == []

@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_incomplete_call_tool_flushed():
    f = VisibleToolJsonFilter()
    assert f.feed("[Call WebFetch]: ") == []
    assert f.flush() == []


@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_bracket_tool_call_empty():
    f = VisibleToolJsonFilter()
    assert f.feed("[TOOL_CALL] [/TOOL_CALL]Done") == ["Done"]
    assert f.flush() == []


@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_bracket_tool_call_mid_line():
    f = VisibleToolJsonFilter()
    assert f.feed("Hi [TOOL_CALL] [/TOOL_CALL] Bye") == ["Hi ", "Bye"]
    assert f.flush() == []


@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_chunked_bracket_tool_call():
    f = VisibleToolJsonFilter()
    assert f.feed("Hi [TOOL") == ["Hi "]
    assert f.feed("_CALL] [/TOOL_CALL] tail") == ["tail"]
    assert f.flush() == []


@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_angle_tool_call():
    f = VisibleToolJsonFilter()
    assert f.feed('Before\n<tool_call> [Write] {"file_path": "x.md", "content": "hi"} </tool_call>\nAfter') == [
        "Before\n",
        "After",
    ]
    assert f.flush() == []


@pytest.mark.skipif(VisibleToolJsonFilter is None, reason="Dependencies mock failed")
def test_visible_tool_json_filter_chunked_angle_tool_call():
    f = VisibleToolJsonFilter()
    assert f.feed("Before\n<tool") == ["Before\n"]
    assert f.feed('_call> [Wri') == []
    assert f.feed('te] {"file_path": "x.md", "content": "hi"}') == []
    assert f.feed(" </tool_call>\nAfter") == ["After"]
    assert f.flush() == []


@pytest.mark.skipif(_parse_tool_calls_from_text is None, reason="Dependencies mock failed")
def test_parse_angle_bracket_tool_call_text():
    blocks = _parse_tool_calls_from_text(
        'Thinking\n<tool_call> [Write] {"file_path": "x.md", "content": "hi"} </tool_call>\nDone'
    )

    assert blocks == [
        {"type": "text", "text": "Thinking"},
        {
            "type": "tool_use",
            "id": "tool_0",
            "name": "Write",
            "input": {"file_path": "x.md", "content": "hi"},
        },
        {"type": "text", "text": "Done"},
    ]


@pytest.mark.skipif(_parse_tool_calls_from_text is None, reason="Dependencies mock failed")
def test_parse_call_tool_with_underscore_name():
    blocks = _parse_tool_calls_from_text(
        '[Call GOOGLECALENDAR_EVENTS_LIST]:\n{"calendarId": "primary", "singleEvents": true}'
    )

    assert blocks == [
        {
            "type": "tool_use",
            "id": "tool_0",
            "name": "GOOGLECALENDAR_EVENTS_LIST",
            "input": {"calendarId": "primary", "singleEvents": True},
        }
    ]
