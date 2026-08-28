"""
utils/email_tracking.py
-----------------------
Email open/click tracking system.

Provides:
- Unique tracking pixel URL generation (1x1 transparent GIF)
- Link click tracking with redirect
- Per-email delivery stats (sent, opened, clicked, replied)
- Aggregated campaign metrics

Architecture:
- Each sent email gets a unique tracking_id
- Open tracking: embed invisible pixel image URL containing tracking_id
- Click tracking: wrap links with redirect URL containing tracking_id + original URL
- Stats stored in user's tracking_data.json

Usage:
    from utils.email_tracking import (
        create_tracking_record,
        generate_tracking_pixel_html,
        wrap_links_for_tracking,
        record_open,
        record_click,
        get_email_stats,
        get_campaign_stats,
    )
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from utils.logger import get_logger
from utils.repositories import load_email_tracking, save_email_tracking
from utils.secrets import get_secret

logger = get_logger("email_tracking")

_TRACKING_FILE = "email_tracking.json"


# ---------------------------------------------------------------------------
# Tracking record lifecycle
# ---------------------------------------------------------------------------

def create_tracking_record(
    user_id: str,
    to_email: str,
    subject: str,
    customer_id: str = "",
    campaign: str = "",
) -> str:
    """
    Create a tracking record for a sent email.

    Args:
        user_id: The sender's username
        to_email: Recipient email address
        subject: Email subject line
        customer_id: Optional CRM customer ID for linking
        campaign: Optional campaign name for grouping

    Returns:
        tracking_id (str) — unique identifier for this email
    """
    tracking_id = uuid.uuid4().hex[:12]

    record = {
        "tracking_id": tracking_id,
        "user_id": user_id,
        "to_email": to_email,
        "subject": subject,
        "customer_id": customer_id,
        "campaign": campaign,
        "sent_at": datetime.now().isoformat(),
        "delivered_at": None,
        "opened_at": None,
        "open_count": 0,
        "clicked_at": None,
        "click_count": 0,
        "clicked_links": [],
        "replied_at": None,
        "bounced_at": None,
        "spam_reported_at": None,
        "unsubscribed_at": None,
        "provider_events": [],
        "status": "sent",  # sent / delivered / opened / clicked / replied / bounced / spamreport / unsubscribe
    }

    # Save to global tracking store
    records = load_email_tracking()
    records.append(record)
    # Cap at 10000 records to prevent unbounded growth
    if len(records) > 10000:
        records = records[-10000:]
    save_email_tracking(records)

    logger.debug("Tracking record created: %s -> %s", tracking_id, to_email)
    return tracking_id


# ---------------------------------------------------------------------------
# Pixel & link generation
# ---------------------------------------------------------------------------

def generate_tracking_pixel_html(tracking_id: str) -> str:
    """
    Generate an invisible tracking pixel HTML snippet.

    The pixel is a 1x1 transparent image whose URL contains the tracking_id.
    When the email client loads the image, it triggers an "open" event.

    Args:
        tracking_id: The email's tracking identifier

    Returns:
        HTML string with the tracking pixel <img> tag
    """
    base_url = get_secret("APP_BASE_URL") or "https://localhost:8501"
    base_url = base_url.rstrip("/")
    pixel_url = f"{base_url}/api/track/open/{tracking_id}"

    return (
        f'<img src="{pixel_url}" width="1" height="1" '
        f'style="display:none;visibility:hidden;" alt="" />'
    )


def wrap_links_for_tracking(html_body: str, tracking_id: str) -> str:
    """
    Replace all links in HTML body with tracked redirect URLs.

    Original: <a href="https://example.com">text</a>
    Tracked:  <a href="{base_url}/api/track/click/{tracking_id}?url=https://example.com">text</a>

    Args:
        html_body: HTML email body
        tracking_id: The email's tracking identifier

    Returns:
        Modified HTML with tracked links
    """
    base_url = get_secret("APP_BASE_URL") or "https://localhost:8501"
    base_url = base_url.rstrip("/")

    def _replace_href(match):
        original_url = match.group(1)
        # Don't track unsubscribe links or mailto:
        if "unsubscribe" in original_url.lower() or original_url.startswith("mailto:"):
            return match.group(0)
        import urllib.parse
        encoded_url = urllib.parse.quote(original_url, safe="")
        tracked_url = f"{base_url}/api/track/click/{tracking_id}?url={encoded_url}"
        return f'href="{tracked_url}"'

    # Match href="..." in anchor tags
    pattern = r'href="([^"]+)"'
    return re.sub(pattern, _replace_href, html_body)


def generate_tracked_email_html(
    body_text: str,
    tracking_id: str,
    include_pixel: bool = True,
    track_links: bool = True,
) -> str:
    """
    Convert plain text email to HTML with full tracking.

    Combines:
    - Text-to-HTML conversion
    - Link wrapping for click tracking
    - Open tracking pixel insertion

    Args:
        body_text: Plain text email body
        tracking_id: Tracking identifier
        include_pixel: Whether to add open tracking pixel
        track_links: Whether to wrap links

    Returns:
        Complete tracked HTML email body
    """
    import html as html_module

    # Convert plain text to HTML
    escaped = html_module.escape(body_text)
    html_body = escaped.replace("\n", "<br>\n")

    # Detect and linkify URLs in the text
    url_pattern = r'(https?://[^\s<>"]+)'
    html_body = re.sub(
        url_pattern,
        r'<a href="\1" style="color:#3b82f6;">\1</a>',
        html_body,
    )

    # Wrap links for click tracking
    if track_links:
        html_body = wrap_links_for_tracking(html_body, tracking_id)

    # Build full HTML
    full_html = f"""
<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333; max-width: 600px;">
    {html_body}
</div>
"""

    # Add tracking pixel at the end
    if include_pixel:
        pixel = generate_tracking_pixel_html(tracking_id)
        full_html += f"\n{pixel}"

    return full_html


# ---------------------------------------------------------------------------
# Event recording
# ---------------------------------------------------------------------------

def record_open(tracking_id: str) -> bool:
    """
    Record an email open event.

    Called when the tracking pixel is loaded by the email client.
    Also triggers an in-app notification to the sender.

    Returns:
        True if the record was found and updated
    """
    records = load_email_tracking()
    for record in records:
        if record["tracking_id"] == tracking_id:
            record["open_count"] = record.get("open_count", 0) + 1
            if not record.get("opened_at"):
                record["opened_at"] = datetime.now().isoformat()
            if record["status"] in ("sent", "delivered"):
                record["status"] = "opened"
            save_email_tracking(records)
            logger.info("Open recorded: %s (count=%d)", tracking_id, record["open_count"])

            # Trigger notification on first open only
            if record["open_count"] == 1:
                try:
                    from utils.notifications import notify_email_opened
                    notify_email_opened(
                        username=record.get("user_id", ""),
                        customer_email=record.get("to_email", ""),
                        subject=record.get("subject", ""),
                    )
                except Exception as e:
                    logger.debug("Open notification failed (non-critical): %s", e)

            return True
    logger.warning("Open event for unknown tracking_id: %s", tracking_id)
    return False


def record_click(tracking_id: str, url: str = "") -> bool:
    """
    Record a link click event.

    Called when a tracked link redirect is triggered.

    Returns:
        True if the record was found and updated
    """
    records = load_email_tracking()
    for record in records:
        if record["tracking_id"] == tracking_id:
            record["click_count"] = record.get("click_count", 0) + 1
            if not record.get("clicked_at"):
                record["clicked_at"] = datetime.now().isoformat()
            if url:
                clicked_links = record.get("clicked_links", [])
                clicked_links.append({"url": url, "at": datetime.now().isoformat()})
                record["clicked_links"] = clicked_links[-20:]  # Keep last 20
            if record["status"] in ("sent", "delivered", "opened"):
                record["status"] = "clicked"
            save_email_tracking(records)
            logger.info("Click recorded: %s -> %s", tracking_id, url[:50])
            return True
    return False


def record_reply(tracking_id: str) -> bool:
    """
    Record that the recipient replied to this email.

    Typically called manually or via inbox integration.

    Returns:
        True if the record was found and updated
    """
    records = load_email_tracking()
    for record in records:
        if record["tracking_id"] == tracking_id:
            if not record.get("replied_at"):
                record["replied_at"] = datetime.now().isoformat()
            record["status"] = "replied"
            save_email_tracking(records)
            logger.info("Reply recorded: %s", tracking_id)
            return True
    return False


def update_tracking_status(tracking_id: str, status: str, reason: str = "") -> bool:
    """Update a tracking record from provider webhook events.

    This is used by SendGrid/Mailgun webhooks to mirror delivery, bounce,
    spam-report, and unsubscribe events into the existing tracking dashboard.
    """
    if not tracking_id:
        return False

    status = status.strip().lower()
    now = datetime.now().isoformat()
    status_field_map = {
        "processed": "processed_at",
        "delivered": "delivered_at",
        "deferred": "deferred_at",
        "bounce": "bounced_at",
        "bounced": "bounced_at",
        "dropped": "dropped_at",
        "spamreport": "spam_reported_at",
        "unsubscribe": "unsubscribed_at",
        "group_unsubscribe": "unsubscribed_at",
    }

    records = load_email_tracking()
    for record in records:
        if record.get("tracking_id") == tracking_id:
            field = status_field_map.get(status)
            if field and not record.get(field):
                record[field] = now

            # Preserve stronger engagement states over delivered/processed.
            if status in {"processed", "delivered", "deferred"}:
                if record.get("status") == "sent":
                    record["status"] = status
            else:
                record["status"] = status

            provider_events = record.get("provider_events", [])
            provider_events.append({"type": status, "reason": reason, "at": now})
            record["provider_events"] = provider_events[-50:]
            save_email_tracking(records)
            logger.info("Tracking status updated: %s -> %s", tracking_id, status)
            return True
    logger.warning("Provider event for unknown tracking_id: %s", tracking_id)
    return False


# ---------------------------------------------------------------------------
# Statistics & reporting
# ---------------------------------------------------------------------------

def get_email_stats(tracking_id: str) -> dict | None:
    """
    Get tracking stats for a single email.

    Returns:
        Record dict or None if not found
    """
    records = load_email_tracking()
    for record in records:
        if record["tracking_id"] == tracking_id:
            return record
    return None


def get_user_email_stats(user_id: str, days: int = 30) -> dict:
    """
    Get aggregated email stats for a user over the last N days.

    Returns:
        Dict with total_sent, total_opened, total_clicked, total_replied,
        open_rate, click_rate, reply_rate
    """
    from datetime import timedelta

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    records = load_email_tracking()

    user_records = [
        r for r in records
        if r.get("user_id") == user_id and r.get("sent_at", "") >= cutoff
    ]

    total = len(user_records)
    if total == 0:
        return {
            "total_sent": 0, "total_opened": 0, "total_clicked": 0,
            "total_replied": 0, "open_rate": 0.0, "click_rate": 0.0,
            "reply_rate": 0.0, "period_days": days,
        }

    opened = sum(1 for r in user_records if r.get("opened_at"))
    clicked = sum(1 for r in user_records if r.get("clicked_at"))
    replied = sum(1 for r in user_records if r.get("replied_at"))

    return {
        "total_sent": total,
        "total_opened": opened,
        "total_clicked": clicked,
        "total_replied": replied,
        "open_rate": round((opened / total) * 100, 1),
        "click_rate": round((clicked / total) * 100, 1),
        "reply_rate": round((replied / total) * 100, 1),
        "period_days": days,
    }


def get_campaign_stats(campaign: str, user_id: str = "") -> dict:
    """
    Get aggregated stats for a named campaign.

    Args:
        campaign: Campaign name to filter by
        user_id: Optional user filter

    Returns:
        Aggregated stats dict
    """
    records = load_email_tracking()
    filtered = [r for r in records if r.get("campaign") == campaign]
    if user_id:
        filtered = [r for r in filtered if r.get("user_id") == user_id]

    total = len(filtered)
    if total == 0:
        return {"campaign": campaign, "total": 0}

    return {
        "campaign": campaign,
        "total_sent": total,
        "total_opened": sum(1 for r in filtered if r.get("opened_at")),
        "total_clicked": sum(1 for r in filtered if r.get("clicked_at")),
        "total_replied": sum(1 for r in filtered if r.get("replied_at")),
        "open_rate": round(sum(1 for r in filtered if r.get("opened_at")) / total * 100, 1),
        "click_rate": round(sum(1 for r in filtered if r.get("clicked_at")) / total * 100, 1),
    }


def get_recent_activity(user_id: str, limit: int = 20) -> list[dict]:
    """
    Get recent email activity (opens/clicks) for a user.

    Returns list of event dicts sorted by most recent.
    """
    records = load_email_tracking()
    user_records = [r for r in records if r.get("user_id") == user_id]

    # Build activity feed
    activities = []
    for r in user_records:
        if r.get("opened_at"):
            activities.append({
                "type": "open",
                "tracking_id": r["tracking_id"],
                "to_email": r["to_email"],
                "subject": r["subject"],
                "at": r["opened_at"],
            })
        if r.get("clicked_at"):
            activities.append({
                "type": "click",
                "tracking_id": r["tracking_id"],
                "to_email": r["to_email"],
                "subject": r["subject"],
                "at": r["clicked_at"],
            })
        if r.get("replied_at"):
            activities.append({
                "type": "reply",
                "tracking_id": r["tracking_id"],
                "to_email": r["to_email"],
                "subject": r["subject"],
                "at": r["replied_at"],
            })

    # Sort by timestamp descending
    activities.sort(key=lambda x: x.get("at", ""), reverse=True)
    return activities[:limit]
