---
name: pdf-worker
description: Merge PDFs or extract text in the workspace via PdfRun or pdf_utils CLI.
---

# PDF worker

Use to merge PDFs, extract text to .txt, or other simple PDF tasks.

## Output
- Default folder: `outputs/pdf/`

## Commands
- Merge: `python -m koraku.artifacts.pdf_utils merge --inputs a.pdf b.pdf --out outputs/pdf/merged.pdf`
- Extract: `python -m koraku.artifacts.pdf_utils extract-text --input file.pdf --out outputs/pdf/file.txt`

Prefer **PdfRun** when the main agent should orchestrate; use this skill for direct Bash steps inside a worker run.
