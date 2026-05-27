"""
utils/email_sendgrid.py
-----------------------
SendGrid email sending integration with open/click tracking.
Falls back to SMTP (email_service.py) if SendGrid is not configured.

Features:
  - Transactional email sending via SendGrid API
  - Open tracking (pixel)
  - Click tracking
  - Unsubscribe management
  - Delivery status callbacks

Configuration:
  SENDGRID_API_KEY: Your SendGrid API key
  SENDGRID_FROM_EMAIL: Verified sender email
  SENDGRID_FROM_NAME: Display name for sender

Usage:
    from utils.email_sendgrid import send_tracked_email, is_sendgrid_configured
    
    if is_sendgrid_configured():
        ok, msg = send_tracked_email(to, subject, body, tracking_id="xyz")
"""
from __future__ import annotations

import uuid

from utils.analytics import track_event
from utils.logger import get_logger
from utils.secrets import get_secret

logger = get_logger("email_sendgrid")


def is_sendgrid_configured() -> bool:
    """Return True if SendGrid API key and sender are configured."""
    return bool(get_secret("SENDGRID_API_KEY")) and bool(get_secret("SENDGRID_FROM_EMAIL"))


def send_tracked_email(
    to_email: str,
    subject: str,
    body: str,
    from_name: str = "",
    tracking_id: str | None = None,
    enable_open_tracking: bool = True,
    enable_click_tracking: bool = True,
    categories: list[str] | None = None,
    reply_to: str = "",
    attachments: list[dict] | None = None,
) -> tuple[bool, str, str]:
    """
    Send an email via SendGrid API with tracking.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body (plain text, will also generate HTML version)
        from_name: Sender display name
        tracking_id: Custom tracking ID (auto-generated if not provided)
        enable_open_tracking: Enable open tracking pixel
        enable_click_tracking: Enable link click tracking
        categories: SendGrid categories for filtering
        reply_to: Reply-to email address
        attachments: optional list of standard attachment dicts
                     (filename / content / content_type) — see
                     utils.email_attachments. Will be base64-encoded
                     into the SendGrid v3 payload.

    Returns:
        (success, message, tracking_id) tuple
    """
    if not is_sendgrid_configured():
        # Fall back to SMTP (with attachments preserved)
        from utils.email_service import send_ai_generated_email
        ok, msg = send_ai_generated_email(
            to_email, subject, body, from_name, attachments=attachments,
        )
        return ok, msg, ""

    api_key = get_secret("SENDGRID_API_KEY")
    from_email = get_secret("SENDGRID_FROM_EMAIL")
    default_from_name = get_secret("SENDGRID_FROM_NAME") or "Trade AI Assistant"
    sender_name = from_name or default_from_name

    # Generate tracking ID if not provided
    if not tracking_id:
        tracking_id = str(uuid.uuid4())[:12]

    # Build HTML version from plain text
    html_body = _text_to_html(body)

    # Build SendGrid API payload
    payload = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "custom_args": {"tracking_id": tracking_id},
        }],
        "from": {"email": from_email, "name": sender_name},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": body},
            {"type": "text/html", "value": html_body},
        ],
        "tracking_settings": {
            "open_tracking": {"enable": enable_open_tracking},
            "click_tracking": {"enable": enable_click_tracking},
        },
        "categories": categories or ["trade-ai-generated"],
        "custom_args": {"tracking_id": tracking_id},
    }

    if reply_to:
        payload["reply_to"] = {"email": reply_to}

    # Encode attachments per SendGrid v3 spec:
    # https://docs.sendgrid.com/api-reference/mail-send/mail-send#body
    if attachments:
        import base64
        sg_attachments = []
        for att in attachments:
            content_b64 = base64.b64encode(att["content"]).decode("ascii")
            sg_attachments.append({
                "content": content_b64,
                "filename": att["filename"],
                "type": att.get("content_type", "application/octet-stream"),
                "disposition": "attachment",
            })
        payload["attachments"] = sg_attachments

    # Send via SendGrid API
    try:
        import json
        import urllib.request

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        response = urllib.request.urlopen(req, timeout=30)
        status = response.status

        if status in (200, 201, 202):
            logger.info("SendGrid email sent to %s (tracking=%s)", to_email, tracking_id)
            track_event("email_sent", {
                "to": to_email,
                "tracking_id": tracking_id,
                "provider": "sendgrid",
            })
            return True, f"邮件已发送到 {to_email}", tracking_id
        else:
            body_resp = response.read().decode()
            logger.error("SendGrid returned status %d: %s", status, body_resp)
            return False, f"发送失败 (HTTP {status})", tracking_id

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        logger.error("SendGrid API error: %s %s", e.code, error_body)
        if e.code == 401:
            return False, "SendGrid API Key 无效", tracking_id
        if e.code == 403:
            return False, "发件人邮箱未验证，请在 SendGrid 中验证", tracking_id
        return False, f"SendGrid 错误 ({e.code})", tracking_id
    except Exception as e:
        logger.error("SendGrid send failed: %s", e)
        # Fall back to SMTP (preserve attachments)
        from utils.email_service import send_ai_generated_email
        ok, msg = send_ai_generated_email(
            to_email, subject, body, from_name, attachments=attachments,
        )
        return ok, msg, ""


def get_email_stats(tracking_id: str) -> dict:
    """
    Get delivery/open/click stats for a tracked email.
    
    Note: In production, this would query SendGrid's Event Webhook data
    stored in our database. For now, returns stats from local tracking.
    """
    # TODO: Implement with SendGrid Event Webhook + database
    return {
        "tracking_id": tracking_id,
        "delivered": None,
        "opened": None,
        "clicked": None,
    }


def _text_to_html(text: str) -> str:
    """Convert plain text email to basic HTML format."""
    import html as html_module

    escaped = html_module.escape(text)
    # Convert newlines to <br>
    html_body = escaped.replace("\n", "<br>\n")
    # Wrap in basic template
    return f"""
    <div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333;">
        {html_body}
    </div>
    """


def send_bulk_tracked(
    recipients: list[dict],
    subject_template: str,
    body_template: str,
    from_name: str = "",
) -> tuple[int, int, list[str]]:
    """
    Send bulk emails with individual tracking.

    Args:
        recipients: List of dicts with 'email', 'name', etc.
        subject_template: Subject (can use {name}, {company} placeholders)
        body_template: Body template with placeholders
        from_name: Sender display name

    Returns:
        (sent_count, failed_count, tracking_ids)
    """
    sent = 0
    failed = 0
    tracking_ids = []

    for recipient in recipients:
        email = recipient.get("email", "")
        if not email:
            failed += 1
            continue

        # Simple placeholder replacement
        subject = subject_template
        body = body_template
        for key, value in recipient.items():
            subject = subject.replace(f"{{{key}}}", str(value))
            body = body.replace(f"{{{key}}}", str(value))

        ok, _msg, tid = send_tracked_email(
            to_email=email,
            subject=subject,
            body=body,
            from_name=from_name,
        )
        if ok:
            sent += 1
            tracking_ids.append(tid)
        else:
            failed += 1

    return sent, failed, tracking_ids
