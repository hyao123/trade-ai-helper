"""Verified-email feature gate for core SaaS capabilities.

Public users may register and sign in before verification, but AI generation,
paid upgrades, and gated business features require a verified email address so
password recovery and account contact remain reliable.
"""
from __future__ import annotations

from utils.repositories import load_user

_EMAIL_VERIFY_MESSAGE = "⚠️ 请先验证邮箱后再使用该功能。邮箱用于密码找回和账户联系。"


def is_verified_email_user(username: str | None) -> bool:
    """Return True when the user may use verified-email-gated features."""
    if not username:
        return False
    if username == "admin":
        return True
    user = load_user(username.strip().lower())
    email = str(user.get("email", "")).strip() if user else ""
    return bool(email and user.get("email_verified") is True)


def verified_email_error_message() -> str:
    """Return the user-facing error for unverified-email feature gates."""
    return _EMAIL_VERIFY_MESSAGE


def require_verified_email(username: str | None) -> tuple[bool, str]:
    """Return ``(allowed, message)`` for a verified-email feature gate."""
    if is_verified_email_user(username):
        return True, ""
    return False, _EMAIL_VERIFY_MESSAGE
