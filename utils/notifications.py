"""
utils/notifications.py
----------------------
Unified notification system for in-app, email digest, and push notifications.

Channels:
  - in_app: Toast/badge notifications within the Streamlit UI
  - email_digest: Periodic summary emails (daily/weekly)
  - push: Web Push notifications via Service Worker (PWA)

Notification types:
  - hot_lead: Customer score crossed threshold
  - followup_due: Follow-up reminder is due
  - email_opened: Tracked email was opened by recipient
  - email_replied: Customer replied to your email
  - payment_success: Subscription payment confirmed
  - team_invite: You've been invited to a team
  - system: Platform updates, maintenance notices

Usage:
    from utils.notifications import (
        notify, get_unread, mark_read, get_notification_preferences,
        set_notification_preferences, send_digest,
    )
"""
from __future__ import annotations

from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("notifications")

_NOTIFICATIONS_FILE = "notifications.json"
_PREFERENCES_FILE = "notification_prefs.json"
_MAX_NOTIFICATIONS = 200  # Per user

# ---------------------------------------------------------------------------
# Notification types & defaults
# ---------------------------------------------------------------------------

NOTIFICATION_TYPES: dict[str, dict] = {
    "hot_lead": {
        "icon": "🔥",
        "title_template": "热门线索: {customer}",
        "title_en": "Hot Lead: {customer}",
        "default_channels": ["in_app", "email_digest"],
        "priority": "high",
    },
    "followup_due": {
        "icon": "📅",
        "title_template": "跟进提醒: {customer}",
        "title_en": "Follow-up Due: {customer}",
        "default_channels": ["in_app", "email_digest", "push"],
        "priority": "high",
    },
    "email_opened": {
        "icon": "👁️",
        "title_template": "{customer} 打开了你的邮件",
        "title_en": "{customer} opened your email",
        "default_channels": ["in_app"],
        "priority": "medium",
    },
    "email_replied": {
        "icon": "💬",
        "title_template": "{customer} 回复了你的邮件",
        "title_en": "{customer} replied to your email",
        "default_channels": ["in_app", "push"],
        "priority": "high",
    },
    "payment_success": {
        "icon": "✅",
        "title_template": "支付成功: {plan} 套餐已激活",
        "title_en": "Payment successful: {plan} plan activated",
        "default_channels": ["in_app", "email_digest"],
        "priority": "medium",
    },
    "team_invite": {
        "icon": "👥",
        "title_template": "{inviter} 邀请你加入团队 {team}",
        "title_en": "{inviter} invited you to team {team}",
        "default_channels": ["in_app", "email_digest", "push"],
        "priority": "high",
    },
    "referral_reward": {
        "icon": "🎁",
        "title_template": "获得 {credits} 积分奖励!",
        "title_en": "Earned {credits} bonus credits!",
        "default_channels": ["in_app"],
        "priority": "low",
    },
    "usage_warning": {
        "icon": "⚠️",
        "title_template": "今日用量已达 {percent}%",
        "title_en": "Today's usage at {percent}%",
        "default_channels": ["in_app"],
        "priority": "medium",
    },
    "system": {
        "icon": "📢",
        "title_template": "{message}",
        "title_en": "{message}",
        "default_channels": ["in_app"],
        "priority": "low",
    },
}

DEFAULT_PREFERENCES = {
    "channels": {
        "in_app": True,
        "email_digest": True,
        "push": False,  # Opt-in
    },
    "digest_frequency": "daily",  # daily / weekly / off
    "quiet_hours": {"enabled": False, "start": "22:00", "end": "08:00"},
    "type_overrides": {},  # Per-type channel overrides
}


# ---------------------------------------------------------------------------
# Core notification API
# ---------------------------------------------------------------------------

def notify(
    username: str,
    notification_type: str,
    message: str = "",
    data: dict | None = None,
    **template_vars,
) -> str:
    """
    Send a notification to a user.

    The notification is stored in-app and optionally queued for
    email digest / push depending on preferences.

    Args:
        username: Recipient username
        notification_type: Type key (from NOTIFICATION_TYPES)
        message: Optional custom message (overrides template)
        data: Optional metadata dict (e.g., customer_id, tracking_id)
        **template_vars: Variables for title template interpolation

    Returns:
        notification_id (str)
    """
    import secrets

    type_info = NOTIFICATION_TYPES.get(notification_type, NOTIFICATION_TYPES["system"])
    prefs = get_notification_preferences(username)

    # Generate title from template
    if message:
        title = message
    else:
        title_template = type_info["title_template"]
        try:
            title = title_template.format(**template_vars)
        except (KeyError, IndexError):
            title = title_template

    notification_id = secrets.token_hex(6)

    notification = {
        "id": notification_id,
        "type": notification_type,
        "icon": type_info["icon"],
        "title": title,
        "message": message,
        "data": data or {},
        "priority": type_info["priority"],
        "read": False,
        "created_at": datetime.now().isoformat(),
        "channels_delivered": [],
    }

    # Determine which channels to deliver to
    channels = _resolve_channels(notification_type, prefs)

    # Check quiet hours
    if prefs.get("quiet_hours", {}).get("enabled") and _is_quiet_hours(prefs):
        # During quiet hours, only deliver in_app (no push/email)
        channels = [c for c in channels if c == "in_app"]

    # Deliver to each channel
    if "in_app" in channels:
        _deliver_in_app(username, notification)
        notification["channels_delivered"].append("in_app")

    if "email_digest" in channels:
        _queue_for_digest(username, notification)
        notification["channels_delivered"].append("email_digest")

    if "push" in channels:
        _deliver_push(username, notification)
        notification["channels_delivered"].append("push")

    logger.debug("Notification sent: %s -> %s (type=%s)", notification_id, username, notification_type)
    return notification_id


def get_unread(username: str, limit: int = 50) -> list[dict]:
    """
    Get unread notifications for a user.

    Args:
        username: User to query
        limit: Maximum notifications to return

    Returns:
        List of unread notification dicts, newest first
    """
    notifications = _load_notifications(username)
    unread = [n for n in notifications if not n.get("read")]
    unread.sort(key=lambda n: n.get("created_at", ""), reverse=True)
    return unread[:limit]


def get_all_notifications(username: str, limit: int = 50) -> list[dict]:
    """Get all notifications (read and unread), newest first."""
    notifications = _load_notifications(username)
    notifications.sort(key=lambda n: n.get("created_at", ""), reverse=True)
    return notifications[:limit]


def get_unread_count(username: str) -> int:
    """Get count of unread notifications."""
    notifications = _load_notifications(username)
    return sum(1 for n in notifications if not n.get("read"))


def mark_read(username: str, notification_id: str) -> bool:
    """Mark a specific notification as read."""
    notifications = _load_notifications(username)
    for n in notifications:
        if n["id"] == notification_id:
            n["read"] = True
            n["read_at"] = datetime.now().isoformat()
            _save_notifications(username, notifications)
            return True
    return False


def mark_all_read(username: str) -> int:
    """Mark all notifications as read. Returns count marked."""
    notifications = _load_notifications(username)
    count = 0
    for n in notifications:
        if not n.get("read"):
            n["read"] = True
            n["read_at"] = datetime.now().isoformat()
            count += 1
    if count > 0:
        _save_notifications(username, notifications)
    return count


def delete_notification(username: str, notification_id: str) -> bool:
    """Delete a notification."""
    notifications = _load_notifications(username)
    original_len = len(notifications)
    notifications = [n for n in notifications if n["id"] != notification_id]
    if len(notifications) < original_len:
        _save_notifications(username, notifications)
        return True
    return False


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

def get_notification_preferences(username: str) -> dict:
    """Get user's notification preferences."""
    prefs = load_user_json(username, _PREFERENCES_FILE, default={})
    # Merge with defaults
    merged = dict(DEFAULT_PREFERENCES)
    merged.update(prefs)
    return merged


def set_notification_preferences(username: str, preferences: dict) -> tuple[bool, str]:
    """
    Update notification preferences.

    Args:
        username: User to update
        preferences: Partial or full preferences dict

    Returns:
        (success, message) tuple
    """
    current = get_notification_preferences(username)
    current.update(preferences)
    save_user_json(username, _PREFERENCES_FILE, current)
    return True, "Preferences updated"


# ---------------------------------------------------------------------------
# Email digest
# ---------------------------------------------------------------------------

def send_digest(username: str, force: bool = False) -> tuple[bool, str]:
    """
    Send a notification digest email to the user.

    Called by scheduler or manually. Collects all queued notifications
    since last digest and sends a summary email.

    Args:
        username: User to send digest to
        force: Send even if no new notifications

    Returns:
        (success, message) tuple
    """
    prefs = get_notification_preferences(username)
    if prefs.get("digest_frequency") == "off" and not force:
        return False, "Digest disabled"

    # Load digest queue
    queue = load_user_json(username, "digest_queue.json", default=[])
    if not queue and not force:
        return False, "No pending notifications"

    # Get user's email
    from utils.user_auth import _load_users_db
    users = _load_users_db()
    user = users.get(username, {})
    email = user.get("email", "")
    if not email:
        return False, "No email address configured"

    # Build digest email
    subject = f"📊 TradeAI 通知摘要 ({len(queue)} 条新通知)"
    body_lines = [
        f"您好 {username},\n",
        f"您有 {len(queue)} 条新通知：\n",
    ]

    for item in queue[:20]:  # Max 20 in digest
        icon = item.get("icon", "•")
        title = item.get("title", "")
        time_str = item.get("created_at", "")[:16]
        body_lines.append(f"  {icon} {title} ({time_str})")

    if len(queue) > 20:
        body_lines.append(f"\n  ... 还有 {len(queue) - 20} 条更多通知")

    body_lines.extend([
        "\n",
        "登录查看详情: https://trade-ai-helper.streamlit.app",
        "\n此邮件由外贸AI助手自动发送。",
    ])

    body = "\n".join(body_lines)

    # Send email
    from utils.email_service import is_email_configured, send_email
    if not is_email_configured():
        return False, "Email not configured"

    ok, msg = send_email(email, subject, body)
    if ok:
        # Clear the queue
        save_user_json(username, "digest_queue.json", [])
        logger.info("Digest sent to %s (%d notifications)", username, len(queue))
        return True, f"Digest sent ({len(queue)} notifications)"
    return False, f"Digest send failed: {msg}"


def check_digest_schedule(username: str) -> bool:
    """
    Check if a digest is due and send it if so.

    Returns True if digest was sent.
    """
    prefs = get_notification_preferences(username)
    frequency = prefs.get("digest_frequency", "daily")
    if frequency == "off":
        return False

    last_digest = load_user_json(username, "digest_last_sent.json", default={})
    last_sent = last_digest.get("sent_at", "")

    if last_sent:
        try:
            last_dt = datetime.fromisoformat(last_sent)
            interval = timedelta(days=1) if frequency == "daily" else timedelta(days=7)
            if datetime.now() - last_dt < interval:
                return False
        except (ValueError, TypeError):
            pass

    ok, _msg = send_digest(username)
    if ok:
        save_user_json(username, "digest_last_sent.json", {"sent_at": datetime.now().isoformat()})
    return ok


# ---------------------------------------------------------------------------
# Internal delivery functions
# ---------------------------------------------------------------------------

def _deliver_in_app(username: str, notification: dict) -> None:
    """Store notification for in-app display."""
    notifications = _load_notifications(username)
    notifications.append(notification)
    # Cap size
    if len(notifications) > _MAX_NOTIFICATIONS:
        notifications = notifications[-_MAX_NOTIFICATIONS:]
    _save_notifications(username, notifications)


def _queue_for_digest(username: str, notification: dict) -> None:
    """Add notification to the email digest queue."""
    queue = load_user_json(username, "digest_queue.json", default=[])
    queue.append({
        "icon": notification.get("icon", ""),
        "title": notification.get("title", ""),
        "type": notification.get("type", ""),
        "created_at": notification.get("created_at", ""),
    })
    # Cap queue
    if len(queue) > 100:
        queue = queue[-100:]
    save_user_json(username, "digest_queue.json", queue)


def _deliver_push(username: str, notification: dict) -> None:
    """
    Queue a push notification for delivery via Service Worker.

    In production, this would use Web Push API (VAPID keys + subscription endpoint).
    For now, we store it for the PWA to pick up on next page load.
    """
    push_queue = load_user_json(username, "push_queue.json", default=[])
    push_queue.append({
        "title": f"{notification.get('icon', '')} {notification.get('title', '')}",
        "body": notification.get("message", ""),
        "tag": notification.get("type", "tradeai"),
        "url": "/",
        "created_at": notification.get("created_at", ""),
    })
    # Keep only recent pushes
    if len(push_queue) > 20:
        push_queue = push_queue[-20:]
    save_user_json(username, "push_queue.json", push_queue)


def _load_notifications(username: str) -> list[dict]:
    """Load notifications from storage."""
    return load_user_json(username, _NOTIFICATIONS_FILE, default=[])


def _save_notifications(username: str, notifications: list[dict]) -> None:
    """Save notifications to storage."""
    save_user_json(username, _NOTIFICATIONS_FILE, notifications)


def _resolve_channels(notification_type: str, prefs: dict) -> list[str]:
    """Determine which channels to use for a notification type."""
    type_info = NOTIFICATION_TYPES.get(notification_type, {})
    default_channels = type_info.get("default_channels", ["in_app"])

    # Check user preferences
    channel_prefs = prefs.get("channels", {})
    type_overrides = prefs.get("type_overrides", {}).get(notification_type, {})

    active_channels = []
    for channel in default_channels:
        # Type-specific override takes priority, then global channel pref
        if channel in type_overrides:
            if type_overrides[channel]:
                active_channels.append(channel)
        elif channel_prefs.get(channel, True):
            active_channels.append(channel)

    return active_channels


def _is_quiet_hours(prefs: dict) -> bool:
    """Check if current time is within quiet hours."""
    quiet = prefs.get("quiet_hours", {})
    if not quiet.get("enabled"):
        return False

    now = datetime.now().strftime("%H:%M")
    start = quiet.get("start", "22:00")
    end = quiet.get("end", "08:00")

    # Handle overnight range (e.g., 22:00 - 08:00)
    if start > end:
        return now >= start or now < end
    else:
        return start <= now < end


# ---------------------------------------------------------------------------
# Convenience helpers for common notifications
# ---------------------------------------------------------------------------

def notify_hot_lead(username: str, customer_name: str, score: int, customer_id: str = "") -> str:
    """Send a hot lead notification."""
    return notify(
        username, "hot_lead",
        data={"customer_id": customer_id, "score": score},
        customer=customer_name,
    )


def notify_followup_due(username: str, customer_name: str, product: str = "", days: int = 0) -> str:
    """Send a follow-up due notification."""
    return notify(
        username, "followup_due",
        data={"product": product, "days_elapsed": days},
        customer=customer_name,
    )


def notify_email_opened(username: str, customer_email: str, subject: str = "") -> str:
    """Send an email opened notification."""
    return notify(
        username, "email_opened",
        data={"subject": subject},
        customer=customer_email,
    )


def notify_email_replied(username: str, customer_email: str, subject: str = "") -> str:
    """Send an email replied notification."""
    return notify(
        username, "email_replied",
        data={"subject": subject},
        customer=customer_email,
    )
