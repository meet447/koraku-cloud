"""Presentation spec helpers — layout aliases and slide body normalization."""
from __future__ import annotations

from typing import Any

# Standard python-pptx default template layout indices (Office theme).
_PPTX_LAYOUT_ALIASES: dict[str, int] = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "title": 0,
    "title_slide": 0,
    "cover": 0,
    "section": 2,
    "section_header": 2,
    "content": 1,
    "title_and_content": 1,
    "title_and_body": 1,
    "default": 1,
    "bullets": 1,
    "list": 1,
    "numbered": 1,
    "two_column": 3,
    "two_content": 3,
    "twocolumn": 3,
    "comparison": 3,
    "table": 1,
    "chart": 1,
    "cards": 1,
    "sources": 1,
    "disclaimer": 1,
}


def resolve_pptx_layout_index(raw: Any, *, max_layouts: int = 12) -> int:
    """Map slide ``layout`` to a safe python-pptx layout index."""
    cap = max(1, int(max_layouts))
    if raw is None or raw == "":
        return 1
    if isinstance(raw, bool):
        return 1
    if isinstance(raw, int):
        return min(max(raw, 0), cap - 1)
    text = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if text.isdigit():
        return min(max(int(text), 0), cap - 1)
    return min(max(_PPTX_LAYOUT_ALIASES.get(text, 1), 0), cap - 1)


def _lines_from_block(block: Any) -> list[str]:
    if block is None:
        return []
    if isinstance(block, str):
        return [line.strip() for line in block.split("\n") if line.strip()]
    if isinstance(block, list):
        out: list[str] = []
        for item in block:
            t = str(item).strip()
            if t:
                out.append(t)
        return out
    if isinstance(block, dict):
        out: list[str] = []
        title = str(block.get("title") or block.get("heading") or "").strip()
        if title:
            out.append(title)
        nested = block.get("bullets") or block.get("body") or block.get("items")
        out.extend(_lines_from_block(nested))
        text = str(block.get("text") or "").strip()
        if text:
            out.append(text)
        return out
    text = str(block).strip()
    return [text] if text else []


def slide_body_lines(slide_spec: dict[str, Any]) -> list[str]:
    """Flatten common slide shapes (body, left/right, table, cards) into bullet lines."""
    body = slide_spec.get("body") if "body" in slide_spec else slide_spec.get("bullets")
    if body is not None:
        return _lines_from_block(body)

    left = slide_spec.get("left")
    right = slide_spec.get("right")
    if left is not None or right is not None:
        lines: list[str] = []
        if left is not None:
            lines.extend(_lines_from_block(left))
        if right is not None:
            if lines:
                lines.append("")
            lines.extend(_lines_from_block(right))
        return lines

    table = slide_spec.get("table")
    if isinstance(table, dict):
        headers = table.get("headers") or table.get("columns") or []
        rows = table.get("rows") or []
        lines: list[str] = []
        if headers:
            lines.append(" | ".join(str(h).strip() for h in headers if str(h).strip()))
        for row in rows:
            if isinstance(row, (list, tuple)):
                lines.append(" | ".join(str(c).strip() for c in row))
            elif str(row).strip():
                lines.append(str(row).strip())
        return lines

    cards = slide_spec.get("cards")
    if isinstance(cards, list):
        lines: list[str] = []
        for card in cards:
            if isinstance(card, dict):
                title = str(card.get("title") or card.get("heading") or "").strip()
                body_text = str(card.get("body") or card.get("text") or "").strip()
                if title:
                    lines.append(title)
                if body_text:
                    lines.append(body_text)
            elif str(card).strip():
                lines.append(str(card).strip())
        return lines

    return []


def infer_pptx_layout_index(slide_spec: dict[str, Any]) -> int:
    """Infer layout when ``layout`` is omitted."""
    if slide_spec.get("left") is not None and slide_spec.get("right") is not None:
        return resolve_pptx_layout_index("two_column")
    if slide_spec.get("table") is not None:
        return resolve_pptx_layout_index("table")
    if slide_spec.get("cards") is not None:
        return resolve_pptx_layout_index("cards")
    if slide_spec.get("type") == "title":
        return 0
    return 1


def normalize_slide_spec(slide_spec: dict[str, Any], *, max_layouts: int = 12) -> dict[str, Any]:
    out = dict(slide_spec)
    raw_layout = out.get("layout")
    if raw_layout is None or raw_layout == "":
        layout_idx = infer_pptx_layout_index(out)
    else:
        layout_idx = resolve_pptx_layout_index(raw_layout, max_layouts=max_layouts)
    out["layout"] = layout_idx
    body_lines = slide_body_lines(out)
    if body_lines:
        out["body"] = body_lines
    return out


def normalize_presentation_spec(spec: dict[str, Any], *, max_layouts: int = 12) -> dict[str, Any]:
    """Normalize presentation JSON before BuildPresentation / pptx_build."""
    if not isinstance(spec, dict):
        return {}
    out = dict(spec)
    slides_in = out.get("slides")
    if not isinstance(slides_in, list):
        return out
    normalized: list[dict[str, Any]] = []
    for raw in slides_in:
        if isinstance(raw, dict):
            normalized.append(normalize_slide_spec(raw, max_layouts=max_layouts))
    out["slides"] = normalized
    return out
