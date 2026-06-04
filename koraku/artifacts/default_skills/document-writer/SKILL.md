---
name: document-writer
description: Create Word (.docx) documents in the workspace via DocumentRun or builder CLI.
---

# Document writer

Use when the user wants a memo, report, proposal, letter, or other Word document saved to the workspace.

## Output
- Default folder: `outputs/documents/`
- Naming: `YYYY-MM-DD-slug.docx`

## Workflow
1. Prefer **DocumentRun** with goal: audience, sections, tone, `output_path`.
2. Or write a JSON spec and run:
   `python -m koraku.artifacts.docx_build --spec spec.json --out outputs/documents/file.docx`
3. Verify with `test -f` or Glob before finishing.

## Spec example
```json
{
  "title": "Project Proposal",
  "sections": [
    {"heading": "Executive Summary", "body": "..."},
    {"heading": "Scope", "bullets": ["Item one", "Item two"]}
  ]
}
```
