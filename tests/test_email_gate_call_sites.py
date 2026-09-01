"""Regression guards for consistent multi-provider email availability checks."""
from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (_ROOT / relative_path).read_text(encoding="utf-8")


def test_email_sending_pages_use_any_provider_gate():
    """Resend/SendGrid users must see the same send UI as SMTP users."""
    for relative_path in (
        "pages/1_📧_开发信.py",
        "pages/10_📅_跟进日历.py",
    ):
        source = _read(relative_path)
        assert "has_email_provider_configured" in source
        assert "is_email_configured" not in source


def test_password_reset_ui_uses_any_provider_gate():
    """Password reset availability must recognize Resend and SendGrid too."""
    source = _read("utils/ui_helpers.py")
    assert "has_email_provider_configured" in source
    assert "is_email_configured" not in source
