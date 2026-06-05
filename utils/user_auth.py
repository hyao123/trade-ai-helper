"""
utils/user_auth.py
------------------
Multi-user authentication system with registration, login, session management,
and per-user data isolation.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

from utils.logger import get_logger
from utils.repositories import (
    load_login_failures,
    load_users,
    save_login_failures,
    save_users,
)
from utils.storage import get_data_dir

logger = get_logger("user_auth")

_PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_HASH_VERSION = "v2"
_PBKDF2_ITERATIONS = 310_000
_LEGACY_PBKDF2_ITERATIONS = 100_000
_PASSWORD_MIN_LENGTH = 10
_LOGIN_FAILURE_LIMIT = 5
_LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60
_USERS_DB_FILENAME = "users_db.json"
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_COMMON_WEAK_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty123",
    "admin12345",
    "letmein123",
}


def _get_users_db_path() -> Path:
    """Return path to the users database JSON file for legacy callers/tests."""
    return get_data_dir() / _USERS_DB_FILENAME


def _get_users_dir() -> Path:
    """Return path to the data/users/ directory. Creates it if needed."""
    users_dir = get_data_dir() / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    return users_dir


def _pbkdf2_hex(password: str, salt: str, iterations: int) -> str:
    """Return PBKDF2-HMAC-SHA256 hex digest."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()


def _hash_password(password: str, salt: str | None = None, iterations: int = _PBKDF2_ITERATIONS) -> str:
    """Hash a password using a versioned PBKDF2-HMAC-SHA256 format.

    New format:
        pbkdf2_sha256$v2$310000$salt$hash

    Legacy ``salt:hash`` records are still verified by ``_verify_password`` and
    are upgraded automatically after successful login.
    """
    if salt is None:
        salt = os.urandom(16).hex()
    digest = _pbkdf2_hex(password, salt, iterations)
    return f"{_PASSWORD_HASH_ALGORITHM}${_PASSWORD_HASH_VERSION}${iterations}${salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against either versioned or legacy stored hash strings."""
    if not stored_hash:
        return False

    if stored_hash.startswith(f"{_PASSWORD_HASH_ALGORITHM}$"):
        try:
            algorithm, _version, iterations_str, salt, digest = stored_hash.split("$", 4)
            if algorithm != _PASSWORD_HASH_ALGORITHM:
                return False
            iterations = int(iterations_str)
        except (ValueError, TypeError):
            return False
        expected = f"{algorithm}${_PASSWORD_HASH_VERSION}${iterations}${salt}${_pbkdf2_hex(password, salt, iterations)}"
        # Compare only the digest portion through an equivalently-shaped string.
        return hmac.compare_digest(expected.rsplit("$", 1)[-1], digest)

    # Legacy format: salt:hash using 100k PBKDF2 iterations.
    if ":" not in stored_hash:
        return False
    salt, legacy_digest = stored_hash.split(":", 1)
    return hmac.compare_digest(_pbkdf2_hex(password, salt, _LEGACY_PBKDF2_ITERATIONS), legacy_digest)


def _password_needs_rehash(stored_hash: str) -> bool:
    """Return True when a stored hash should be upgraded to the current policy."""
    if not stored_hash.startswith(f"{_PASSWORD_HASH_ALGORITHM}$"):
        return True
    try:
        algorithm, version, iterations_str, _salt, _digest = stored_hash.split("$", 4)
        return (
            algorithm != _PASSWORD_HASH_ALGORITHM
            or version != _PASSWORD_HASH_VERSION
            or int(iterations_str) < _PBKDF2_ITERATIONS
        )
    except (ValueError, TypeError):
        return True


def _is_strong_password(password: str) -> bool:
    """Return True when a password meets the current minimum policy."""
    if not password or len(password) < _PASSWORD_MIN_LENGTH:
        return False
    if password.strip().lower() in _COMMON_WEAK_PASSWORDS:
        return False
    return True


def _password_policy_message() -> str:
    """Return user-facing password policy guidance."""
    return f"Password must be at least {_PASSWORD_MIN_LENGTH} characters and not be a common weak password"


def _is_valid_email(email: str) -> bool:
    """Return True when the email is present and roughly RFC-like."""
    return bool(email and _EMAIL_RE.match(email.strip()))


def _load_login_failures() -> dict:
    """Load login failure counters keyed by normalized username."""
    return load_login_failures()


def _save_login_failures(failures: dict) -> None:
    """Persist login failure counters."""
    save_login_failures(failures)


def _active_failures(username: str, now: float | None = None) -> list[float]:
    """Return recent failed-login timestamps for a username."""
    current_time = time.time() if now is None else now
    failures = _load_login_failures()
    active = [
        float(ts)
        for ts in failures.get(username, [])
        if current_time - float(ts) < _LOGIN_FAILURE_WINDOW_SECONDS
    ]
    failures[username] = active
    _save_login_failures(failures)
    return active


def _is_login_locked(username: str) -> bool:
    """Return True if recent failures exceed the login lock threshold."""
    return len(_active_failures(username)) >= _LOGIN_FAILURE_LIMIT


def _record_login_failure(username: str) -> None:
    """Record a failed login attempt for rate limiting."""
    failures = _load_login_failures()
    now = time.time()
    active = [
        float(ts)
        for ts in failures.get(username, [])
        if now - float(ts) < _LOGIN_FAILURE_WINDOW_SECONDS
    ]
    active.append(now)
    failures[username] = active
    _save_login_failures(failures)


def _clear_login_failures(username: str) -> None:
    """Clear failed-login attempts after a successful login."""
    failures = _load_login_failures()
    if username in failures:
        failures.pop(username, None)
        _save_login_failures(failures)


def _load_users_db() -> dict:
    """Load users database from the active database backend."""
    return load_users()


def _save_users_db(users: dict) -> None:
    """Save users database through the active database backend."""
    save_users(users)


def _build_public_user_info(user: dict) -> dict:
    """Return session-safe user info without password or token fields."""
    return {
        "username": user["username"],
        "email": user.get("email", ""),
        "tier": user.get("tier", "free"),
        "created_at": user.get("created_at", ""),
        "email_verified": user.get("email_verified", False),
        "language": user.get("language", ""),
    }


def _extract_token_data(token_data) -> tuple[str, str]:
    """Support both legacy bare string tokens and dict token payloads."""
    if isinstance(token_data, dict):
        return token_data.get("token", ""), token_data.get("expires", "")
    return str(token_data or ""), ""


def register_user(username: str, password: str, email: str = "") -> tuple[bool, str]:
    """Register a new user. Email is required for password recovery and contact."""
    if not username or not username.strip():
        return False, "Username cannot be empty"
    username = username.strip().lower()
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if not username.isalnum():
        return False, "Username must contain only letters and numbers"
    if not _is_valid_email(email):
        return False, "Email is required for password recovery and account contact"
    if not _is_strong_password(password):
        return False, _password_policy_message()

    email = email.strip().lower()
    users = _load_users_db()
    if username in users:
        return False, "Username already exists"
    for existing in users.values():
        if existing.get("email", "").strip().lower() == email:
            return False, "Email is already registered"

    verification_token = secrets.token_urlsafe(32)
    users[username] = {
        "username": username,
        "email": email,
        "password_hash": _hash_password(password),
        "tier": "free",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "email_verified": False,
        "verification_token": {
            "token": verification_token,
            "expires": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        },
    }
    _save_users_db(users)

    user_dir = get_user_data_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)

    from utils.email_service import is_email_configured, send_verification_email
    if is_email_configured():
        send_verification_email(email, verification_token)

    st.session_state.authenticated = True
    st.session_state["current_user"] = _build_public_user_info(users[username])
    if users[username].get("language"):
        st.session_state["language"] = users[username]["language"]

    logger.info("User registered and authenticated: %s", username)
    return True, "Registration successful"


def authenticate_user(username: str, password: str) -> tuple[bool, dict | None]:
    """Authenticate a user by username and password."""
    if not username or not password:
        return False, None

    username = username.strip().lower()
    if _is_login_locked(username):
        logger.warning("Login temporarily locked for user: %s", username)
        return False, None

    users = _load_users_db()
    if username not in users:
        _record_login_failure(username)
        return False, None

    user = users[username]
    if _verify_password(password, user["password_hash"]):
        if _password_needs_rehash(user.get("password_hash", "")):
            users[username]["password_hash"] = _hash_password(password)
            _save_users_db(users)
            user = users[username]
            logger.info("Password hash upgraded for user: %s", username)
        _clear_login_failures(username)
        user_info = _build_public_user_info(user)
        logger.info("User authenticated: %s", username)
        return True, user_info

    _record_login_failure(username)
    return False, None


def get_current_user() -> dict | None:
    """Get the currently logged-in user from session state."""
    return st.session_state.get("current_user", None)


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """Change a user's password."""
    if not _is_strong_password(new_password):
        return False, _password_policy_message()

    username = username.strip().lower()
    users = _load_users_db()
    if username not in users:
        return False, "User not found"
    if not _verify_password(old_password, users[username]["password_hash"]):
        return False, "Current password is incorrect"

    users[username]["password_hash"] = _hash_password(new_password)
    _save_users_db(users)
    logger.info("Password changed for user: %s", username)
    return True, "Password changed successfully"


def get_user_data_dir(username: str) -> Path:
    """Return the data directory for a specific user. Creates it if needed."""
    if not username.isalnum():
        raise ValueError("Invalid username")
    user_dir = _get_users_dir() / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def verify_email_token(username: str, token: str) -> tuple[bool, str]:
    """Verify an email verification token for a user."""
    if not username or not token:
        return False, "Username and token are required"

    username = username.strip().lower()
    users = _load_users_db()
    if username not in users:
        return False, "User not found"

    user = users[username]
    stored_token, expires_str = _extract_token_data(user.get("verification_token", ""))
    if not stored_token:
        return False, "No verification token found"
    if not hmac.compare_digest(token, stored_token):
        return False, "Invalid verification token"

    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str)
            now = datetime.now(timezone.utc)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if now > expires_dt:
                return False, "Token expired"
        except (ValueError, TypeError):
            pass

    users[username]["email_verified"] = True
    users[username]["verification_token"] = ""
    _save_users_db(users)
    logger.info("Email verified for user: %s", username)
    return True, "Email verified successfully"


def resend_verification_email(username: str) -> tuple[bool, str]:
    """Generate a new verification token and resend the verification email."""
    if not username:
        return False, "Username is required"

    username = username.strip().lower()
    users = _load_users_db()
    if username not in users:
        return False, "User not found"

    user = users[username]
    email = user.get("email", "")
    if not email:
        return False, "No email address on file"

    from utils.email_service import is_email_configured, send_verification_email
    if not is_email_configured():
        return False, "Email service is not configured"

    new_token = secrets.token_urlsafe(32)
    users[username]["verification_token"] = {
        "token": new_token,
        "expires": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }
    users[username]["email_verified"] = False
    _save_users_db(users)

    success, msg = send_verification_email(email, new_token)
    if success:
        return True, "Verification email sent"
    return False, f"Failed to send email: {msg}"


def find_user_by_email(email: str) -> str | None:
    """Scan users from the active database backend for a matching email field."""
    if not email:
        return None
    email_lower = email.strip().lower()
    users = _load_users_db()
    for username, user_data in users.items():
        if user_data.get("email", "").strip().lower() == email_lower:
            return username
    return None


def request_password_reset(email_or_username: str) -> tuple[bool, str]:
    """Request a password reset for a user identified by email or username."""
    vague_message = "If an account exists with that email, a reset link has been sent"
    if not email_or_username or not email_or_username.strip():
        return True, vague_message

    identifier = email_or_username.strip()
    username = None
    if "@" in identifier:
        username = find_user_by_email(identifier)
    else:
        candidate = identifier.lower()
        users = _load_users_db()
        if candidate in users:
            username = candidate

    if username is None:
        return True, vague_message

    users = _load_users_db()
    user = users.get(username)
    if not user:
        return True, vague_message
    user_email = user.get("email", "").strip()
    if not user_email:
        return True, vague_message

    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    users[username]["reset_token"] = {"token": token, "expires": expires}
    _save_users_db(users)

    from utils.email_service import is_email_configured, send_password_reset_email
    if is_email_configured():
        send_password_reset_email(user_email, token)

    logger.info("Password reset requested for user: %s", username)
    return True, "Reset email sent"


def reset_password(username: str, token: str, new_password: str) -> tuple[bool, str]:
    """Reset a user's password using a reset token."""
    if not _is_strong_password(new_password):
        return False, _password_policy_message()
    if not username or not token:
        return False, "Username and token are required"

    username = username.strip().lower()
    users = _load_users_db()
    if username not in users:
        return False, "Invalid token"

    user = users[username]
    reset_token_data = user.get("reset_token")
    if not reset_token_data:
        return False, "Invalid token"

    stored_token, expires_str = _extract_token_data(reset_token_data)
    if not stored_token or not hmac.compare_digest(token, stored_token):
        return False, "Invalid token"

    try:
        expires_dt = datetime.fromisoformat(expires_str)
        now = datetime.now(timezone.utc)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if now > expires_dt:
            return False, "Token expired"
    except (ValueError, TypeError):
        return False, "Invalid token"

    users[username]["password_hash"] = _hash_password(new_password)
    users[username].pop("reset_token", None)
    _save_users_db(users)
    logger.info("Password reset completed for user: %s", username)
    return True, "Password reset successful"
