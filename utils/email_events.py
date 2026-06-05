"""Normalized email provider event store.

This module stores SendGrid/Mailgun webhook events as an append-only, idempotent
business event log. It complements the existing ``email_tracking`` stats module:
tracking records answer "what happened to this email?", while email events keep
provider webhook evidence for delivery, bounce, spam, and unsubscribe workflows.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from utils.logger import get_logger
from utils.repositories import load_email_events, save_email_events

logger = get_logger("email_events")

MAX_EMAIL_EVENTS = 50_000
TERMINAL_EVENT_TYPES = {"bounce", "dropped", "spamreport", "unsubscribe", "group_unsubscribe"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def build_event_id(event: dict) -> str:
    """Build a stable idempotency key for provider events."""
    explicit = event.get("event_id") or event.get("sg_event_id") or event.get("mailgun_event_id")
    if explicit:
        return str(explicit)
    material = {
        "provider": event.get("provider", ""),
        "tracking_id": event.get("tracking_id", ""),
        "message_id": event.get("message_id", ""),
        "recipient": event.get("recipient", ""),
        "event_type": event.get("event_type", ""),
        "timestamp": event.get("timestamp", ""),
        "reason": event.get("reason", ""),
        "url": event.get("url", ""),
    }
    return hashlib.sha256(_stable_json(material).encode("utf-8")).hexdigest()[:24]


def normalize_event(event: dict) -> dict:
    """Return a normalized, schema-stable event dictionary."""
    normalized = {
        "id": event.get("id", ""),
        "provider": str(event.get("provider", "unknown")).lower(),
        "event_type": str(event.get("event_type", "unknown")).lower(),
        "tracking_id": str(event.get("tracking_id", "")),
        "message_id": str(event.get("message_id", "")),
        "recipient": str(event.get("recipient", "")),
        "subject": str(event.get("subject", "")),
        "customer_id": str(event.get("customer_id", "")),
        "campaign": str(event.get("campaign", "")),
        "timestamp": str(event.get("timestamp", "")) or _now_iso(),
        "reason": str(event.get("reason", "")),
        "url": str(event.get("url", "")),
        "severity": str(event.get("severity", "")),
        "raw": event.get("raw", {}),
        "received_at": event.get("received_at") or _now_iso(),
    }
    normalized["id"] = build_event_id(normalized)
    return normalized


def _update_tracking_from_event(event: dict) -> None:
    """Best-effort sync from provider events into existing email_tracking stats."""
    tracking_id = event.get("tracking_id", "")
    if not tracking_id:
        return

    event_type = event.get("event_type", "")
    try:
        if event_type in {"open", "opened"}:
            from utils.email_tracking import record_open
            record_open(tracking_id)
        elif event_type in {"click", "clicked"}:
            from utils.email_tracking import record_click
            record_click(tracking_id, event.get("url", ""))
        elif event_type in {"bounce", "bounced", "dropped", "spamreport", "unsubscribe", "group_unsubscribe"}:
            from utils.email_tracking import update_tracking_status
            update_tracking_status(tracking_id, event_type, reason=event.get("reason", ""))
    except Exception as exc:
        logger.debug("Email tracking sync failed for event=%s: %s", event.get("id"), exc)


def record_email_event(event: dict, *, sync_tracking: bool = True) -> tuple[bool, dict]:
    """Record one normalized provider event idempotently.

    Returns ``(created, normalized_event)``. Duplicate events are ignored and
    return ``created=False`` with the existing event.
    """
    normalized = normalize_event(event)
    events = load_email_events()
    existing_by_id = {e.get("id"): e for e in events if e.get("id")}
    if normalized["id"] in existing_by_id:
        return False, existing_by_id[normalized["id"]]

    events.append(normalized)
    if len(events) > MAX_EMAIL_EVENTS:
        events = events[-MAX_EMAIL_EVENTS:]
    save_email_events(events)

    if sync_tracking:
        _update_tracking_from_event(normalized)

    logger.info(
        "Email event recorded: provider=%s type=%s recipient=%s tracking=%s",
        normalized.get("provider"),
        normalized.get("event_type"),
        normalized.get("recipient"),
        normalized.get("tracking_id"),
    )
    return True, normalized


def record_email_events(events: list[dict], *, sync_tracking: bool = True) -> dict:
    """Record a batch of provider events."""
    created = 0
    duplicates = 0
    normalized_events = []
    for event in events:
        is_created, normalized = record_email_event(event, sync_tracking=sync_tracking)
        normalized_events.append(normalized)
        if is_created:
            created += 1
        else:
            duplicates += 1
    return {
        "received": len(events),
        "created": created,
        "duplicates": duplicates,
        "events": normalized_events,
    }


def get_events_for_tracking_id(tracking_id: str) -> list[dict]:
    """Return all provider events for a tracking ID."""
    return [event for event in load_email_events() if event.get("tracking_id") == tracking_id]


def get_events_for_recipient(recipient: str, limit: int = 100) -> list[dict]:
    """Return recent provider events for a recipient email address."""
    recipient_lower = recipient.strip().lower()
    matches = [
        event for event in load_email_events()
        if event.get("recipient", "").strip().lower() == recipient_lower
    ]
    matches.sort(key=lambda event: event.get("timestamp", ""), reverse=True)
    return matches[:limit]


def get_email_event_summary(days: int | None = None) -> dict:
    """Return aggregate counts by event type.

    ``days`` is accepted for future filtering; current JSON backend keeps this
    intentionally simple and returns all stored events.
    """
    events = load_email_events()
    counts: dict[str, int] = {}
    for event in events:
        event_type = event.get("event_type", "unknown")
        counts[event_type] = counts.get(event_type, 0) + 1
    return {"total": len(events), "by_type": counts, "period_days": days}
