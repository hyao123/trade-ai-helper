"""
utils/email_service.py
----------------------
Email sending service using SMTP (Python stdlib smtplib + email.mime).
All SMTP config is read via get_secret().
Functions return (success: bool, message: str) tuples and handle errors gracefully.

Supports plain-text bodies and arbitrary file attachments (PDF reports,
quotes, invoices, etc.). Attachments use the standard dict format from
utils.email_attachments.
"""
from __future__ import annotations

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.logger import get_logger
from utils.secrets import get_secret

logger = get_logger("email_service")
SMTP_TIMEOUT_SECONDS = 30


def is_email_configured() -> bool:
    """Return True only if all required SMTP environment variables are set (non-empty)."""
    required_vars = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"]
    return all(get_secret(var) for var in required_vars)


def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send a plain-text email via SMTP (no attachments).

    Returns (success, message) tuple.
    """
    return send_email_with_attachments(to_email, subject, body, attachments=None)


def send_email_with_attachments(
    to_email: str,
    subject: str,
    body: str,
    attachments: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Send an email with optional file attachments via SMTP.

    Args:
        to_email: recipient email address
        subject: email subject line
        body: plain-text body
        attachments: list of standard attachment dicts (see utils.email_attachments).
                     Each dict must have 'filename', 'content' (bytes),
                     and 'content_type' keys.

    Returns:
        (success, message) tuple.
    """
    if not is_email_configured():
        return False, "SMTP is not configured"

    # Validate attachments before opening any connection
    if attachments:
        from utils.email_attachments import validate_attachments
        ok, err = validate_attachments(attachments)
        if not ok:
            return False, err

    smtp_host = get_secret("SMTP_HOST")
    smtp_port = get_secret("SMTP_PORT")
    smtp_user = get_secret("SMTP_USER")
    smtp_password = get_secret("SMTP_PASSWORD")
    from_email = get_secret("SMTP_FROM_EMAIL")

    try:
        port = int(smtp_port)
    except (ValueError, TypeError):
        return False, f"Invalid SMTP_PORT value: {smtp_port}"

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach files (if any)
    if attachments:
        for att in attachments:
            filename = att["filename"]
            content = att["content"]
            ctype = att.get("content_type", "application/octet-stream")
            maintype, _, subtype = ctype.partition("/")
            subtype = subtype or "octet-stream"

            part = MIMEApplication(content, _subtype=subtype)
            # RFC 2231-encoded filename to support unicode (CJK) safely
            try:
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=("utf-8", "", filename),
                )
            except Exception:
                # Fallback for older Python: ASCII-only header
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                )
            msg.attach(part)

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=SMTP_TIMEOUT_SECONDS)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=SMTP_TIMEOUT_SECONDS)
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        n_att = len(attachments) if attachments else 0
        logger.info("Email sent to %s: %s (attachments=%d)", to_email, subject, n_att)
        return True, "Email sent successfully"
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", smtp_user)
        return False, "SMTP authentication failed"
    except smtplib.SMTPConnectError as e:
        logger.error("SMTP connection error: %s", e)
        return False, f"SMTP connection failed: {e}"
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
        return False, f"SMTP error: {e}"
    except OSError as e:
        logger.error("Network error sending email: %s", e)
        return False, f"Network error: {e}"


def send_verification_email(to_email: str, token: str) -> tuple[bool, str]:
    """
    Send an email verification message containing the token.

    Returns (success, message) tuple.
    """
    subject = "Email Verification - Trade AI Assistant"
    body = (
        "Thank you for registering with Trade AI Assistant!\n\n"
        "Your email verification token is:\n\n"
        f"    {token}\n\n"
        "Please enter this token on the Account Management page to verify your email.\n\n"
        "If you did not register for this service, please ignore this email."
    )
    return send_email(to_email, subject, body)


def send_password_reset_email(to_email: str, token: str) -> tuple[bool, str]:
    """
    Send a password reset email containing the token.

    Returns (success, message) tuple.
    """
    subject = "Password Reset - Trade AI Assistant"
    body = (
        "You have requested a password reset for your Trade AI Assistant account.\n\n"
        "Your password reset token is:\n\n"
        f"    {token}\n\n"
        "Please enter this token to reset your password.\n\n"
        "If you did not request this, please ignore this email."
    )
    return send_email(to_email, subject, body)



def send_followup_reminder(
    to_email: str,
    customer_name: str,
    company: str,
    product: str,
    days_elapsed: int,
    rule_hint: str,
) -> tuple[bool, str]:
    """
    Send an automated follow-up reminder email to the salesperson.

    Called by the follow-up calendar when a reminder is due.
    """
    subject = f"🔔 跟进提醒: {customer_name} ({company}) — {product}"
    body = (
        f"您好，\n\n"
        f"这是您的跟进提醒：\n\n"
        f"  客户: {customer_name}（{company}）\n"
        f"  产品: {product}\n"
        f"  已发送: {days_elapsed} 天\n\n"
        f"建议行动: {rule_hint}\n\n"
        f"请登录外贸AI助手生成跟进邮件：\n"
        f"https://trade-ai-helper.streamlit.app\n\n"
        f"此邮件由外贸AI助手自动发送，请勿直接回复。"
    )
    return send_email(to_email, subject, body)


def send_ai_generated_email(
    to_email: str,
    subject: str,
    body: str,
    from_name: str = "",
    customer_id: str = "",
    campaign: str = "",
    attachments: list | None = None,
) -> tuple[bool, str]:
    """
    Send an AI-generated email directly to a customer.

    Automatically creates an email tracking record and uses SendGrid
    (with open/click tracking) when configured, falling back to SMTP.

    Args:
        to_email: recipient email address
        subject: email subject line
        body: email body (plain text)
        from_name: optional display name for sender
        customer_id: optional CRM customer ID for linking tracking
        campaign: optional campaign name for grouping stats
        attachments: optional list of attachment inputs. Accepts:
                     - standard dicts: {"filename","content","content_type"}
                     - tuples: (filename, bytes) or (filename, bytes, content_type)
                     - file paths (str / Path)
                     See utils.email_attachments for full spec.

    Returns:
        (success, message) tuple
    """
    # ── Normalize and validate attachments up-front ──
    norm_attachments: list[dict] = []
    if attachments:
        from utils.email_attachments import (
            normalize_attachments,
            validate_attachments,
        )
        norm_attachments = normalize_attachments(attachments)
        ok, err = validate_attachments(norm_attachments)
        if not ok:
            return False, err

    # ── Create tracking record ──
    tracking_id = ""
    try:
        from utils.email_tracking import create_tracking_record
        from utils.user_auth import get_current_user
        user = get_current_user()
        user_id = user.get("username", "anonymous") if user else "anonymous"
        tracking_id = create_tracking_record(
            user_id=user_id,
            to_email=to_email,
            subject=subject,
            customer_id=customer_id,
            campaign=campaign,
        )
    except Exception as e:
        logger.debug("Email tracking record creation failed (non-critical): %s", e)

    # ── Try SendGrid first (has built-in open/click tracking) ──
    try:
        from utils.email_sendgrid import is_sendgrid_configured, send_tracked_email
        if is_sendgrid_configured():
            ok, msg, _tid = send_tracked_email(
                to_email=to_email,
                subject=subject,
                body=body,
                from_name=from_name,
                tracking_id=tracking_id,
                attachments=norm_attachments or None,
            )
            return ok, msg
    except ImportError:
        pass
    except Exception as e:
        logger.warning("SendGrid send failed, falling back to SMTP: %s", e)

    # ── Fallback: SMTP send ──
    if not is_email_configured():
        return False, "SMTP 未配置，请在设置中填写 SMTP 参数"

    success, msg = send_email_with_attachments(
        to_email, subject, body, attachments=norm_attachments or None,
    )

    if success:
        return True, f"邮件已发送到 {to_email}"
    # Translate common errors to Chinese
    error_map = {
        "SMTP authentication failed": "SMTP 认证失败，请检查用户名和密码",
        "SMTP connection failed": "SMTP 连接失败",
    }
    for en_prefix, zh_msg in error_map.items():
        if msg.startswith(en_prefix):
            return False, zh_msg
    return False, msg
