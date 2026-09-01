"""Automatic lead capture from classified inquiry emails.

When the AI inbox pipeline classifies an email as a high-intent inquiry
(inquiry / order_intent / complaint / sample_request / negotiation), the
sender is captured into the CRM as a new customer (deduplicated by email),
a follow-up workflow is started, and a hot-lead notification is raised.
Low-intent mail and senders without an address are ignored.

The capture path reuses the existing ``customers`` and ``workflow`` modules;
in non-UI callers (tests, backgrounds) a Streamlit session stub must be in
place, exactly like the rest of the app's session-scoped storage.
"""
from __future__ import annotations

import re
from datetime import datetime

from utils.customers import add_customer, get_customers
from utils.logger import get_logger
from utils.notifications import notify_hot_lead
from utils.workflow import create_workflow_from_customer

logger = get_logger("lead_capture")

# Intents that represent a real sales opportunity worth capturing.
HIGH_INTENT = {"inquiry", "order_intent", "complaint", "sample_request", "negotiation"}

_DEFAULT_STAGE = "新客户"


def _parse_sender(from_field: str) -> tuple[str, str]:
    """Split a From header into (name, bare_email)."""
    raw = (from_field or "").strip()
    name = raw
    email = ""
    m = re.search(r"<([^>]+)>", raw)
    if m:
        email = m.group(1).strip()
        name = (raw[: m.start()] or "").strip(" '\"")
    elif "@" in raw:
        email = raw
        name = raw.split("@", 1)[0].strip()
    return name, email


def _find_customer_by_email(customers: list[dict], email: str) -> dict | None:
    needle = email.strip().lower()
    for cust in customers:
        if (cust.get("email") or "").strip().lower() == needle:
            return cust
    return None


def capture_lead_from_email(
    username: str,
    email_entry: dict,
    classification: dict,
) -> dict:
    """Capture one classified email as a CRM lead.

    Returns:
        ``{"created": True, "customer": {...}, "workflow_created": bool,
        "notified": bool}`` on capture; or ``{"created": False,
        "reason": "low_intent" | "no_email" | "duplicate"}`` to skip.
    """
    intent = classification.get("intent", "info_only")
    if intent not in HIGH_INTENT:
        return {"created": False, "reason": "low_intent"}

    name, email = _parse_sender(email_entry.get("from", ""))
    if not email:
        return {"created": False, "reason": "no_email"}

    customers = get_customers()
    if _find_customer_by_email(customers, email):
        return {"created": False, "reason": "duplicate"}

    customer = {
        "company": name or email.split("@")[-1] or "邮件线索",
        "contact": name or email,
        "email": email,
        "product": "",
        "stage": _DEFAULT_STAGE,
        "source": "email_capture",
        "intent": intent,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "last_contact": datetime.now().strftime("%Y-%m-%d"),
    }
    add_customer(customer)

    workflow_created = False
    try:
        workflow_created = bool(create_workflow_from_customer(customer))
    except Exception as exc:  # noqa: BLE001 - workflow is best-effort
        logger.debug("Workflow creation skipped for %s: %s", email, exc)

    notified = False
    try:
        notify_hot_lead(
            username,
            customer_name=name or email,
            score=int(classification.get("priority_score", 0) or 0),
        )
        notified = True
    except Exception as exc:  # noqa: BLE001 - notification is best-effort
        logger.debug("Hot-lead notification skipped for %s: %s", email, exc)

    logger.info("Lead captured from email intent=%s email=%s workflow=%s", intent, email, workflow_created)
    return {
        "created": True,
        "customer": customer,
        "workflow_created": workflow_created,
        "notified": notified,
    }


def capture_leads_from_inbox(username: str, processed_results: list[dict]) -> list[dict]:
    """Capture leads from every classified entry in a processed inbox batch."""
    captured: list[dict] = []
    for entry in processed_results or []:
        try:
            result = capture_lead_from_email(
                username,
                entry.get("email", {}),
                entry.get("classification", {}),
            )
        except Exception as exc:  # noqa: BLE001 - one bad email must not stop the batch
            logger.debug("Lead capture error for %s: %s", username, exc)
            continue
        if result.get("created"):
            captured.append(result)
    return captured