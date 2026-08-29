"""
utils/email_resend.py
---------------------
Resend email sending integration (https://resend.com).

Resend is a modern, developer-friendly transactional email API with a generous
free tier (3,000 emails/month, 100/day). This module mirrors the shape of
utils.email_sendgrid so the two providers are drop-in interchangeable:

  - is_resend_configured() -> bool
  - send_resend_email(...) -> (ok, message, tracking_id)

Like the SendGrid wrapper it stays on Python's standard library (urllib) so no
extra dependency is added to requirements.txt. Attachments are base64-encoded
into the Resend v3 payload per the API spec:
  https://resend.com/docs/api-reference/emails/send-email

Configuration (env / secrets):
  RESEND_API_KEY        : Your Resend API key (re_...)
  RESEND_FROM_EMAIL     : Verified sender email (domain verified in Resend)
  RESEND_FROM_NAME      : Optional display name for the sender
  RESEND_REPLY_TO       : Optional reply-to address

A webhook (events like delivered/opened/clicked/bounced) can be pointed at the
same webhook endpoint already used by SendGrid/Mailgun; see utils.email_webhooks.
"""
from __future__ import annotations

import uuid

from utils.logger import get_logger
from utils.secrets import get_secret

logger = get_logger("email_resend")

RESEND_API_URL = "https://api.resend.com/emails"


def is_resend_configured() -> bool:
    """Return True only if the Resend API key and a verified sender are set."""
    return bool(get_secret("RESEND_API_KEY")) and bool(get_secret("RESEND_FROM_EMAIL"))


def send_resend_email(
    to_email: str,
    subject: str,
    body: str,
    from_name: str = "",
    reply_to: str = "",
    tracking_id: str | None = None,
    html: str = "",
    attachments: list[dict] | None = None,
) -> tuple[bool, str, str]:
    """
    Send an email via the Resend API.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Plain-text email body
        from_name: Optional sender display name
        reply_to: Optional reply-to email address
        tracking_id: Custom tracking id (auto-generated if not provided)
        html: Optional HTML body (if empty, a simple HTML version is derived)
        attachments: Optional list of standard attachment dicts
                     (filename / content / content_type) from
                     utils.email_attachments.

    Returns:
        (success, message, tracking_id) tuple. On a general provider error it
        returns (False, message, tracking_id) and lets the caller fall back.
    """
    from_email = get_secret("RESEND_FROM_EMAIL")
    default_from_name = get_secret("RESEND_FROM_NAME") or "Trade AI Assistant"
    sender_name = from_name or default_from_name

    if not tracking_id:
        tracking_id = str(uuid.uuid4())[:12]

    # Build payload per Resend API spec (v3).
    payload = {
        "from": f"{sender_name} <{from_email}>",
        "to": [to_email],
        "subject": subject,
        "text": body,
        "headers": {"X-TradeAI-Tracking-Id": tracking_id},
    }

    if reply_to:
        payload["reply_to"] = reply_to

    if html:
        payload["html"] = html
    else:
        payload["html"] = _text_to_html(body)

    # Attachments: Resend expects base64-encoded content plus file type.
    if attachments:
        import base64
        resend_attachments = []
        for att in attachments:
            content_b64 = base64.b64encode(att["content"]).decode("ascii")
            resend_attachments.append({
                "filename": att["filename"],
                "content": content_b64,
                "content_type": att.get("content_type", "application/octet-stream"),
            })
        payload["attachments"] = resend_attachments

    api_key = get_secret("RESEND_API_KEY")
    try:
        import json
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            RESEND_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        response = urllib.request.urlopen(req, timeout=30)
        data = json.loads(response.read().decode())

        # Successful responses carry an "id" for the sent email.
        if response.status in (200, 201, 202):
            email_id = data.get("id", "")
            logger.info("Resend email sent to %s (tracking=%s, id=%s)", to_email, tracking_id, email_id)
            try:
                from utils.analytics import track_event
                track_event("email_sent", {
                    "to": to_email,
                    "tracking_id": tracking_id,
                    "provider": "resend",
                })
            except Exception:
                pass
            return True, f"邮件已发送到 {to_email}", tracking_id

        return False, f"发送失败 (HTTP {response.status})", tracking_id

    except urllib.error.HTTPError as e:
        error_body = e.read().decode(errors="replace") if e.fp else str(e)
        logger.error("Resend API error: %s %s", e.code, error_body)
        if e.code == 401:
            return False, "Resend API Key 无效", tracking_id
        if e.code == 403:
            return False, "发件人邮箱未验证，请在 Resend 中验证", tracking_id
        if e.code == 422:
            return False, "Resend 请求被拒绝（参数错误或发件人未验证）", tracking_id
        if e.code == 429:
            return False, "Resend 达到发送频率限制，请稍后再试", tracking_id
        return False, f"Resend 错误 ({e.code})", tracking_id
    except Exception as e:
        logger.error("Resend send failed: %s", e)
        return False, f"Resend 发送失败: {e}", tracking_id


def _text_to_html(text: str) -> str:
    """Convert plain text email body into a minimal HTML version."""
    import html as html_module

    escaped = html_module.escape(text)
    html_body = escaped.replace("\n", "<br>\n")
    return (
        '<div style="font-family: Arial, sans-serif; font-size: 14px; '
        f'line-height: 1.6; color: #333;">{html_body}</div>'
    )
