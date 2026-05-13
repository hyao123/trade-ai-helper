"""
utils/email_service.py
----------------------
Email sending service using SMTP (Python stdlib smtplib + email.mime).
All SMTP config is read via get_secret().
Functions return (success: bool, message: str) tuples and handle errors gracefully.
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from utils.secrets import get_secret
from utils.logger import get_logger

logger = get_logger("email_service")


def is_email_configured() -> bool:
    """Return True only if all required SMTP environment variables are set (non-empty)."""
    required_vars = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"]
    return all(get_secret(var) for var in required_vars)


def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send an email via SMTP.

    Returns (success, message) tuple.
    """
    if not is_email_configured():
        return False, "SMTP is not configured"

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

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=30)
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        logger.info("Email sent to %s: %s", to_email, subject)
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
