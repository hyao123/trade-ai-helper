"""Tests for Inbox OAuth setup guidance (P2 dependency UX)."""
from __future__ import annotations


def test_oauth_setup_guidance_mentions_required_env_keys_and_redirect_uri():
    """Missing OAuth config guidance must tell admins exactly what to configure."""
    from utils.inbox_integration import oauth_setup_guidance

    redirect_uri = "http://localhost:8501/AI收件箱"
    text = oauth_setup_guidance(redirect_uri)

    assert "GMAIL_CLIENT_ID" in text
    assert "GMAIL_CLIENT_SECRET" in text
    assert "OUTLOOK_CLIENT_ID" in text
    assert "OUTLOOK_CLIENT_SECRET" in text
    assert redirect_uri in text
    assert "重启应用" in text or "刷新" in text
