"""Tests for webhook HTTP status codes and AUTO_LOGIN readiness."""
from __future__ import annotations

from unittest.mock import patch


def test_webhook_receiver_returns_400_for_missing_signature():
    from webhook_receiver import application
    import io

    environ = {
        "PATH_INFO": "/api/stripe/webhook",
        "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": "10",
        "wsgi.input": io.BytesIO(b"test_body"),
        "HTTP_STRIPE_SIGNATURE": "",
    }
    status = []
    def start_response(s, h):
        status.append(s)
    application(environ, start_response)
    assert status[0] == "400 Bad Request"


def test_webhook_receiver_returns_400_for_invalid_signature():
    from webhook_receiver import application
    import io

    environ = {
        "PATH_INFO": "/api/stripe/webhook",
        "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": "10",
        "wsgi.input": io.BytesIO(b"test_body"),
        "HTTP_STRIPE_SIGNATURE": "invalid",
    }
    status = []
    def start_response(s, h):
        status.append(s)
    
    with patch("webhook_receiver.verify_and_process", return_value=(False, "Invalid signature")):
        application(environ, start_response)
    
    assert status[0] == "400 Bad Request"


def test_webhook_receiver_returns_500_for_handler_exception():
    from webhook_receiver import application
    import io

    environ = {
        "PATH_INFO": "/api/stripe/webhook",
        "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": "10",
        "wsgi.input": io.BytesIO(b"test_body"),
        "HTTP_STRIPE_SIGNATURE": "sig",
    }
    status = []
    def start_response(s, h):
        status.append(s)
    
    with patch("webhook_receiver.verify_and_process", side_effect=RuntimeError("upgrade failed")):
        application(environ, start_response)
    
    assert status[0] == "500 Internal Server Error"


def test_production_readiness_fails_when_auto_login_enabled():
    from utils.production_readiness import run_readiness_checks

    def mock_secret(key, default=""):
        if key == "AUTO_LOGIN":
            return "1"
        if key == "AUTH_REQUIRED":
            return "true"
        if key in ("NVIDIA_API_KEY", "OPENAI_API_KEY"):
            return "test_key"
        return default
    
    checks = run_readiness_checks(secret_getter=mock_secret)
    auto_login_check = next((c for c in checks if c.id == "auto_login"), None)
    assert auto_login_check is not None
    assert auto_login_check.status == "critical"


def test_production_readiness_passes_when_auto_login_disabled():
    from utils.production_readiness import run_readiness_checks

    def mock_secret(key, default=""):
        # Return empty string for AUTO_LOGIN (disabled)
        # Return reasonable defaults for other checks
        if key == "AUTO_LOGIN":
            return ""
        if key == "AUTH_REQUIRED":
            return "true"
        if key in ("NVIDIA_API_KEY", "OPENAI_API_KEY"):
            return "test_key"
        return default
    
    # Pass mock as secret_getter parameter instead of patching
    checks = run_readiness_checks(secret_getter=mock_secret)
    auto_login_check = next((c for c in checks if c.id == "auto_login"), None)
    assert auto_login_check is not None
    assert auto_login_check.status == "pass", f"Got {auto_login_check.status}: {auto_login_check.detail}"
