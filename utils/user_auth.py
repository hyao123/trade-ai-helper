"""
utils/user_auth.py
------------------
Multi-user authentication system with registration, login, session management,
and per-user data isolation.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

from utils.storage import get_data_dir, load_json, save_json
from utils.logger import get_logger

logger = get_logger("user_auth")

_PBKDF2_ITERATIONS = 100_000
_USERS_DB_FILENAME = "users_db.json"


def _get_users_db_path() -> Path:
    """Return path to the users database JSON file."""
    return get_data_dir() / _USERS_DB_FILENAME


def _get_users_dir() -> Path:
    """Return path to the data/users/ directory. Creates it if needed."""
    users_dir = get_data_dir() / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    return users_dir


def _hash_password(password: str, salt: str | None = None) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a per-user random salt.

    Returns a string in the format 'salt_hex:hash_hex'.
    If salt is not provided, generates a new random 16-byte salt.
    """
    if salt is None:
        salt = os.urandom(16).hex()
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    return f"{salt}:{hash_bytes.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a password against a stored hash string.

    The stored_hash format is 'salt_hex:hash_hex'.
    """
    if ":" not in stored_hash:
        return False
    salt = stored_hash.split(":")[0]
    return _hash_password(password, salt) == stored_hash


def _load_users_db() -> dict:
    """Load users database from disk."""
    return load_json(_USERS_DB_FILENAME, default={})


def _save_users_db(users: dict) -> None:
    """Save users database to disk."""
    save_json(_USERS_DB_FILENAME, users)


def register_user(username: str, password: str, email: str = "") -> tuple[bool, str]:
    """
    Register a new user.

    Returns (success, message) tuple.
    Validates input, checks uniqueness, creates user profile and data directory.
    """
    # Validate input
    if not username or not username.strip():
        return False, "Username cannot be empty"
    username = username.strip().lower()
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if not username.isalnum():
        return False, "Username must contain only letters and numbers"
    if not password or len(password) < 4:
        return False, "Password must be at least 4 characters"

    # Check uniqueness
    users = _load_users_db()
    if username in users:
        return False, "Username already exists"

    # Create user profile with per-user random salt
    password_hash = _hash_password(password)
    verification_token = secrets.token_urlsafe(32)
    users[username] = {
        "username": username,
        "email": email.strip(),
        "password_hash": password_hash,
        "tier": "free",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "email_verified": False,
        "verification_token": {"token": verification_token, "expires": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()},
    }
    _save_users_db(users)

    # Create user data directory
    user_dir = get_user_data_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)

    # Send verification email if email provided and SMTP configured
    if email.strip():
        from utils.email_service import is_email_configured, send_verification_email
        if is_email_configured():
            send_verification_email(email.strip(), verification_token)

    logger.info("User registered: %s", username)
    return True, "Registration successful"


def authenticate_user(username: str, password: str) -> tuple[bool, dict | None]:
    """
    Authenticate a user by username and password.

    Returns (success, user_dict or None).
    """
    if not username or not password:
        return False, None

    username = username.strip().lower()
    users = _load_users_db()

    if username not in users:
        return False, None

    user = users[username]
    if _verify_password(password, user["password_hash"]):
        # Return user info without password hash
        user_info = {
            "username": user["username"],
            "email": user.get("email", ""),
            "tier": user.get("tier", "free"),
            "created_at": user.get("created_at", ""),
            "email_verified": user.get("email_verified", False),
            "language": user.get("language", ""),
        }
        logger.info("User authenticated: %s", username)
        return True, user_info

    return False, None


def get_current_user() -> dict | None:
    """Get the currently logged-in user from session state."""
    return st.session_state.get("current_user", None)


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """
    Change a user's password.

    Returns (success, message) tuple.
    """
    if not new_password or len(new_password) < 4:
        return False, "New password must be at least 4 characters"

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
    """
    Verify an email verification token for a user.

    Returns (success, message) tuple.
    """
    if not username or not token:
        return False, "Username and token are required"

    username = username.strip().lower()
    users = _load_users_db()

    if username not in users:
        return False, "User not found"

    user = users[username]
    stored_token_data = user.get("verification_token", "")

    if not stored_token_data:
        return False, "No verification token found"

    # Support both old format (bare string) and new format (dict with expiry)
    if isinstance(stored_token_data, dict):
        stored_token = stored_token_data.get("token", "")
        expires_str = stored_token_data.get("expires", "")
    else:
        stored_token = stored_token_data
        expires_str = ""

    if not stored_token:
        return False, "No verification token found"

    if token != stored_token:
        return False, "Invalid verification token"

    # Check expiry if present
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
    """
    Generate a new verification token and resend the verification email.

    Returns (success, message) tuple.
    """
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
    users[username]["verification_token"] = {"token": new_token, "expires": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
    users[username]["email_verified"] = False
    _save_users_db(users)

    success, msg = send_verification_email(email, new_token)
    if success:
        return True, "Verification email sent"
    return False, f"Failed to send email: {msg}"


def find_user_by_email(email: str) -> str | None:
    """
    Scan users_db.json for a user with matching email field (case-insensitive).

    Returns username (str) or None if not found.
    """
    if not email:
        return None
    email_lower = email.strip().lower()
    users = _load_users_db()
    for username, user_data in users.items():
        if user_data.get("email", "").strip().lower() == email_lower:
            return username
    return None


def request_password_reset(email_or_username: str) -> tuple[bool, str]:
    """
    Request a password reset for a user identified by email or username.

    If input contains '@', tries find_user_by_email() first.
    Otherwise looks up directly by username (lowercase).
    Returns (success, message) tuple. Always returns True for security
    (does not reveal whether user exists).
    """
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

    # Generate token with 1-hour expiry
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    users[username]["reset_token"] = {"token": token, "expires": expires}
    _save_users_db(users)

    # Send the reset email
    from utils.email_service import is_email_configured, send_password_reset_email

    if is_email_configured():
        send_password_reset_email(user_email, token)

    logger.info("Password reset requested for user: %s", username)
    return True, "Reset email sent"


def reset_password(username: str, token: str, new_password: str) -> tuple[bool, str]:
    """
    Reset a user's password using a reset token.

    Validates the token has not expired (1 hour) and matches stored token.
    Returns (success, message) tuple.
    """
    if not new_password or len(new_password) < 4:
        return False, "Password must be at least 4 characters"

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

    stored_token = reset_token_data.get("token", "")
    expires_str = reset_token_data.get("expires", "")

    if token != stored_token:
        return False, "Invalid token"

    # Check expiry
    try:
        expires_dt = datetime.fromisoformat(expires_str)
        # Ensure timezone-aware comparison
        now = datetime.now(timezone.utc)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if now > expires_dt:
            return False, "Token expired"
    except (ValueError, TypeError):
        return False, "Invalid token"

    # Update password and clear reset token
    users[username]["password_hash"] = _hash_password(new_password)
    users[username].pop("reset_token", None)
    _save_users_db(users)

    logger.info("Password reset completed for user: %s", username)
    return True, "Password reset successful"
