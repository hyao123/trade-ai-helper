"""Repository helpers built on top of the configured DatabaseBackend.

This module is the narrow data-access seam for account, pricing, payment,
history, preference, email event, and inbound email state. The default backend
remains JSON via ``utils.db.JSONBackend``, but callers no longer reach into
``utils.storage`` directly for core per-user data.
"""

from __future__ import annotations

from typing import Any

from utils.db import get_db

USERS_COLLECTION = "users_db.json"
LOGIN_FAILURES_COLLECTION = "login_failures.json"
USAGE_COLLECTION = "usage.json"
CONSUMED_SESSIONS_COLLECTION = "consumed_sessions.json"
HISTORY_COLLECTION = "history.json"
PREFS_COLLECTION = "prefs.json"
EMAIL_EVENTS_COLLECTION = "email_events.json"
INBOUND_EMAILS_COLLECTION = "inbound_emails.json"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def load_users() -> dict:
    """Return the complete users database from the active backend."""
    return get_db().get_all_users()


def save_users(users: dict) -> None:
    """Persist the complete users database through the active backend."""
    get_db().save_all_users(users)


def load_user(username: str) -> dict | None:
    """Return one user profile from the active backend."""
    return get_db().get_user(username)


def save_user(username: str, user_data: dict) -> None:
    """Upsert one user profile while preserving the current backend contract."""
    users = load_users()
    users[username] = user_data
    save_users(users)


# ---------------------------------------------------------------------------
# Global auth state
# ---------------------------------------------------------------------------
def load_login_failures() -> dict:
    """Return login failure counters keyed by normalized username."""
    data = get_db().load_global_data(LOGIN_FAILURES_COLLECTION, default={})
    return data if isinstance(data, dict) else {}


def save_login_failures(failures: dict) -> None:
    """Persist login failure counters through the active backend."""
    get_db().save_global_data(LOGIN_FAILURES_COLLECTION, failures)


# ---------------------------------------------------------------------------
# Per-user billing/payment state
# ---------------------------------------------------------------------------
def load_user_usage(username: str) -> dict:
    """Return a user's daily usage document."""
    data = get_db().load_user_data(username, USAGE_COLLECTION, default={})
    return data if isinstance(data, dict) else {}


def save_user_usage(username: str, usage: dict) -> None:
    """Persist a user's daily usage document."""
    get_db().save_user_data(username, USAGE_COLLECTION, usage)


def load_consumed_sessions(username: str) -> list[str]:
    """Return consumed Stripe checkout session IDs for a user."""
    data: Any = get_db().load_user_data(username, CONSUMED_SESSIONS_COLLECTION, default=[])
    return data if isinstance(data, list) else []


def save_consumed_sessions(username: str, sessions: list[str]) -> None:
    """Persist consumed Stripe checkout session IDs for a user."""
    get_db().save_user_data(username, CONSUMED_SESSIONS_COLLECTION, sessions)


# ---------------------------------------------------------------------------
# Per-user generation history
# ---------------------------------------------------------------------------
def load_user_history(username: str) -> list[dict]:
    """Return persisted generation history for a user."""
    data: Any = get_db().load_user_data(username, HISTORY_COLLECTION, default=[])
    return data if isinstance(data, list) else []


def save_user_history(username: str, history: list[dict]) -> None:
    """Persist generation history for a user."""
    get_db().save_user_data(username, HISTORY_COLLECTION, history)


def load_shared_history() -> list[dict]:
    """Return shared/admin generation history."""
    data: Any = get_db().load_global_data(HISTORY_COLLECTION, default=[])
    return data if isinstance(data, list) else []


def save_shared_history(history: list[dict]) -> None:
    """Persist shared/admin generation history."""
    get_db().save_global_data(HISTORY_COLLECTION, history)


# ---------------------------------------------------------------------------
# User preferences / onboarding
# ---------------------------------------------------------------------------
def load_user_prefs(username: str) -> dict:
    """Return persisted preferences for a user."""
    data: Any = get_db().load_user_data(username, PREFS_COLLECTION, default={})
    return data if isinstance(data, dict) else {}


def save_user_prefs(username: str, prefs: dict) -> None:
    """Persist preferences for a user."""
    get_db().save_user_data(username, PREFS_COLLECTION, prefs)


def load_shared_prefs() -> dict:
    """Return shared/admin preferences."""
    data: Any = get_db().load_global_data(PREFS_COLLECTION, default={})
    return data if isinstance(data, dict) else {}


def save_shared_prefs(prefs: dict) -> None:
    """Persist shared/admin preferences."""
    get_db().save_global_data(PREFS_COLLECTION, prefs)


# ---------------------------------------------------------------------------
# Provider email events / webhooks
# ---------------------------------------------------------------------------
def load_email_events() -> list[dict]:
    """Return normalized SendGrid/Mailgun email webhook events."""
    data: Any = get_db().load_global_data(EMAIL_EVENTS_COLLECTION, default=[])
    return data if isinstance(data, list) else []


def save_email_events(events: list[dict]) -> None:
    """Persist normalized SendGrid/Mailgun email webhook events."""
    get_db().save_global_data(EMAIL_EVENTS_COLLECTION, events)


# ---------------------------------------------------------------------------
# Inbound email intake
# ---------------------------------------------------------------------------
def load_inbound_emails(username: str) -> list[dict]:
    """Return inbound emails imported by a user."""
    data: Any = get_db().load_user_data(username, INBOUND_EMAILS_COLLECTION, default=[])
    return data if isinstance(data, list) else []


def save_inbound_emails(username: str, emails: list[dict]) -> None:
    """Persist inbound emails imported by a user."""
    get_db().save_user_data(username, INBOUND_EMAILS_COLLECTION, emails)
