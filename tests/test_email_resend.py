"""
tests/test_email_resend.py
Unit tests for utils/email_resend.py (Resend sending integration).
"""
from __future__ import annotations

import json
import os
import sys
import types
from unittest.mock import patch

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit + dotenv so modules import cleanly in a non-Streamlit runtime.
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st

_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv

from utils.email_resend import (  # noqa: E402
    RESEND_API_URL,
    _text_to_html,
    is_resend_configured,
    send_resend_email,
)

_RESEND_SECRETS = {
    "RESEND_API_KEY": "re_test_123",
    "RESEND_FROM_EMAIL": "no-reply@example.com",
    "RESEND_FROM_NAME": "Trade AI Assistant",
}


def _resend_secret(key: str, default: str = "") -> str:
    return _RESEND_SECRETS.get(key, default)


class _FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def read(self):
        return self._body


class TestResendConfig:
    def test_is_resend_configured_false_when_key_missing(self):
        with patch("utils.email_resend.get_secret", return_value=""):
            assert is_resend_configured() is False

    def test_is_resend_configured_true_when_both_set(self):
        with patch("utils.email_resend.get_secret", side_effect=_resend_secret):
            assert is_resend_configured() is True

    def test_is_resend_configured_false_when_from_missing(self):
        def secret_override(key, default=""):
            if key == "RESEND_API_KEY":
                return "re_test_123"
            return default

        with patch("utils.email_resend.get_secret", side_effect=secret_override):
            assert is_resend_configured() is False


class TestSendResendEmail:
    @patch("urllib.request.urlopen")
    @patch("utils.email_resend.get_secret", side_effect=_resend_secret)
    def test_success_sends_payload(self, mock_secret, mock_urlopen):
        mock_urlopen.return_value = _FakeResponse(200, json.dumps({"id": "email_xyz"}).encode())

        with patch("utils.analytics.track_event"):
            ok, msg, tid = send_resend_email("buyer@example.com", "Hello", "Body text")

        assert ok is True
        assert "buyer@example.com" in msg
        assert tid  # auto-generated tracking id

        # Verify the request that was sent.
        req = mock_urlopen.call_args.args[0]
        assert req.full_url == RESEND_API_URL
        assert req.get_method() == "POST"
        auth = req.get_header("Authorization")
        assert auth == "Bearer re_test_123"

        payload = json.loads(req.data.decode("utf-8"))
        assert payload["to"] == ["buyer@example.com"]
        assert payload["subject"] == "Hello"
        assert "no-reply@example.com" in payload["from"]
        assert payload["text"] == "Body text"
        assert payload["html"]  # derived HTML
        assert "X-TradeAI-Tracking-Id" in payload["headers"]

    @patch("urllib.request.urlopen")
    @patch("utils.email_resend.get_secret", side_effect=_resend_secret)
    def test_attachments_are_base64_encoded(self, mock_secret, mock_urlopen):
        mock_urlopen.return_value = _FakeResponse(202, json.dumps({"id": "email_xyz"}).encode())

        with patch("utils.analytics.track_event"):
            ok, _, _ = send_resend_email(
                "buyer@example.com",
                "Quote",
                "See attached",
                attachments=[{"filename": "quote.pdf", "content": b"%PDF-bytes", "content_type": "application/pdf"}],
            )

        assert ok is True
        req = mock_urlopen.call_args.args[0]
        payload = json.loads(req.data.decode("utf-8"))
        att = payload["attachments"][0]
        assert att["filename"] == "quote.pdf"
        assert att["content_type"] == "application/pdf"
        import base64
        assert base64.b64decode(att["content"]) == b"%PDF-bytes"

    @patch("utils.email_resend.get_secret", side_effect=_resend_secret)
    def test_http_401_returns_clear_error(self, mock_secret):
        import urllib.error

        def _raise_401(*args, **kwargs):
            raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)

        with patch("urllib.request.urlopen", side_effect=_raise_401):
            ok, msg, _ = send_resend_email("buyer@example.com", "S", "B")

        assert ok is False
        assert "无效" in msg


class TestTextToHtml:
    def test_escapes_and_breaks_lines(self):
        html = _text_to_html("Hello\n<b>world</b>")
        assert "&lt;b&gt;" in html
        assert "<br>" in html
