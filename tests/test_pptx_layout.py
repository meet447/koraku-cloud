"""Presentation layout normalization."""
from __future__ import annotations

from koraku.artifacts.pptx_layout import (
    normalize_presentation_spec,
    resolve_pptx_layout_index,
    slide_body_lines,
)


def test_resolve_pptx_layout_string_aliases() -> None:
    assert resolve_pptx_layout_index("two_column") == 3
    assert resolve_pptx_layout_index("title") == 0
    assert resolve_pptx_layout_index("content") == 1
    assert resolve_pptx_layout_index("2") == 2


def test_normalize_presentation_spec_converts_layout_strings() -> None:
    spec = {
        "title": "Deck",
        "slides": [
            {"title": "Overview", "layout": "two_column", "left": {"bullets": ["A"]}, "right": {"bullets": ["B"]}},
            {"title": "Data", "layout": "table", "table": {"headers": ["X", "Y"], "rows": [["1", "2"]]}},
        ],
    }
    out = normalize_presentation_spec(spec)
    assert out["slides"][0]["layout"] == 3
    assert out["slides"][1]["layout"] == 1
    assert "A" in out["slides"][0]["body"][0]
    assert "X" in out["slides"][1]["body"][0]


def test_slide_body_lines_two_column() -> None:
    lines = slide_body_lines(
        {
            "left": {"title": "Winners", "bullets": ["FMCG"]},
            "right": {"title": "Losers", "bullets": ["Energy"]},
        }
    )
    assert "Winners" in lines[0]
    assert "Energy" in lines[-1]


def test_build_pptx_spec_normalizes_before_import() -> None:
    spec = {
        "title": "Test",
        "slides": [{"title": "Slide 1", "layout": "two_column", "body": ["Point A", "Point B"]}],
    }
    out = normalize_presentation_spec(spec)
    assert out["slides"][0]["layout"] == 3
    assert out["slides"][0]["body"] == ["Point A", "Point B"]
