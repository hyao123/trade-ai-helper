"""
utils/user_auth.py
------------------
Multi-user authentication system with registration, login, session management,
and per-user data isolation.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
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
    users[username] = {
        "username": username,
        "email": email.strip(),
        "password_hash": password_hash,
        "tier": "free",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    _save_users_db(users)

    # Create user data directory
    user_dir = get_user_data_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)

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
