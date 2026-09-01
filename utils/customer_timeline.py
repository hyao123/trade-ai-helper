"""Unified customer timeline — every significant customer interaction as one event.

Captures email_received, email_classified, email_replied, email_sent,
lead_captured, workflow_created, etc. so pages/28 (customer profile) and
pages/3 (customer analytics) can show a single chronological audit trail
instead of querying multiple disjoint collections.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("customer_timeline")

_TIMELINE_FILE = "customer_timeline.json"
_MAX_EVENTS = 1000


def _now_iso() -> str:
    return datetime.now().isoformat()


def append_event(
    username: str,
    customer_email: str,
    event_type: str,
    data: dict | None = None,
    source: str = "",
) -> None:
    """Append one event to the user's customer timeline.

    Best-effort: failures log a debug message and never raise so the calling
    path (send/capture/classify) is never broken by a timeline write failure.
    """
    try:
        timeline = load_user_json(username, _TIMELINE_FILE, default=[])
        if not isinstance(timeline, list):
            timeline = []
        event = {
            "event_id": uuid.uuid4().hex[:16],
            "customer_email": (customer_email or "").strip().lower(),
            "event_type": event_type,
            "timestamp": _now_iso(),
            "data": data or {},
            "source": source,
        }
        timeline.append(event)
        if len(timeline) > _MAX_EVENTS:
            timeline = timeline[-_MAX_EVENTS:]
        save_user_json(username, _TIMELINE_FILE, timeline)
    except Exception as exc:  # noqa: BLE001 - timeline writes must never break callers
        logger.debug("Timeline append failed for %s: %s", username, exc)


def get_timeline(
    username: str,
    customer_email: str,
    limit: int = 50,
) -> list[dict]:
    """Return timeline events for one customer, most recent first."""
    try:
        timeline = load_user_json(username, _TIMELINE_FILE, default=[])
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(timeline, list):
        return []
    needle = (customer_email or "").strip().lower()
    filtered = [e for e in timeline if (e.get("customer_email") or "").strip().lower() == needle]
    filtered.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return filtered[:limit]