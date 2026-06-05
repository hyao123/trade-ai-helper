"""SendGrid/Mailgun webhook parsing and verification helpers.

Streamlit Cloud is not an ideal HTTP webhook receiver. These helpers are pure
business logic so they can be reused from a small FastAPI app, Cloudflare Worker,
Supabase Edge Function, or any future webhook endpoint.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from utils.email_events import record_email_events
from utils.logger import get_logger
from utils.secrets import get_secret

logger = get_logger("email_webhooks")

SENDGRID_EVENT_MAP = {
    "processed": "processed",
    "delivered": "delivered",
    "open": "open",
    "click": "click",
    "bounce": "bounce",
    "dropped": "dropped",
    "deferred": "deferred",
    "spamreport": "spamreport",
    "unsubscribe": "unsubscribe",
    "group_unsubscribe": "group_unsubscribe",
}

MAILGUN_EVENT_MAP = {
    "accepted": "processed",
    "delivered": "delivered",
    "opened": "open",
    "clicked": "click",
    "failed": "bounce",
    "complained": "spamreport",
    "unsubscribed": "unsubscribe",
}


def _timestamp_to_iso(value: Any) -> str:
    """Convert provider timestamp values to ISO string when possible."""
    if value in (None, ""):
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    return str(value)


def _loads_json_body(body: str | bytes) -> Any:
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return json.loads(body or "[]")


def _extract_tracking_id(custom_args: dict) -> str:
    """Extract tracking_id from provider custom args/variables."""
    for key in ("tracking_id", "trackingId", "tid"):
        if custom_args.get(key):
            return str(custom_args[key])
    return ""


def normalize_sendgrid_events(payload: list[dict]) -> list[dict]:
    """Normalize SendGrid Event Webhook payload items."""
    events: list[dict] = []
    for item in payload:
        custom_args = item.get("custom_args") or item.get("unique_args") or {}
        event_type = SENDGRID_EVENT_MAP.get(str(item.get("event", "")).lower(), str(item.get("event", "unknown")).lower())
        events.append({
            "provider": "sendgrid",
            "event_id": item.get("sg_event_id") or item.get("event_id"),
            "sg_event_id": item.get("sg_event_id"),
            "event_type": event_type,
            "tracking_id": _extract_tracking_id(custom_args),
            "message_id": item.get("sg_message_id") or item.get("smtp-id") or "",
            "recipient": item.get("email", ""),
            "subject": custom_args.get("subject", ""),
            "customer_id": custom_args.get("customer_id", ""),
            "campaign": custom_args.get("campaign", ""),
            "timestamp": _timestamp_to_iso(item.get("timestamp")),
            "reason": item.get("reason") or item.get("response") or item.get("status") or "",
            "url": item.get("url", ""),
            "severity": item.get("type", ""),
            "raw": item,
        })
    return events


def normalize_mailgun_events(payload: dict | list[dict]) -> list[dict]:
    """Normalize Mailgun webhook payload.

    Supports both modern single-event payloads with ``event-data`` and batches of
    event-like dictionaries for tests/backfills.
    """
    if isinstance(payload, list):
        raw_events = payload
    else:
        raw_events = [payload.get("event-data", payload)]

    events: list[dict] = []
    for item in raw_events:
        user_vars = item.get("user-variables") or item.get("user_variables") or {}
        message = item.get("message", {}) if isinstance(item.get("message"), dict) else {}
        headers = message.get("headers", {}) if isinstance(message.get("headers"), dict) else {}
        recipient = item.get("recipient") or message.get("recipient") or ""
        event_name = str(item.get("event", "unknown")).lower()
        event_type = MAILGUN_EVENT_MAP.get(event_name, event_name)
        delivery_status = item.get("delivery-status", {}) if isinstance(item.get("delivery-status"), dict) else {}
        events.append({
            "provider": "mailgun",
            "event_id": item.get("id"),
            "mailgun_event_id": item.get("id"),
            "event_type": event_type,
            "tracking_id": _extract_tracking_id(user_vars),
            "message_id": headers.get("message-id") or message.get("headers", {}).get("message-id", ""),
            "recipient": recipient,
            "subject": user_vars.get("subject", "") or headers.get("subject", ""),
            "customer_id": user_vars.get("customer_id", ""),
            "campaign": user_vars.get("campaign", ""),
            "timestamp": _timestamp_to_iso(item.get("timestamp")),
            "reason": delivery_status.get("message") or item.get("reason", ""),
            "url": item.get("url", ""),
            "severity": item.get("severity", ""),
            "raw": item,
        })
    return events


def verify_mailgun_signature(timestamp: str, token: str, signature: str, signing_key: str | None = None) -> bool:
    """Verify Mailgun webhook HMAC-SHA256 signature."""
    key = signing_key or get_secret("MAILGUN_WEBHOOK_SIGNING_KEY") or get_secret("MAILGUN_API_KEY")
    if not key or not timestamp or not token or not signature:
        return False
    digest = hmac.new(key.encode("utf-8"), f"{timestamp}{token}".encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def verify_sendgrid_signature(body: str | bytes, signature: str, timestamp: str, public_key: str | None = None) -> bool:
    """Verify SendGrid webhook signature when cryptography is installed.

    SendGrid uses ECDSA verification over ``timestamp + body``. The core app does
    not currently depend on ``cryptography``; if absent, this returns False
    rather than silently accepting unsigned requests.
    """
    key = public_key or get_secret("SENDGRID_WEBHOOK_PUBLIC_KEY")
    if not key or not signature or not timestamp:
        return False
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except Exception:
        logger.warning("cryptography is not installed; cannot verify SendGrid webhook signature")
        return False

    if isinstance(body, str):
        body_bytes = body.encode("utf-8")
    else:
        body_bytes = body
    signed_payload = timestamp.encode("utf-8") + body_bytes
    signature_bytes = base64.b64decode(signature)

    try:
        public_key_obj = serialization.load_pem_public_key(key.encode("utf-8"))
        if not isinstance(public_key_obj, ec.EllipticCurvePublicKey):
            return False
        public_key_obj.verify(signature_bytes, signed_payload, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def handle_sendgrid_webhook(body: str | bytes, headers: dict | None = None, *, require_signature: bool = True) -> dict:
    """Parse, optionally verify, normalize, and store SendGrid events."""
    headers = headers or {}
    if require_signature:
        signature = headers.get("X-Twilio-Email-Event-Webhook-Signature", "") or headers.get("x-twilio-email-event-webhook-signature", "")
        timestamp = headers.get("X-Twilio-Email-Event-Webhook-Timestamp", "") or headers.get("x-twilio-email-event-webhook-timestamp", "")
        if not verify_sendgrid_signature(body, signature, timestamp):
            return {"ok": False, "error": "invalid_sendgrid_signature", "received": 0, "created": 0}

    payload = _loads_json_body(body)
    if not isinstance(payload, list):
        raise ValueError("SendGrid webhook payload must be a JSON array")
    events = normalize_sendgrid_events(payload)
    result = record_email_events(events)
    return {"ok": True, "provider": "sendgrid", **result}


def handle_mailgun_webhook(body: str | bytes, *, require_signature: bool = True) -> dict:
    """Parse, optionally verify, normalize, and store Mailgun events."""
    payload = _loads_json_body(body)
    if require_signature:
        signature_data = payload.get("signature", {}) if isinstance(payload, dict) else {}
        if not verify_mailgun_signature(
            str(signature_data.get("timestamp", "")),
            str(signature_data.get("token", "")),
            str(signature_data.get("signature", "")),
        ):
            return {"ok": False, "error": "invalid_mailgun_signature", "received": 0, "created": 0}

    events = normalize_mailgun_events(payload)
    result = record_email_events(events)
    return {"ok": True, "provider": "mailgun", **result}
