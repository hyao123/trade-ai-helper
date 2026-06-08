"""
utils/security_audit.py
-----------------------
Security audit event helpers for account and billing critical paths.

The audit layer intentionally reuses the existing analytics pipeline so it
works with the current JSON storage and any configured external forwarder.
"""
from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from utils.analytics import get_events, track_event
from utils.logger import get_logger

logger = get_logger("security_audit")

AUDIT_EVENT_NAME = "security_audit"
REDACTED = "[REDACTED]"
_MAX_STRING_LENGTH = 200
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "session",
    "signature",
    "token",
)


def audit_event(
    action: str,
    outcome: str,
    *,
    user_id: str | None = None,
    severity: str = "info",
    metadata: Mapping[str, Any] | None = None,
) -> None:
    """Record a failure-safe, sanitized security audit event."""
    safe_action = action or "unknown"
    safe_outcome = outcome or "unknown"
    safe_severity = severity or "info"
    properties = {
        "action": safe_action,
        "outcome": safe_outcome,
        "severity": safe_severity,
        "metadata": sanitize_metadata(metadata or {}),
    }

    try:
        track_event(AUDIT_EVENT_NAME, properties, user_id=user_id)
        logger.info(
            "Security audit event: action=%s outcome=%s severity=%s user=%s",
            safe_action,
            safe_outcome,
            safe_severity,
            user_id or "anonymous",
        )
    except Exception as exc:
        logger.warning("Failed to record security audit event %s: %s", safe_action, exc)


def get_audit_events(
    *,
    user_id: str | None = None,
    action: str | None = None,
    outcome: str | None = None,
    severity: str | None = None,
    days: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return recent security audit events with optional filters."""
    events = get_events(AUDIT_EVENT_NAME, limit=max(limit * 5, limit, 100))
    cutoff = _cutoff_iso(days)
    filtered: list[dict[str, Any]] = []

    for event in reversed(events):
        properties = event.get("properties", {})
        if user_id and event.get("user_id") != user_id:
            continue
        if action and properties.get("action") != action:
            continue
        if outcome and properties.get("outcome") != outcome:
            continue
        if severity and properties.get("severity") != severity:
            continue
        if cutoff and event.get("timestamp", "") < cutoff:
            continue

        filtered.append({
            "timestamp": event.get("timestamp", ""),
            "user_id": event.get("user_id", "anonymous"),
            "action": properties.get("action", "unknown"),
            "outcome": properties.get("outcome", "unknown"),
            "severity": properties.get("severity", "info"),
            "metadata": sanitize_metadata(properties.get("metadata", {})),
        })
        if len(filtered) >= limit:
            break

    return filtered


def summarize_audit_events(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize security audit events for operations dashboards."""
    by_severity: dict[str, int] = {}
    by_action: dict[str, int] = {}
    failures = 0
    warnings = 0

    for event in events:
        severity = str(event.get("severity") or "info")
        action = str(event.get("action") or "unknown")
        outcome = str(event.get("outcome") or "")
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_action[action] = by_action.get(action, 0) + 1
        if severity in {"warning", "critical"}:
            warnings += 1
        if "fail" in action or "failed" in outcome or outcome in {"invalid_password", "invalid_token"}:
            failures += 1

    return {
        "total": len(events),
        "warnings": warnings,
        "failures": failures,
        "by_severity": by_severity,
        "top_actions": sorted(by_action.items(), key=lambda item: item[1], reverse=True)[:10],
    }


def detect_audit_risks(
    events: Sequence[Mapping[str, Any]],
    *,
    login_failure_threshold: int = 5,
    token_failure_threshold: int = 3,
    reset_probe_threshold: int = 10,
) -> list[dict[str, Any]]:
    """Return actionable risk signals detected from security audit events."""
    login_failures: dict[str, int] = {}
    token_failures: dict[str, int] = {}
    reset_probes = 0
    stripe_failures = 0

    for event in events:
        action = str(event.get("action") or "")
        outcome = str(event.get("outcome") or "")
        user_id = str(event.get("user_id") or "anonymous")

        if action in {"login_failed", "login_locked"}:
            login_failures[user_id] = login_failures.get(user_id, 0) + 1

        if action in {"password_reset_failed", "email_verification_failed"}:
            token_failures[user_id] = token_failures.get(user_id, 0) + 1

        if action == "password_reset_requested" and outcome == "unknown_account":
            reset_probes += 1

        if action.startswith("stripe_webhook_") or (
            action == "stripe_checkout_completed"
            and outcome in {"missing_metadata", "upgrade_failed"}
        ):
            stripe_failures += 1

    risks: list[dict[str, Any]] = []
    for user_id, count in sorted(login_failures.items(), key=lambda item: item[1], reverse=True):
        if count >= login_failure_threshold:
            risks.append({
                "id": "login_failure_burst",
                "severity": "high",
                "title": "登录失败集中出现",
                "detail": f"{user_id} 在当前窗口内出现 {count} 次登录失败或锁定事件。",
                "recommendation": "检查是否为撞库/爆破攻击；必要时冻结账号、强制重置密码并核查来源 IP。",
                "count": count,
                "user_id": user_id,
            })

    for user_id, count in sorted(token_failures.items(), key=lambda item: item[1], reverse=True):
        if count >= token_failure_threshold:
            risks.append({
                "id": "token_failure_burst",
                "severity": "medium",
                "title": "邮箱或密码 token 校验异常",
                "detail": f"{user_id} 在当前窗口内出现 {count} 次 token 校验失败。",
                "recommendation": "确认用户是否反复使用过期链接；若非本人操作，应撤销旧 token 并提醒用户改密。",
                "count": count,
                "user_id": user_id,
            })

    if reset_probes >= reset_probe_threshold:
        risks.append({
            "id": "password_reset_probe",
            "severity": "medium",
            "title": "密码重置探测异常",
            "detail": f"当前窗口内出现 {reset_probes} 次未知账号的密码重置请求。",
            "recommendation": "检查是否有账号枚举行为；可考虑增加 CAPTCHA、IP 限速或邮件重置冷却时间。",
            "count": reset_probes,
            "user_id": "anonymous",
        })

    if stripe_failures:
        risks.append({
            "id": "stripe_webhook_failure",
            "severity": "high",
            "title": "Stripe 回调异常",
            "detail": f"当前窗口内出现 {stripe_failures} 次 Stripe webhook 或 checkout 异常。",
            "recommendation": "核查 STRIPE_WEBHOOK_SECRET、事件重放、checkout metadata 和支付升级链路。",
            "count": stripe_failures,
            "user_id": "system",
        })

    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(risks, key=lambda risk: (severity_order.get(str(risk["severity"]), 99), -int(risk["count"])))


def export_audit_events_csv(events: Sequence[Mapping[str, Any]]) -> bytes:
    """Return sanitized audit events as UTF-8-SIG CSV bytes for admin export."""
    output = io.StringIO()
    fieldnames = ["timestamp", "user_id", "action", "outcome", "severity", "metadata"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for event in events:
        metadata = sanitize_metadata(event.get("metadata", {}))
        writer.writerow({
            "timestamp": event.get("timestamp", ""),
            "user_id": event.get("user_id", ""),
            "action": event.get("action", ""),
            "outcome": event.get("outcome", ""),
            "severity": event.get("severity", ""),
            "metadata": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
        })

    return output.getvalue().encode("utf-8-sig")


def sanitize_metadata(value: Any) -> Any:
    """Return a JSON-friendly copy with secrets, tokens, and credentials removed."""
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if _is_sensitive_key(key_str):
                safe[key_str] = REDACTED
            else:
                safe[key_str] = sanitize_metadata(item)
        return safe

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize_metadata(item) for item in value]

    if isinstance(value, (bytes, bytearray)):
        return REDACTED

    if isinstance(value, str) and len(value) > _MAX_STRING_LENGTH:
        return f"{value[:_MAX_STRING_LENGTH]}..."

    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _cutoff_iso(days: int | None) -> str | None:
    if days is None or days <= 0:
        return None
    return (datetime.now() - timedelta(days=days)).isoformat()
