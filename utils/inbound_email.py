"""Inbound email intake service.

Phase 1 focuses on manual intake: users can paste raw email text or upload an
.eml file. The service parses sender, subject, date, and body, then stores a
pending inbound email record that can be used to seed the inquiry-reply page.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser, Parser
from email.utils import parseaddr
from typing import Any

from utils.repositories import load_inbound_emails, save_inbound_emails

MAX_INBOUND_EMAILS_PER_USER = 1000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_body(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    # Keep quoted history for context, but trim excessive blank lines.
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _extract_text_from_message(msg) -> str:
    """Extract a readable text body from an email.message.Message."""
    if msg.is_multipart():
        html_fallback = ""
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", "")).lower()
            if "attachment" in content_disposition:
                continue
            content_type = part.get_content_type()
            try:
                payload = part.get_content()
            except Exception:
                continue
            if content_type == "text/plain" and isinstance(payload, str) and payload.strip():
                return _clean_body(payload)
            if content_type == "text/html" and isinstance(payload, str) and payload.strip() and not html_fallback:
                html_fallback = payload
        if html_fallback:
            return _html_to_text(html_fallback)
        return ""

    try:
        payload = msg.get_content()
    except Exception:
        payload = msg.get_payload(decode=True) or b""
        if isinstance(payload, bytes):
            payload = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    if msg.get_content_type() == "text/html":
        return _html_to_text(str(payload))
    return _clean_body(str(payload))


def _html_to_text(html: str) -> str:
    """Very small HTML-to-text helper using stdlib only."""
    import html as html_module

    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html or "")
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return _clean_body(text)


def _sender_parts(raw_from: str) -> tuple[str, str]:
    name, email_addr = parseaddr(raw_from or "")
    return name.strip(), email_addr.strip().lower()


def _fingerprint(email_record: dict) -> str:
    material = "|".join([
        email_record.get("message_id", ""),
        email_record.get("from_email", ""),
        email_record.get("subject", ""),
        email_record.get("body", "")[:500],
    ])
    return hashlib.sha256(material.encode("utf-8", errors="ignore")).hexdigest()[:24]


def parse_eml_bytes(data: bytes) -> dict:
    """Parse raw .eml bytes into a normalized inbound email draft."""
    msg = BytesParser(policy=policy.default).parsebytes(data)
    from_name, from_email = _sender_parts(str(msg.get("From", "")))
    record = {
        "source": "eml",
        "message_id": str(msg.get("Message-ID", "")).strip(),
        "from_name": from_name,
        "from_email": from_email,
        "to": str(msg.get("To", "")).strip(),
        "cc": str(msg.get("Cc", "")).strip(),
        "subject": str(msg.get("Subject", "")).strip(),
        "received_at": str(msg.get("Date", "")).strip(),
        "body": _extract_text_from_message(msg),
        "raw_headers": {
            "from": str(msg.get("From", "")),
            "to": str(msg.get("To", "")),
            "date": str(msg.get("Date", "")),
            "message_id": str(msg.get("Message-ID", "")),
        },
    }
    record["fingerprint"] = _fingerprint(record)
    return record


def parse_raw_email_text(raw_text: str) -> dict:
    """Parse pasted raw email text or simple body-only text."""
    raw_text = raw_text or ""
    parsed = Parser(policy=policy.default).parsestr(raw_text)
    has_headers = bool(parsed.get("From") or parsed.get("Subject") or parsed.get("Date"))
    if has_headers:
        from_name, from_email = _sender_parts(str(parsed.get("From", "")))
        body = _extract_text_from_message(parsed)
        record = {
            "source": "raw_text",
            "message_id": str(parsed.get("Message-ID", "")).strip(),
            "from_name": from_name,
            "from_email": from_email,
            "to": str(parsed.get("To", "")).strip(),
            "cc": str(parsed.get("Cc", "")).strip(),
            "subject": str(parsed.get("Subject", "")).strip(),
            "received_at": str(parsed.get("Date", "")).strip(),
            "body": body,
            "raw_headers": {
                "from": str(parsed.get("From", "")),
                "to": str(parsed.get("To", "")),
                "date": str(parsed.get("Date", "")),
                "message_id": str(parsed.get("Message-ID", "")),
            },
        }
    else:
        record = {
            "source": "pasted_body",
            "message_id": "",
            "from_name": "",
            "from_email": "",
            "to": "",
            "cc": "",
            "subject": "",
            "received_at": "",
            "body": _clean_body(raw_text),
            "raw_headers": {},
        }
    record["fingerprint"] = _fingerprint(record)
    return record


def create_inbound_record(username: str, parsed_email: dict, *, customer_id: str = "") -> tuple[bool, dict]:
    """Persist an inbound email for the user idempotently by fingerprint."""
    if not username:
        return False, {"error": "username_required"}
    body = parsed_email.get("body", "").strip()
    if not body:
        return False, {"error": "email_body_required"}

    emails = load_inbound_emails(username)
    fingerprint = parsed_email.get("fingerprint") or _fingerprint(parsed_email)
    for existing in emails:
        if existing.get("fingerprint") == fingerprint:
            return False, existing

    record = {
        "id": uuid.uuid4().hex[:12],
        "fingerprint": fingerprint,
        "status": "pending",  # pending / drafted / replied / archived
        "customer_id": customer_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        **parsed_email,
    }
    emails.append(record)
    if len(emails) > MAX_INBOUND_EMAILS_PER_USER:
        emails = emails[-MAX_INBOUND_EMAILS_PER_USER:]
    save_inbound_emails(username, emails)
    return True, record


def list_inbound_emails(username: str, status: str | None = None, limit: int = 100) -> list[dict]:
    """List recent inbound emails for a user."""
    emails = load_inbound_emails(username)
    if status:
        emails = [email for email in emails if email.get("status") == status]
    emails.sort(key=lambda email: email.get("created_at", ""), reverse=True)
    return emails[:limit]


def update_inbound_status(username: str, inbound_id: str, status: str) -> bool:
    """Update an inbound email status."""
    if status not in {"pending", "drafted", "replied", "archived"}:
        return False
    emails = load_inbound_emails(username)
    for email in emails:
        if email.get("id") == inbound_id:
            email["status"] = status
            email["updated_at"] = _now_iso()
            save_inbound_emails(username, emails)
            return True
    return False


def get_inbound_email(username: str, inbound_id: str) -> dict | None:
    """Return one inbound email by ID."""
    for email in load_inbound_emails(username):
        if email.get("id") == inbound_id:
            return email
    return None


def seed_inquiry_session_state(st, inbound: dict) -> None:
    """Seed the existing inquiry reply page from an inbound email record."""
    display_name = inbound.get("from_name") or inbound.get("from_email") or "客户"
    subject = inbound.get("subject", "")
    body = inbound.get("body", "")
    prefix = f"Subject: {subject}\n\n" if subject else ""
    st.session_state["inquiry_text_val"] = prefix + body
    st.session_state["inquiry_customer_val"] = display_name
