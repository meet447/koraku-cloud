"""Document attachment extraction (chat + iMessage)."""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from koraku.api.chat_routes import StreamAttachmentPart, StreamChatBody
from koraku.integrations import attachment_extract as ae


def test_is_supported_attachment_types() -> None:
    assert ae.is_supported_attachment("notes.txt", "text/plain")
    assert ae.is_supported_attachment("report.pdf")
    assert ae.is_supported_attachment("data.csv", "text/csv")
    assert not ae.is_supported_attachment("archive.zip", "application/zip")


def test_extract_text_from_txt_bytes() -> None:
    data = b"Hello from a text attachment.\nSecond line."
    row = ae.extract_text_from_bytes(data, filename="hello.txt", media_type="text/plain")
    assert row.error is None
    assert "Hello from a text attachment" in row.text
    assert not row.truncated


def test_extract_unsupported_type() -> None:
    row = ae.extract_text_from_bytes(b"data", filename="file.bin", media_type="application/octet-stream")
    assert row.error
    assert "Unsupported" in row.error


def test_process_chat_attachments_builds_markdown() -> None:
    raw = b"Quarterly summary"
    b64 = base64.b64encode(raw).decode("ascii")
    ctx = ae.process_chat_attachments(
        [{"filename": "q1.txt", "media_type": "text/plain", "data": b64}],
    )
    assert "## Attachments" in ctx
    assert "q1.txt" in ctx
    assert "Quarterly summary" in ctx


def test_save_attachment_to_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ae.settings, "chat_attachment_save_to_workspace", True, raising=False)
    rel = ae.save_attachment_to_workspace(b"payload", "doc.txt", str(tmp_path))
    assert rel
    assert (tmp_path / rel).read_bytes() == b"payload"


def test_stream_chat_body_accepts_attachments_only() -> None:
    raw = base64.b64encode(b"only attachment").decode("ascii")
    body = StreamChatBody(
        msg="",
        attachments=[
            StreamAttachmentPart(
                filename="solo.txt",
                media_type="text/plain",
                data=raw,
            )
        ],
    )
    assert len(body.attachments) == 1
    assert body.attachments[0].filename == "solo.txt"


def test_stream_attachment_rejects_unsupported() -> None:
    raw = base64.b64encode(b"x").decode("ascii")
    with pytest.raises(ValueError, match="Unsupported"):
        StreamAttachmentPart(filename="x.zip", media_type="application/zip", data=raw)


@pytest.mark.asyncio
async def test_build_imessage_user_text_document(monkeypatch: pytest.MonkeyPatch) -> None:
    import koraku.channels.inbound_media as inbound_media

    async def fake_extract(url: str) -> str | None:
        return "[Attachment: brief.txt\n```\nfrom imessage\n```]"

    monkeypatch.setattr(inbound_media, "classify_attachment_url", lambda url: "document")
    monkeypatch.setattr(inbound_media, "extract_attachment_from_url", fake_extract)

    out = await inbound_media.build_imessage_user_text(
        text="see attached",
        media_urls=["https://cdn.example.com/brief.txt"],
    )
    assert "see attached" in out
    assert "from imessage" in out
