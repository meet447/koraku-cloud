"""Sanity checks for Composio per-toolkit priority slug lists."""

from koraku.integrations import composio


def test_gmail_priority_includes_send_and_draft_flow():
    slugs = composio._COMPOSIO_PRIORITY_SLUGS_BY_TOOLKIT.get("GMAIL", ())
    assert "GMAIL_CREATE_EMAIL_DRAFT" in slugs
    assert "GMAIL_SEND_DRAFT" in slugs
    assert "GMAIL_SEND_EMAIL" in slugs
    assert "GMAIL_FETCH_EMAILS" in slugs


def test_scoped_toolkit_builder_returns_empty_when_no_active_toolkits(monkeypatch):
    """Sub-agent builder yields no tools when nothing is connected (no SDK client needed)."""
    monkeypatch.setattr(composio, "is_configured", lambda: True)
    monkeypatch.setattr(composio, "active_toolkit_slugs", lambda: [])
    assert composio.build_dynamic_composio_tools_for_toolkits(["GMAIL", "SLACK"]) == []
