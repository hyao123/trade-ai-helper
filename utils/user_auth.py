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
    load_email_verification_requests,
    load_login_failures,
    load_password_reset_requests,
    load_users,
    save_email_verification_requests,
    save_login_failures,
    save_password_reset_requests,
    save_users,
)
from utils.security_audit import audit_event
from utils.storage import get_data_dir

logger = get_logger("user_auth")

_PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_HASH_VERSION = "v2"
_TOKEN_HASH_ALGORITHM = "sha256"
_PBKDF2_ITERATIONS = 310_000
_LEGACY_PBKDF2_ITERATIONS = 100_000
_PASSWORD_MIN_LENGTH = 10
_LOGIN_FAILURE_LIMIT = 5
_LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60
_PASSWORD_RESET_REQUEST_LIMIT = 3
_PASSWORD_RESET_REQUEST_WINDOW_SECONDS = 15 * 60
_EMAIL_VERIFICATION_REQUEST_LIMIT = 3
_EMAIL_VERIFICATION_REQUEST_WINDOW_SECONDS = 15 * 60
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


def _load_password_reset_requests() -> dict:
    """Load password reset request counters keyed by hashed identifier."""
    return load_password_reset_requests()


def _save_password_reset_requests(requests: dict) -> None:
    """Persist password reset request counters."""
    save_password_reset_requests(requests)


def _load_email_verification_requests() -> dict:
    """Load verification email request counters keyed by hashed username."""
    return load_email_verification_requests()


def _save_email_verification_requests(requests: dict) -> None:
    """Persist verification email request counters."""
    save_email_verification_requests(requests)


def _prune_timestamp_counters(counters: dict, *, window_seconds: int, now: float) -> dict[str, list[float]]:
    """Return counters with only valid timestamps inside the active window."""
    pruned: dict[str, list[float]] = {}
    for key, timestamps in counters.items():
        if not isinstance(timestamps, list):
            continue
        active: list[float] = []
        for ts in timestamps:
            try:
                ts_float = float(ts)
            except (TypeError, ValueError):
                continue
            if now - ts_float < window_seconds:
                active.append(ts_float)
        if active:
            pruned[str(key)] = active
    return pruned


def _active_failures(username: str, now: float | None = None) -> list[float]:
    """Return recent failed-login timestamps for a username."""
    current_time = time.time() if now is None else now
    failures = _prune_timestamp_counters(
        _load_login_failures(),
        window_seconds=_LOGIN_FAILURE_WINDOW_SECONDS,
        now=current_time,
    )
    active = failures.get(username, [])
    _save_login_failures(failures)
    return active


def _is_login_locked(username: str) -> bool:
    """Return True if recent failures exceed the login lock threshold."""
    return len(_active_failures(username)) >= _LOGIN_FAILURE_LIMIT


def _record_login_failure(username: str) -> None:
    """Record a failed login attempt for rate limiting."""
    now = time.time()
    failures = _prune_timestamp_counters(
        _load_login_failures(),
        window_seconds=_LOGIN_FAILURE_WINDOW_SECONDS,
        now=now,
    )
    active = failures.get(username, [])
    active.append(now)
    failures[username] = active
    _save_login_failures(failures)


def _clear_login_failures(username: str) -> None:
    """Clear failed-login attempts after a successful login."""
    failures = _load_login_failures()
    if username in failures:
        failures.pop(username, None)
        _save_login_failures(failures)


def _password_reset_request_key(identifier: str) -> str:
    """Return a non-reversible key for password reset rate limiting."""
    return _hash_token(identifier.strip().lower())


def _consume_windowed_request(
    requests: dict,
    key: str,
    *,
    limit: int,
    window_seconds: int,
    now: float | None = None,
) -> tuple[bool, dict]:
    """Record a request in a sliding window and return updated counters."""
    current_time = time.time() if now is None else now
    requests = _prune_timestamp_counters(requests, window_seconds=window_seconds, now=current_time)
    active = requests.get(key, [])
    if len(active) >= limit:
        requests[key] = active
        return False, requests

    active.append(current_time)
    requests[key] = active
    return True, requests


def _consume_password_reset_request(identifier: str, now: float | None = None) -> bool:
    """Record a password reset request and return False when rate limited."""
    allowed, requests = _consume_windowed_request(
        _load_password_reset_requests(),
        _password_reset_request_key(identifier),
        limit=_PASSWORD_RESET_REQUEST_LIMIT,
        window_seconds=_PASSWORD_RESET_REQUEST_WINDOW_SECONDS,
        now=now,
    )
    _save_password_reset_requests(requests)
    return allowed


def _email_verification_request_key(username: str) -> str:
    """Return a non-reversible key for verification email rate limiting."""
    return _hash_token(username.strip().lower())


def _consume_email_verification_request(username: str, now: float | None = None) -> bool:
    """Record a verification resend request and return False when rate limited."""
    allowed, requests = _consume_windowed_request(
        _load_email_verification_requests(),
        _email_verification_request_key(username),
        limit=_EMAIL_VERIFICATION_REQUEST_LIMIT,
        window_seconds=_EMAIL_VERIFICATION_REQUEST_WINDOW_SECONDS,
        now=now,
    )
    _save_email_verification_requests(requests)
    return allowed


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


def _hash_token(token: str) -> str:
    """Return a one-way hash for account recovery and verification tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_token_record(token: str, expires: str) -> dict:
    """Build a persisted token record without storing the raw token."""
    return {
        "algorithm": _TOKEN_HASH_ALGORITHM,
        "token_hash": _hash_token(token),
        "expires": expires,
    }


def _extract_token_data(token_data) -> tuple[str, str, bool]:
    """Support current hashed tokens plus legacy raw-token payloads."""
    if isinstance(token_data, dict):
        if token_data.get("token_hash"):
            return token_data.get("token_hash", ""), token_data.get("expires", ""), True
        return token_data.get("token", ""), token_data.get("expires", ""), False
    return str(token_data or ""), "", False


def _token_matches(token: str, token_data) -> tuple[bool, str]:
    """Return whether a provided token matches stored data and its expiry."""
    stored_token, expires_str, is_hashed = _extract_token_data(token_data)
    if not stored_token:
        return False, expires_str
    candidate = _hash_token(token) if is_hashed else token
    return hmac.compare_digest(candidate, stored_token), expires_str


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
    verification_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    users[username] = {
        "username": username,
        "email": email,
        "password_hash": _hash_password(password),
        "tier": "free",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "email_verified": False,
        "verification_token": _build_token_record(verification_token, verification_expires),
    }
    _save_users_db(users)

    user_dir = get_user_data_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)

    from utils.email_service import is_email_configured, send_verification_email
    if is_email_configured():
        send_verification_email(email, verification_token)

    st.session_state["authenticated"] = True
    st.session_state["current_user"] = _build_public_user_info(users[username])
    if users[username].get("language"):
        st.session_state["language"] = users[username]["language"]

    logger.info("User registered and authenticated: %s", username)
    audit_event("user_registered", "success", user_id=username)
    return True, "Registration successful"


def authenticate_user(username: str, password: str) -> tuple[bool, dict | None]:
    """Authenticate a user by username and password."""
    if not username or not password:
        return False, None

    username = username.strip().lower()
    if _is_login_locked(username):
        logger.warning("Login temporarily locked for user: %s", username)
        audit_event("login_locked", "blocked", user_id=username, severity="warning")
        return False, None

    users = _load_users_db()
    if username not in users:
        _record_login_failure(username)
        audit_event("login_failed", "unknown_user", user_id=username, severity="warning")
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
        audit_event("login_succeeded", "success", user_id=username)
        return True, user_info

    _record_login_failure(username)
    locked_after_failure = _is_login_locked(username)
    audit_event(
        "login_failed",
        "invalid_password",
        user_id=username,
        severity="warning",
        metadata={"locked_after_failure": locked_after_failure},
    )
    if locked_after_failure:
        audit_event("login_locked", "threshold_reached", user_id=username, severity="warning")
    return False, None


def get_current_user() -> dict | None:
    """Get the currently logged-in user from session state."""
    return st.session_state.get("current_user", None)


def is_current_admin() -> bool:
    """Return True only for an authenticated admin session."""
    current_user = get_current_user()
    return bool(
        st.session_state.get("authenticated")
        and current_user
        and current_user.get("username") == "admin"
        and current_user.get("tier") == "enterprise"
    )


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """Change a user's password."""
    if not _is_strong_password(new_password):
        return False, _password_policy_message()

    username = username.strip().lower()
    users = _load_users_db()
    if username not in users:
        audit_event("password_change_failed", "unknown_user", user_id=username, severity="warning")
        return False, "User not found"
    if not _verify_password(old_password, users[username]["password_hash"]):
        audit_event("password_change_failed", "invalid_current_password", user_id=username, severity="warning")
        return False, "Current password is incorrect"

    users[username]["password_hash"] = _hash_password(new_password)
    _save_users_db(users)
    logger.info("Password changed for user: %s", username)
    audit_event("password_changed", "success", user_id=username)
    return True, "Password changed successfully"


def update_account_email(username: str, email: str) -> tuple[bool, str]:
    """Update the account email and require verification for the new address."""
    if not username:
        return False, "Username is required"
    if not _is_valid_email(email):
        return False, "Email is required for password recovery and account contact"

    username = username.strip().lower()
    email = email.strip().lower()
    users = _load_users_db()
    if username not in users:
        audit_event("account_email_change_failed", "unknown_user", user_id=username, severity="warning")
        return False, "User not found"

    for existing_username, existing in users.items():
        if existing_username != username and existing.get("email", "").strip().lower() == email:
            audit_event("account_email_change_failed", "duplicate_email", user_id=username, severity="warning")
            return False, "Email is already registered"

    user = users[username]
    current_email = user.get("email", "").strip().lower()
    if current_email == email:
        return True, "Email unchanged"

    verification_token = secrets.token_urlsafe(32)
    verification_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    user["email"] = email
    user["email_verified"] = False
    user["verification_token"] = _build_token_record(verification_token, verification_expires)
    _save_users_db(users)

    if st.session_state.get("current_user", {}).get("username") == username:
        st.session_state["current_user"] = _build_public_user_info(user)

    from utils.email_service import is_email_configured, send_verification_email
    if is_email_configured():
        send_verification_email(email, verification_token)

    audit_event("account_email_changed", "success", user_id=username)
    return True, "Email updated; verification required"


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
        audit_event("email_verification_failed", "unknown_user", user_id=username, severity="warning")
        return False, "User not found"

    user = users[username]
    token_matches, expires_str = _token_matches(token, user.get("verification_token", ""))
    if not user.get("verification_token"):
        audit_event("email_verification_failed", "missing_token", user_id=username, severity="warning")
        return False, "No verification token found"
    if not token_matches:
        audit_event("email_verification_failed", "invalid_token", user_id=username, severity="warning")
        return False, "Invalid verification token"

    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str)
            now = datetime.now(timezone.utc)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if now > expires_dt:
                audit_event("email_verification_failed", "expired_token", user_id=username, severity="warning")
                return False, "Token expired"
        except (ValueError, TypeError):
            pass

    users[username]["email_verified"] = True
    users[username]["verification_token"] = ""
    _save_users_db(users)
    if st.session_state.get("current_user", {}).get("username") == username:
        st.session_state["current_user"] = _build_public_user_info(users[username])
    logger.info("Email verified for user: %s", username)
    audit_event("email_verified", "success", user_id=username)
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

    if not _consume_email_verification_request(username):
        audit_event("email_verification_resend", "rate_limited", user_id=username, severity="warning")
        return True, "Verification email sent"

    from utils.email_service import is_email_configured, send_verification_email
    if not is_email_configured():
        return False, "Email service is not configured"

    new_token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    users[username]["verification_token"] = _build_token_record(new_token, expires)
    users[username]["email_verified"] = False
    _save_users_db(users)

    success, msg = send_verification_email(email, new_token)
    if success:
        audit_event("email_verification_resend", "success", user_id=username)
        return True, "Verification email sent"
    audit_event("email_verification_resend", "send_failed", user_id=username, severity="warning")
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
    if not _consume_password_reset_request(identifier):
        audit_event(
            "password_reset_requested",
            "rate_limited",
            severity="warning",
            metadata={"identifier_type": "email" if "@" in identifier else "username"},
        )
        return True, vague_message

    username = None
    if "@" in identifier:
        username = find_user_by_email(identifier)
    else:
        candidate = identifier.lower()
        users = _load_users_db()
        if candidate in users:
            username = candidate

    if username is None:
        audit_event(
            "password_reset_requested",
            "unknown_account",
            metadata={"identifier_type": "email" if "@" in identifier else "username"},
        )
        return True, vague_message

    users = _load_users_db()
    user = users.get(username)
    if not user:
        audit_event("password_reset_requested", "unknown_account", user_id=username)
        return True, vague_message
    user_email = user.get("email", "").strip()
    if not user_email:
        audit_event("password_reset_requested", "missing_email", user_id=username, severity="warning")
        return True, vague_message

    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    users[username]["reset_token"] = _build_token_record(token, expires)
    _save_users_db(users)

    from utils.email_service import is_email_configured, send_password_reset_email
    if is_email_configured():
        send_password_reset_email(user_email, token)

    logger.info("Password reset requested for user: %s", username)
    audit_event("password_reset_requested", "success", user_id=username)
    return True, vague_message


def reset_password(username: str, token: str, new_password: str) -> tuple[bool, str]:
    """Reset a user's password using a reset token."""
    if not _is_strong_password(new_password):
        return False, _password_policy_message()
    if not username or not token:
        return False, "Username and token are required"

    username = username.strip().lower()
    users = _load_users_db()
    if username not in users:
        audit_event("password_reset_failed", "unknown_user", user_id=username, severity="warning")
        return False, "Invalid token"

    user = users[username]
    reset_token_data = user.get("reset_token")
    if not reset_token_data:
        audit_event("password_reset_failed", "missing_token", user_id=username, severity="warning")
        return False, "Invalid token"

    token_matches, expires_str = _token_matches(token, reset_token_data)
    if not token_matches:
        audit_event("password_reset_failed", "invalid_token", user_id=username, severity="warning")
        return False, "Invalid token"

    try:
        expires_dt = datetime.fromisoformat(expires_str)
        now = datetime.now(timezone.utc)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if now > expires_dt:
            audit_event("password_reset_failed", "expired_token", user_id=username, severity="warning")
            return False, "Token expired"
    except (ValueError, TypeError):
        audit_event("password_reset_failed", "invalid_token", user_id=username, severity="warning")
        return False, "Invalid token"

    users[username]["password_hash"] = _hash_password(new_password)
    users[username].pop("reset_token", None)
    _save_users_db(users)
    logger.info("Password reset completed for user: %s", username)
    audit_event("password_reset_completed", "success", user_id=username)
    return True, "Password reset successful"
