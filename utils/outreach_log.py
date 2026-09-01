"""Unified outgoing outreach log across inbox, inbound, and campaign sends.

Every outbound customer email (AI inbox direct reply, inbound-queue reply,
campaign send) appends one event here so there is a single per-user
audit trail of what was sent to whom, when, and via which source.
"""
from __future__ import annotations

from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("outreach_log")

OUTREACH_LOG_FILE = "outreach_log.json"
_MAX_LOG_ENTRIES = 500


def _now_iso() -> str:
    return datetime.now().isoformat()


def append_outreach_log(username: str, event: dict) -> None:
    """Append one outbound-email event to the user's unified log.

    ``event`` is a dict (e.g. direction/source/to_email/subject/tracking_id/
    status/timestamp). Best-effort: a storage failure logs a debug message
    and never raises, so callers (email send paths) are never broken by it.
    """
    try:
        logs = load_user_json(username, OUTREACH_LOG_FILE, default=[])
        if not isinstance(logs, list):
            logs = []
        merged = {**event}
        merged.setdefault("timestamp", _now_iso())
        logs.append(merged)
        if len(logs) > _MAX_LOG_ENTRIES:
            logs = logs[-_MAX_LOG_ENTRIES:]
        save_user_json(username, OUTREACH_LOG_FILE, logs)
    except Exception as exc:  # noqa: BLE001 - logging must never break sending
        logger.debug("outreach log write failed for %s: %s", username, exc)


def get_outreach_logs(username: str, limit: int = 50) -> list[dict]:
    """Return the user's most recent outreach log entries."""
    try:
        logs = load_user_json(username, OUTREACH_LOG_FILE, default=[])
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(logs, list):
        return []
    logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]