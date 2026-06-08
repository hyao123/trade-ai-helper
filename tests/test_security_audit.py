"""Tests for security audit event sanitization and tracking."""
from __future__ import annotations

import csv
import io
from unittest.mock import patch


def test_sanitize_metadata_redacts_sensitive_nested_fields():
    from utils.security_audit import REDACTED, sanitize_metadata

    safe = sanitize_metadata({
        "target_tier": "pro",
        "password": "secret-password",
        "nested": {
            "apiKey": "sk_test_123",
            "items": [{"reset_token": "token-value"}, {"status": "ok"}],
        },
        "session_id": "cs_test_123",
    })

    assert safe["target_tier"] == "pro"
    assert safe["password"] == REDACTED
    assert safe["nested"]["apiKey"] == REDACTED
    assert safe["nested"]["items"][0]["reset_token"] == REDACTED
    assert safe["nested"]["items"][1]["status"] == "ok"
    assert safe["session_id"] == REDACTED


def test_audit_event_tracks_sanitized_security_event():
    from utils.security_audit import AUDIT_EVENT_NAME, REDACTED, audit_event

    with patch("utils.security_audit.track_event") as track:
        audit_event(
            "password_reset_completed",
            "success",
            user_id="audituser",
            metadata={"token": "raw-token", "source": "test"},
        )

    track.assert_called_once_with(
        AUDIT_EVENT_NAME,
        {
            "action": "password_reset_completed",
            "outcome": "success",
            "severity": "info",
            "metadata": {"token": REDACTED, "source": "test"},
        },
        user_id="audituser",
    )


def test_get_audit_events_filters_and_returns_sanitized_recent_rows():
    from utils.security_audit import REDACTED, get_audit_events

    raw_events = [
        {
            "event": "security_audit",
            "user_id": "alice",
            "timestamp": "2026-06-08T10:00:00",
            "properties": {
                "action": "login_failed",
                "outcome": "invalid_password",
                "severity": "warning",
                "metadata": {"password": "raw-password"},
            },
        },
        {
            "event": "security_audit",
            "user_id": "bob",
            "timestamp": "2026-06-08T11:00:00",
            "properties": {
                "action": "login_succeeded",
                "outcome": "success",
                "severity": "info",
                "metadata": {"source": "web"},
            },
        },
    ]

    with patch("utils.security_audit.get_events", return_value=raw_events):
        events = get_audit_events(user_id="alice", severity="warning", limit=10)

    assert len(events) == 1
    assert events[0]["user_id"] == "alice"
    assert events[0]["action"] == "login_failed"
    assert events[0]["metadata"]["password"] == REDACTED


def test_summarize_audit_events_counts_risk_and_top_actions():
    from utils.security_audit import summarize_audit_events

    summary = summarize_audit_events([
        {"action": "login_failed", "outcome": "invalid_password", "severity": "warning"},
        {"action": "login_failed", "outcome": "invalid_password", "severity": "warning"},
        {"action": "login_succeeded", "outcome": "success", "severity": "info"},
    ])

    assert summary["total"] == 3
    assert summary["warnings"] == 2
    assert summary["failures"] == 2
    assert summary["by_severity"] == {"warning": 2, "info": 1}
    assert summary["top_actions"][0] == ("login_failed", 2)


def test_detect_audit_risks_flags_login_token_and_stripe_anomalies():
    from utils.security_audit import detect_audit_risks

    events = [
        {"user_id": "alice", "action": "login_failed", "outcome": "invalid_password", "severity": "warning"},
        {"user_id": "alice", "action": "login_failed", "outcome": "invalid_password", "severity": "warning"},
        {"user_id": "alice", "action": "login_failed", "outcome": "invalid_password", "severity": "warning"},
        {"user_id": "bob", "action": "password_reset_failed", "outcome": "invalid_token", "severity": "warning"},
        {"user_id": "bob", "action": "email_verification_failed", "outcome": "invalid_token", "severity": "warning"},
        {"user_id": "system", "action": "stripe_webhook_verification_failed", "outcome": "invalid_signature"},
    ]

    risks = detect_audit_risks(events, login_failure_threshold=3, token_failure_threshold=2)
    by_id = {risk["id"]: risk for risk in risks}

    assert by_id["login_failure_burst"]["user_id"] == "alice"
    assert by_id["login_failure_burst"]["severity"] == "high"
    assert by_id["token_failure_burst"]["user_id"] == "bob"
    assert by_id["stripe_webhook_failure"]["severity"] == "high"


def test_detect_audit_risks_flags_password_reset_probe():
    from utils.security_audit import detect_audit_risks

    events = [
        {"action": "password_reset_requested", "outcome": "unknown_account", "severity": "info"}
        for _ in range(4)
    ]

    risks = detect_audit_risks(events, reset_probe_threshold=4)

    assert len(risks) == 1
    assert risks[0]["id"] == "password_reset_probe"
    assert risks[0]["count"] == 4


def test_export_audit_events_csv_is_excel_friendly_and_sanitized():
    from utils.security_audit import REDACTED, export_audit_events_csv

    exported = export_audit_events_csv([
        {
            "timestamp": "2026-06-08T12:00:00",
            "user_id": "audituser",
            "action": "stripe_checkout_completed",
            "outcome": "success",
            "severity": "info",
            "metadata": {"session_id": "cs_test_123", "target_tier": "企业版"},
        }
    ])

    assert exported.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(exported.decode("utf-8-sig"))))
    assert rows == [
        {
            "timestamp": "2026-06-08T12:00:00",
            "user_id": "audituser",
            "action": "stripe_checkout_completed",
            "outcome": "success",
            "severity": "info",
            "metadata": f'{{"session_id": "{REDACTED}", "target_tier": "企业版"}}',
        }
    ]
