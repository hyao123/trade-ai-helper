"""
utils/analytics.py
------------------
Lightweight event tracking system for user behavior analytics.
Events are stored locally (JSON) and can be forwarded to external services
(Mixpanel, PostHog, etc.) when configured.

Usage:
    from utils.analytics import track_event
    track_event("email_generated", {"feature": "cold_email", "language": "en"})
"""
from __future__ import annotations

from datetime import datetime

from utils.logger import get_logger
from utils.secrets import get_secret
from utils.storage import load_json, save_json

logger = get_logger("analytics")

_EVENTS_FILE = "analytics_events.json"

# Maximum events to keep in local storage (rolling window)
_MAX_LOCAL_EVENTS = 5000


def track_event(
    event_name: str,
    properties: dict | None = None,
    user_id: str | None = None,
) -> None:
    """
    Track a user behavior event.

    Args:
        event_name: Name of the event (e.g., "email_generated", "waitlist_signup")
        properties: Optional dict of event properties
        user_id: Optional user identifier (defaults to "anonymous")
    """
    try:
        event = {
            "event": event_name,
            "user_id": user_id or _get_user_id(),
            "properties": properties or {},
            "timestamp": datetime.now().isoformat(),
        }

        # Store locally
        _store_local(event)

        # Forward to external service if configured
        _forward_external(event)

        logger.debug("Event tracked: %s (user=%s)", event_name, event["user_id"])
    except Exception as e:
        # Analytics should never crash the app
        logger.warning("Failed to track event %s: %s", event_name, e)


def get_events(
    event_name: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Retrieve tracked events, optionally filtered by event name.

    Args:
        event_name: Optional filter by event name
        limit: Maximum number of events to return (most recent first)

    Returns:
        List of event dicts
    """
    events = load_json(_EVENTS_FILE, default=[])
    if event_name:
        events = [e for e in events if e.get("event") == event_name]
    return events[-limit:]


def get_event_counts(days: int = 7) -> dict[str, int]:
    """
    Get event counts grouped by event name for the last N days.

    Returns:
        Dict of {event_name: count}
    """
    from datetime import timedelta

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    events = load_json(_EVENTS_FILE, default=[])
    counts: dict[str, int] = {}
    for event in events:
        if event.get("timestamp", "") >= cutoff:
            name = event.get("event", "unknown")
            counts[name] = counts.get(name, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_user_id() -> str:
    """Get current user ID from session state if available."""
    try:
        import streamlit as st
        user = st.session_state.get("current_user")
        if user and user.get("username"):
            return user["username"]
    except Exception:
        pass
    return "anonymous"


def _store_local(event: dict) -> None:
    """Append event to local JSON storage with size cap."""
    events = load_json(_EVENTS_FILE, default=[])
    events.append(event)
    # Keep only recent events to prevent unbounded growth
    if len(events) > _MAX_LOCAL_EVENTS:
        events = events[-_MAX_LOCAL_EVENTS:]
    save_json(_EVENTS_FILE, events)


def _forward_external(event: dict) -> None:
    """
    Forward event to external analytics service (if configured).

    Supports:
    - POSTHOG_API_KEY: PostHog cloud
    - MIXPANEL_TOKEN: Mixpanel

    This is non-blocking and failure-safe.
    """
    posthog_key = get_secret("POSTHOG_API_KEY")
    if posthog_key:
        try:
            import urllib.request
            import json

            payload = json.dumps({
                "api_key": posthog_key,
                "event": event["event"],
                "distinct_id": event["user_id"],
                "properties": event["properties"],
                "timestamp": event["timestamp"],
            }).encode()

            host = get_secret("POSTHOG_HOST") or "https://app.posthog.com"
            req = urllib.request.Request(
                f"{host}/capture/",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.debug("PostHog forward failed: %s", e)
