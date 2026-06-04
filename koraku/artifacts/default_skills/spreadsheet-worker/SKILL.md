---
name: spreadsheet-worker
description: Create Excel (.xlsx) spreadsheets in the workspace via SpreadsheetRun or builder CLI.
---

# Spreadsheet worker

Use for budgets, trackers, tabular exports, or simple models.

## Output
- Default folder: `outputs/spreadsheets/`

## Workflow
1. Prefer **SpreadsheetRun** with columns, rows, and `output_path`.
2. Or `python -m koraku.artifacts.xlsx_build --spec spec.json --out outputs/spreadsheets/file.xlsx`

## Spec example
```json
{
  "headers": ["Task", "Owner", "Status"],
  "rows": [
    ["Launch", "Alex", "Done"],
    ["Review", "Sam", "In progress"]
  ]
}
```
