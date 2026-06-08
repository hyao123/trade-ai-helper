"""Tests for SendGrid/Mailgun email webhook event ingestion."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv


def test_sendgrid_events_are_normalized_and_deduplicated():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.email_events import get_events_for_tracking_id
            from utils.email_webhooks import handle_sendgrid_webhook

            body = json.dumps([
                {
                    "email": "buyer@example.com",
                    "timestamp": 1760000000,
                    "event": "delivered",
                    "sg_event_id": "sg_evt_1",
                    "sg_message_id": "msg_123",
                    "custom_args": {
                        "tracking_id": "track123",
                        "customer_id": "cust1",
                        "campaign": "launch",
                        "subject": "Hello",
                    },
                }
            ])

            first = handle_sendgrid_webhook(body, require_signature=False)
            second = handle_sendgrid_webhook(body, require_signature=False)

            assert first["ok"] is True
            assert first["created"] == 1
            assert second["created"] == 0
            assert second["duplicates"] == 1

            events = get_events_for_tracking_id("track123")
            assert len(events) == 1
            assert events[0]["provider"] == "sendgrid"
            assert events[0]["event_type"] == "delivered"
            assert events[0]["recipient"] == "buyer@example.com"
            assert events[0]["customer_id"] == "cust1"


def test_mailgun_signature_and_event_normalization():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        with patch("utils.storage.get_data_dir", return_value=tmp_dir), \
             patch("utils.email_webhooks.get_secret", return_value="test-signing-key"):
            import hashlib
            import hmac

            from utils.email_events import get_events_for_tracking_id
            from utils.email_webhooks import handle_mailgun_webhook

            timestamp = "1760000000"
            token = "mailgun-token"
            signature = hmac.new(
                b"test-signing-key",
                f"{timestamp}{token}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            body = json.dumps({
                "signature": {"timestamp": timestamp, "token": token, "signature": signature},
                "event-data": {
                    "id": "mg_evt_1",
                    "event": "failed",
                    "timestamp": 1760000001,
                    "recipient": "buyer@example.com",
                    "user-variables": {"tracking_id": "track456", "campaign": "launch"},
                    "delivery-status": {"message": "Mailbox unavailable"},
                    "message": {"headers": {"message-id": "mg_msg_1", "subject": "Quote"}},
                },
            })

            result = handle_mailgun_webhook(body, require_signature=True)
            assert result["ok"] is True
            assert result["created"] == 1
            events = get_events_for_tracking_id("track456")
            assert len(events) == 1
            assert events[0]["provider"] == "mailgun"
            assert events[0]["event_type"] == "bounce"
            assert events[0]["reason"] == "Mailbox unavailable"


def test_mailgun_invalid_signature_is_rejected():
    with patch("utils.email_webhooks.get_secret", return_value="test-signing-key"):
        from utils.email_webhooks import handle_mailgun_webhook
        body = json.dumps({
            "signature": {"timestamp": "1", "token": "abc", "signature": "bad"},
            "event-data": {"event": "delivered"},
        })
        result = handle_mailgun_webhook(body, require_signature=True)
        assert result["ok"] is False
        assert result["error"] == "invalid_mailgun_signature"


def test_provider_event_updates_existing_tracking_status():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.email_events import record_email_event
            from utils.email_tracking import create_tracking_record, get_email_stats

            tracking_id = create_tracking_record(
                user_id="seller",
                to_email="buyer@example.com",
                subject="Quote",
                customer_id="cust1",
                campaign="launch",
            )
            created, event = record_email_event({
                "provider": "sendgrid",
                "event_type": "bounce",
                "tracking_id": tracking_id,
                "recipient": "buyer@example.com",
                "reason": "blocked",
                "timestamp": "2026-01-01T00:00:00+00:00",
            })
            assert created is True
            assert event["event_type"] == "bounce"

            stats = get_email_stats(tracking_id)
            assert stats is not None
            assert stats["status"] == "bounce"
            assert stats["bounced_at"] is not None
            assert stats["provider_events"][-1]["type"] == "bounce"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS: {name}")
