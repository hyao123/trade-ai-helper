"""Repository helpers backed by the configured DatabaseBackend.

These helpers keep business modules away from direct JSON file access while
preserving the current JSONBackend data layout by default.
"""
from __future__ import annotations

from typing import Any

from utils.db import get_db

_USERS_COLLECTION = "users_db.json"
_LOGIN_FAILURES_COLLECTION = "login_failures.json"
_USAGE_COLLECTION = "usage.json"
_CONSUMED_SESSIONS_COLLECTION = "consumed_sessions.json"


# ---------------------------------------------------------------------------
# User account repository
# ---------------------------------------------------------------------------
def load_users() -> dict:
    """Return the complete users database."""
    return get_db().get_all_users()


def save_users(users: dict) -> None:
    """Persist the complete users database."""
    get_db().save_all_users(users)


def get_user(username: str) -> dict | None:
    """Return one user profile by username."""
    return get_db().get_user(username)


# ---------------------------------------------------------------------------
# Global app data repository
# ---------------------------------------------------------------------------
def load_login_failures() -> dict:
    """Return global failed-login counters."""
    data = get_db().load_global_data(_LOGIN_FAILURES_COLLECTION, default={})
    return data if isinstance(data, dict) else {}


def save_login_failures(failures: dict) -> None:
    """Persist global failed-login counters."""
    get_db().save_global_data(_LOGIN_FAILURES_COLLECTION, failures)


# ---------------------------------------------------------------------------
# Per-user billing and payment repository
# ---------------------------------------------------------------------------
def load_usage(username: str) -> dict:
    """Return the user's daily AI usage record."""
    data = get_db().load_user_data(username, _USAGE_COLLECTION, default={})
    return data if isinstance(data, dict) else {}


def save_usage(username: str, usage: dict) -> None:
    """Persist the user's daily AI usage record."""
    get_db().save_user_data(username, _USAGE_COLLECTION, usage)


def load_consumed_sessions(username: str) -> list[str]:
    """Return consumed Stripe Checkout session IDs for a user."""
    data = get_db().load_user_data(username, _CONSUMED_SESSIONS_COLLECTION, default=[])
    return data if isinstance(data, list) else []


def save_consumed_sessions(username: str, sessions: list[str]) -> None:
    """Persist consumed Stripe Checkout session IDs for a user."""
    get_db().save_user_data(username, _CONSUMED_SESSIONS_COLLECTION, sessions)


# ---------------------------------------------------------------------------
# Generic escape hatch for incremental migrations
# ---------------------------------------------------------------------------
def load_user_collection(username: str, collection: str, default: Any = None) -> Any:
    """Load a per-user collection through the active backend."""
    return get_db().load_user_data(username, collection, default=default)


def save_user_collection(username: str, collection: str, data: Any) -> None:
    """Save a per-user collection through the active backend."""
    get_db().save_user_data(username, collection, data)
