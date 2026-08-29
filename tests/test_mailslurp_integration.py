"""
tests/test_mailslurp_integration.py
Unit tests for utils/mailslurp_integration.py (MailSlurp receiving integration).
"""
from __future__ import annotations

import json
import os
import sys
import types
from unittest.mock import patch

# Add project root to path so imports work.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit + dotenv so modules import cleanly in a non-Streamlit runtime.
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st

_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv

from utils import mailslurp_integration as ms  # noqa: E402


class _FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def read(self):
        return self._body


def _mailslurp_secret(key: str, default: str = "") -> str:
    return {"MAILSLURP_API_KEY": "test-key-123"}.get(key, default)


class TestIsConfigured:
    def test_not_configured_without_key(self):
        with patch("utils.mailslurp_integration.get_secret", return_value=""):
            assert ms.is_mailslurp_configured() is False

    def test_configured_with_key(self):
        with patch("utils.mailslurp_integration.get_secret", side_effect=_mailslurp_secret):
            assert ms.is_mailslurp_configured() is True


class TestEnsureInbox:
    def test_uses_shared_inbox_id_from_config(self):
        def secret_override(key, default=""):
            if key == "MAILSLURP_INBOX_ID":
                return "shared-id-1"
            return _mailslurp_secret(key, default)

        with patch("utils.mailslurp_integration.get_secret", side_effect=secret_override):
            ok, inbox = ms.ensure_inbox("alice")
        assert ok is True
        assert inbox["id"] == "shared-id-1"
        assert inbox["shared"] is True

    def test_creates_and_persists_inbox(self):
        created = {"id": "inb_123", "emailAddress": "sales@abc.mailslurp.com", "createdAt": "2024-01-01"}
        saved = {}

        def capturing_save(username, state):
            saved[username] = state

        with patch("utils.mailslurp_integration.get_secret", side_effect=_mailslurp_secret), \
             patch("utils.mailslurp_integration._http_post", side_effect=lambda *a, **k: (201, json.dumps(created).encode())), \
             patch("utils.mailslurp_integration._save_inbox_state", side_effect=capturing_save):
            ok, inbox = ms.ensure_inbox("alice")

        assert ok is True
        assert inbox["id"] == "inb_123"
        assert inbox["emailAddress"] == "sales@abc.mailslurp.com"
        assert saved["alice"]["id"] == "inb_123"

    def test_reuses_existing_inbox(self):
        state = {"id": "inb_existing", "emailAddress": "buyer@abc.mailslurp.com"}
        with patch("utils.mailslurp_integration.get_secret", side_effect=_mailslurp_secret), \
             patch("utils.mailslurp_integration.get_inbox_state", return_value=state), \
             patch("utils.mailslurp_integration._http_post") as mock_post:
            ok, inbox = ms.ensure_inbox("bob")
        assert ok is True
        assert inbox == state
        mock_post.assert_not_called()  # did not create a new inbox

    def test_error_without_api_key(self):
        with patch("utils.mailslurp_integration.get_secret", return_value=""):
            ok, inbox = ms.ensure_inbox("carla")
        assert ok is False
        assert "未配置" in inbox.get("error", "")


class TestFetchReceivedEmails:
    def test_normalizes_emails_and_fetches_bodies(self):
        listing = [
            {"id": "em_1", "from": "buyer@x.com", "subject": "Inquiry", "receivedAt": "2024-01-01T00:00:00Z"},
            {"id": "em_2", "from": "spam@y.com", "subject": "Promo", "receivedAt": "2024-01-01T00:01:00Z"},
        ]

        def fake_http(url, timeout=30):
            if "/inboxes/" in url and "/emails" in url:
                return 200, json.dumps(listing).encode()
            if "/emails/em_1/body" in url:
                return 200, b"We need a quote for LED lamps."
            if "/emails/em_2/body" in url:
                return 200, b"Buy our thing now!"
            return 404, b""

        with patch("utils.mailslurp_integration.get_secret", side_effect=_mailslurp_secret), \
             patch("utils.mailslurp_integration.get_inbox_state",
                   return_value={"id": "inb_123", "emailAddress": "sales@abc.mailslurp.com"}), \
             patch("utils.mailslurp_integration._http_get", side_effect=fake_http):
            ok, emails = ms.fetch_received_emails("alice", max_results=10)

        assert ok is True
        assert len(emails) == 2
        first = emails[0]
        assert first["id"] == "em_1"
        assert first["provider"] == "mailslurp"
        assert "LED lamps" in first["snippet"]
        assert first["subject"] == "Inquiry"
        assert first["is_unread"] is True

    def test_returns_error_on_fetch_failure(self):
        with patch("utils.mailslurp_integration.get_secret", side_effect=_mailslurp_secret), \
             patch("utils.mailslurp_integration.get_inbox_state",
                   return_value={"id": "inb_123", "emailAddress": "sales@abc.mailslurp.com"}), \
             patch("utils.mailslurp_integration._http_get",
                   side_effect=lambda *a, **k: (_ for _ in ()).throw(OSError("network down"))):
            ok, result = ms.fetch_received_emails("alice")
        assert ok is False
        assert isinstance(result, str)


class TestProcessReceivedInbox:
    def test_feeds_into_inbox_ai(self):
        # no network: patch fetch_received_emails to return canned messages.
        canned = [
            {"id": "em_1", "from": "buyer@x.com", "subject": "Quote request",
             "snippet": "Need pricing", "date": "d", "provider": "mailslurp"}
        ]

        fake_processed = [
            {"email_id": "em_1", "email": canned[0],
             "classification": {"intent": "inquiry", "priority_score": 60},
             "priority_score": 60}
        ]

        with patch("utils.mailslurp_integration.fetch_received_emails", return_value=(True, canned)), \
             patch("utils.inbox_ai.process_inbox", return_value=fake_processed):
            ok, processed = ms.process_received_inbox("alice")

        assert ok is True
        assert processed[0]["priority_score"] == 60

    def test_empty_inbox_returns_empty(self):
        with patch("utils.mailslurp_integration.fetch_received_emails", return_value=(True, [])):
            ok, processed = ms.process_received_inbox("alice")
        assert ok is True
        assert processed == []
