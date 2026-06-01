"""Security tests for custom AI provider validation."""
from __future__ import annotations

import os
import sys
import types
from unittest.mock import patch

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dotenv before importing modules that use it (not available in test env)
_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv

from utils.ai_gateway import (  # noqa: E402
    _custom_client_cache_key,
    _get_custom_provider_config,
    _redact,
    _validate_custom_provider_base_url,
)


def test_validate_custom_provider_requires_https():
    ok, normalized, reason = _validate_custom_provider_base_url("http://api.example.com/v1")
    assert ok is False
    assert normalized == ""
    assert "https" in reason


def test_validate_custom_provider_rejects_credentials_query_and_fragment():
    cases = [
        "https://user:pass@api.example.com/v1",
        "https://api.example.com/v1?api_key=abc",
        "https://api.example.com/v1#token",
    ]
    for url in cases:
        ok, normalized, _reason = _validate_custom_provider_base_url(url)
        assert ok is False
        assert normalized == ""


def test_validate_custom_provider_rejects_localhost_and_private_ip():
    cases = [
        "https://localhost/v1",
        "https://localhost.localdomain/v1",
        "https://127.0.0.1/v1",
        "https://10.0.0.1/v1",
        "https://172.16.0.1/v1",
        "https://192.168.1.1/v1",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/v1",
    ]
    for url in cases:
        ok, normalized, _reason = _validate_custom_provider_base_url(url)
        assert ok is False
        assert normalized == ""


def test_validate_custom_provider_allows_public_https_hostname():
    with patch("utils.ai_gateway._resolve_host_ips", return_value={"93.184.216.34"}):
        ok, normalized, reason = _validate_custom_provider_base_url("https://api.example.com/v1/")
    assert ok is True
    assert normalized == "https://api.example.com/v1"
    assert reason == ""


def test_validate_custom_provider_rejects_hostname_resolving_to_private_ip():
    with patch("utils.ai_gateway._resolve_host_ips", return_value={"127.0.0.1"}):
        ok, normalized, _reason = _validate_custom_provider_base_url("https://api.example.com/v1")
    assert ok is False
    assert normalized == ""


def test_get_custom_provider_config_rejects_unsafe_url():
    prefs = {
        "custom_provider_enabled": "true",
        "custom_provider_base_url": "https://127.0.0.1/v1",
        "custom_provider_api_key": "sk-secret",
        "custom_provider_model": "test-model",
        "custom_provider_name": "Local Test",
    }
    with patch.dict(sys.modules, {"utils.user_prefs": types.SimpleNamespace(get_prefs=lambda: prefs)}):
        assert _get_custom_provider_config() is None


def test_get_custom_provider_config_normalizes_safe_url():
    prefs = {
        "custom_provider_enabled": "true",
        "custom_provider_base_url": "https://api.example.com/v1/",
        "custom_provider_api_key": "sk-secret",
        "custom_provider_model": "test-model",
        "custom_provider_name": "Example",
    }
    with patch.dict(sys.modules, {"utils.user_prefs": types.SimpleNamespace(get_prefs=lambda: prefs)}), \
         patch("utils.ai_gateway._resolve_host_ips", return_value={"93.184.216.34"}):
        cfg = _get_custom_provider_config()
    assert cfg is not None
    assert cfg["base_url"] == "https://api.example.com/v1"
    assert cfg["api_key"] == "sk-secret"
    assert cfg["model_id"] == "test-model"


def test_custom_client_cache_key_does_not_include_raw_api_key():
    key = _custom_client_cache_key("https://api.example.com/v1", "sk-super-secret")
    assert "sk-super-secret" not in key
    assert "sha256:" in key


def test_redact_hides_supplied_secrets_and_sensitive_query_values():
    text = _redact(
        "Request failed for https://api.example.com/v1?api_key=abc123 with Bearer token123 and sk-secret",
        ["sk-secret"],
    )
    assert "abc123" not in text
    assert "token123" not in text
    assert "sk-secret" not in text
    assert "[REDACTED]" in text
