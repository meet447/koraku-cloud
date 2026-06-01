"""Detect paths where ``Read`` should not decode the file as UTF-8 text lines."""
from __future__ import annotations

import os

# Extensions we treat as non-text for the Read tool (same behavior local + cloud).
_BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        "pdf",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
        "odt",
        "ods",
        "odp",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
        "ico",
        "bmp",
        "tif",
        "tiff",
        "heic",
        "avif",
        "zip",
        "gz",
        "tgz",
        "tar",
        "bz2",
        "xz",
        "7z",
        "rar",
        "wasm",
        "exe",
        "dll",
        "so",
        "dylib",
        "bin",
        "mp3",
        "mp4",
        "m4a",
        "webm",
        "mov",
        "avi",
        "mkv",
        "woff",
        "woff2",
        "ttf",
        "otf",
        "eot",
        "sqlite",
        "db",
        "pkl",
        "pickle",
        "onnx",
        "pt",
        "pth",
    }
)


def file_extension_for_read_path(file_path: str) -> str:
    """Final path segment extension, lowercased, without dot (empty if none)."""
    base = os.path.basename((file_path or "").replace("\\", "/"))
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def is_binary_extension(ext: str) -> bool:
    return ext.lower() in _BINARY_EXTENSIONS


def should_use_binary_read_branch(file_path: str) -> bool:
    return is_binary_extension(file_extension_for_read_path(file_path))


def format_binary_read_response(file_path: str, size_bytes: int | None) -> str:
    ext = file_extension_for_read_path(file_path)
    ext_note = f".{ext}" if ext else "(no extension)"
    if size_bytes is None:
        size_line = "Size: unknown."
    else:
        size_line = f"Size: {size_bytes} bytes."
    return (
        "[Binary file — Read returns line-oriented text only]\n"
        f"Path: {file_path}\n"
        f"Type: {ext_note}\n"
        f"{size_line}\n\n"
        "Use **Bash** with an appropriate tool for this format, or follow a workspace **SKILL.md** under `.koraku/skills/`.\n"
        "- **PDF**: e.g. `pdftotext <path> -` if installed, or a short Python script using `pypdf`.\n"
        "- **Office (.docx etc.)**: Python `python-docx` or unpack XML from the zip container.\n"
        "- **Images**: `file` for type; for visual understanding, ask the user to attach the image in chat.\n"
    )
