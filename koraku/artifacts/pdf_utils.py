"""PDF merge, split, and text extract (CLI: python -m koraku.artifacts.pdf_utils)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def merge_pdfs(inputs: list[str], out_path: str) -> str:
    try:
        from pypdf import PdfWriter
    except ImportError as e:
        raise SystemExit("pypdf is required. Install with: pip install 'koraku[artifacts]'") from e

    writer = PdfWriter()
    for inp in inputs:
        writer.append(str(Path(inp).expanduser().resolve()))
    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    return str(out)


def extract_text(pdf_path: str, out_txt: str | None = None) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit("pypdf is required. Install with: pip install 'koraku[artifacts]'") from e

    reader = PdfReader(str(Path(pdf_path).expanduser().resolve()))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n\n".join(parts).strip()
    if out_txt:
        out = Path(out_txt).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        return str(out)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PDF utilities for Koraku artifacts")
    sub = parser.add_subparsers(dest="command", required=True)

    merge_p = sub.add_parser("merge", help="Merge PDFs into one file")
    merge_p.add_argument("--inputs", nargs="+", required=True)
    merge_p.add_argument("--out", required=True)

    extract_p = sub.add_parser("extract-text", help="Extract text from a PDF")
    extract_p.add_argument("--input", required=True)
    extract_p.add_argument("--out", help="Optional .txt output path")

    args = parser.parse_args(argv)
    if args.command == "merge":
        path = merge_pdfs(args.inputs, args.out)
        print(json.dumps({"ok": True, "path": path, "type": "pdf", "action": "merge"}))
    elif args.command == "extract-text":
        result = extract_text(args.input, args.out)
        if args.out:
            print(json.dumps({"ok": True, "path": result, "type": "txt", "action": "extract-text"}))
        else:
            print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
