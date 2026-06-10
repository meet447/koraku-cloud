---
name: presentation-builder
description: Create PowerPoint (.pptx) decks in the workspace via PresentationRun or BuildPresentation.
---

# Presentation builder

Use when the user wants slides, a pitch deck, QBR, or training presentation.

## Output
- Default folder: `outputs/presentations/`
- Naming: `YYYY-MM-DD-slug.pptx`
- **Workspace-relative paths only** — never `/Users/.../koraku-cloud`

## Workflow
1. Prefer **PresentationRun** from the main agent, or inside the worker:
2. Compose JSON spec → call **BuildPresentation** with `output_path` and `spec` (JSON string).
3. Verify with **Glob** before finishing.

Do **not** use `python -m koraku.artifacts.pptx_build` in Bash unless BuildPresentation fails.

## Spec example
```json
{
  "title": "Understanding LLMs",
  "subtitle": "A quick introduction",
  "slides": [
    {"title": "What is an LLM?", "body": ["Large neural network", "Trained on text data"]},
    {"title": "Compare", "layout": "two_column", "left": {"bullets": ["Pros"]}, "right": {"bullets": ["Cons"]}}
  ]
```

`layout` accepts integers **or** string aliases (`title`, `content`, `two_column`, `table`, `cards`, `list`, `sources`). Aliases are normalized automatically.
}
```
