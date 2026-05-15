"""
tests/test_email_service.py
Unit tests for utils/email_service.py - email sending via SMTP.
"""
from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, patch

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that use it
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st

# Mock dotenv
_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda: None
sys.modules["dotenv"] = _mock_dotenv


class TestEmailService:
    """Tests for utils/email_service.py email functions."""

    def test_is_email_configured_returns_false_when_not_set(self):
        """is_email_configured returns False when SMTP vars are not set."""
        with patch("utils.secrets.get_secret", return_value=""):
            # Need to reimport to pick up the mock
            from utils.email_service import is_email_configured
            assert is_email_configured() is False

    def test_is_email_configured_returns_true_when_all_set(self):
        """is_email_configured returns True when all SMTP vars are set."""
        def mock_get_secret(key, default=""):
            secrets_map = {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "password123",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            }
            return secrets_map.get(key, default)

        with patch("utils.email_service.get_secret", side_effect=mock_get_secret):
            from utils.email_service import is_email_configured
            assert is_email_configured() is True

    def test_is_email_configured_returns_false_when_partial(self):
        """is_email_configured returns False when some SMTP vars are missing."""
        def mock_get_secret(key, default=""):
            secrets_map = {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "",
                "SMTP_PASSWORD": "password123",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            }
            return secrets_map.get(key, default)

        with patch("utils.email_service.get_secret", side_effect=mock_get_secret):
            from utils.email_service import is_email_configured
            assert is_email_configured() is False

    def test_send_email_with_mocked_smtplib(self):
        """send_email connects to SMTP and sends mail."""
        def mock_get_secret(key, default=""):
            secrets_map = {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "password123",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            }
            return secrets_map.get(key, default)

        mock_smtp_instance = MagicMock()
        mock_smtp_class = MagicMock(return_value=mock_smtp_instance)

        with patch("utils.email_service.get_secret", side_effect=mock_get_secret), \
             patch("utils.email_service.smtplib.SMTP", mock_smtp_class):
            from utils.email_service import send_email
            success, msg = send_email("recipient@example.com", "Test Subject", "Test Body")
            assert success is True
            assert "sent" in msg.lower()
            mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=30)
            mock_smtp_instance.starttls.assert_called_once()
            mock_smtp_instance.login.assert_called_once_with("user@example.com", "password123")
            mock_smtp_instance.sendmail.assert_called_once()
            mock_smtp_instance.quit.assert_called_once()

    def test_send_email_ssl_port_465(self):
        """send_email uses SMTP_SSL for port 465."""
        def mock_get_secret(key, default=""):
            secrets_map = {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "465",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "password123",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            }
            return secrets_map.get(key, default)

        mock_smtp_ssl_instance = MagicMock()
        mock_smtp_ssl_class = MagicMock(return_value=mock_smtp_ssl_instance)

        with patch("utils.email_service.get_secret", side_effect=mock_get_secret), \
             patch("utils.email_service.smtplib.SMTP_SSL", mock_smtp_ssl_class):
            from utils.email_service import send_email
            success, msg = send_email("recipient@example.com", "Test", "Body")
            assert success is True
            mock_smtp_ssl_class.assert_called_once_with("smtp.example.com", 465, timeout=30)

    def test_send_email_handles_connection_error(self):
        """send_email handles connection errors gracefully."""
        def mock_get_secret(key, default=""):
            secrets_map = {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "password123",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            }
            return secrets_map.get(key, default)

        mock_smtp_class = MagicMock(side_effect=OSError("Connection refused"))

        with patch("utils.email_service.get_secret", side_effect=mock_get_secret), \
             patch("utils.email_service.smtplib.SMTP", mock_smtp_class):
            from utils.email_service import send_email
            success, msg = send_email("recipient@example.com", "Test", "Body")
            assert success is False
            assert "error" in msg.lower() or "refused" in msg.lower()

    def test_send_email_not_configured(self):
        """send_email returns failure when SMTP is not configured."""
        with patch("utils.email_service.get_secret", return_value=""):
            from utils.email_service import send_email
            success, msg = send_email("recipient@example.com", "Test", "Body")
            assert success is False
            assert "not configured" in msg.lower()

    def test_send_verification_email_contains_token(self):
        """send_verification_email constructs message body containing the token."""
        from email import message_from_string

        def mock_get_secret(key, default=""):
            secrets_map = {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "password123",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            }
            return secrets_map.get(key, default)

        mock_smtp_instance = MagicMock()
        mock_smtp_class = MagicMock(return_value=mock_smtp_instance)

        with patch("utils.email_service.get_secret", side_effect=mock_get_secret), \
             patch("utils.email_service.smtplib.SMTP", mock_smtp_class):
            from utils.email_service import send_verification_email
            token = "test-verification-token-abc123"
            success, msg = send_verification_email("user@test.com", token)
            assert success is True
            # Check that sendmail was called with the token in the body
            call_args = mock_smtp_instance.sendmail.call_args
            sent_message = call_args[0][2]  # third arg is the message string
            # Parse the MIME message and extract the text payload
            parsed = message_from_string(sent_message)
            body = ""
            for part in parsed.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8")
                    break
            assert token in body

    def test_send_password_reset_email_contains_token(self):
        """send_password_reset_email constructs message body containing the token."""
        from email import message_from_string

        def mock_get_secret(key, default=""):
            secrets_map = {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "password123",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            }
            return secrets_map.get(key, default)

        mock_smtp_instance = MagicMock()
        mock_smtp_class = MagicMock(return_value=mock_smtp_instance)

        with patch("utils.email_service.get_secret", side_effect=mock_get_secret), \
             patch("utils.email_service.smtplib.SMTP", mock_smtp_class):
            from utils.email_service import send_password_reset_email
            token = "reset-token-xyz789"
            success, msg = send_password_reset_email("user@test.com", token)
            assert success is True
            call_args = mock_smtp_instance.sendmail.call_args
            sent_message = call_args[0][2]
            # Parse the MIME message and extract the text payload
            parsed = message_from_string(sent_message)
            body = ""
            for part in parsed.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8")
                    break
            assert token in body


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestEmailService()
    methods = [m for m in dir(cls) if m.startswith("test_")]
    passed = failed = 0
    for m in sorted(methods):
        try:
            getattr(cls, m)()
            passed += 1
            print(f"  PASS: {m}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {m}: {e}")
            traceback.print_exc()
    print(f"\nResults: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
