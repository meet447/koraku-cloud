"""iMessage file attachment queue."""
from __future__ import annotations

import os

import pytest

from koraku.channels import file_attachments as fa
from koraku.channels.context import ActiveChannel, reset_active_channel, set_active_channel


@pytest.fixture
def imessage_channel():
    ch = ActiveChannel(
        kind="imessage",
        outbound_phone="+15551234567",
        thread_id="t1",
        user_id="u1",
        org_id="o1",
    )
    t1, t2 = set_active_channel(ch)
    cap = fa.start_imessage_file_capture()
    yield
    fa.end_imessage_file_capture(cap)
    reset_active_channel(t1, t2)


def test_record_host_file_when_imessage_active(imessage_channel, tmp_path) -> None:
    f = tmp_path / "report.pdf"
    f.write_bytes(b"%PDF-1.4")
    fa.record_host_file_if_imessage(str(f), logical_path="report.pdf")
    pending = fa.drain_imessage_attachments()
    assert len(pending) == 1
    assert pending[0].display_name == "report.pdf"


def test_skips_env_files(imessage_channel, tmp_path) -> None:
    f = tmp_path / ".env"
    f.write_text("SECRET=1\n")
    fa.record_host_file_if_imessage(str(f))
    assert fa.drain_imessage_attachments() == []


def test_no_record_without_imessage_channel(tmp_path) -> None:
    cap = fa.start_imessage_file_capture()
    try:
        f = tmp_path / "notes.txt"
        f.write_text("hi")
        fa.record_host_file_if_imessage(str(f))
        assert fa.drain_imessage_attachments() == []
    finally:
        fa.end_imessage_file_capture(cap)
