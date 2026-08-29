"""
utils/mailslurp_integration.py
------------------------------
Programmatic email *receiving* via MailSlurp (https://www.mailslurp.com).

MailSlurp is an email API that lets you create disposable/real inboxes and read
incoming mail programmatically. This is complementary to the Gmail/Outlook OAuth
inbox (utils.inbox_integration): instead of connecting a user's personal mailbox,
this module mints a dedicated receive inbox (e.g. sales@yourbrand.com) and polls
it for customer inquiries / replies. The normalized messages are then fed into
the existing AI classification pipeline (utils.inbox_ai) unchanged.

Architecture / data flow:
  1. ensure_inbox(username)  -> (ok, inbox_info)
       Creates (once) a MailSlurp inbox for the user and persists its id +
       emailAddress under data/users/<username>/mailslurp_inbox.json.
  2. fetch_received_emails(username, max_results) -> (ok, messages|error)
       Lists the newest messages from that inbox and fetches each one's
       plain-text body, returning messages in the same dict shape that
       utils.inbox_ai.process_inbox expects (id / from / subject / snippet /
       date / provider).
  3. process_received_inbox(username, max_results) -> (ok, processed|error)
       Convenience wrapper: fetch_received_emails + inbox_ai.process_inbox.

Configuration (env / secrets):
  MAILSLURP_API_KEY : Your MailSlurp API key (required)
  MAILSLURP_INBOX_ID: (optional) an existing inbox id to use. When unset, a new
                      inbox is created per user on first use.

No extra dependency is required: all HTTP calls use Python's standard library.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from utils.logger import get_logger
from utils.secrets import get_secret
from utils.storage import load_user_json, save_user_json

logger = get_logger("mailslurp_integration")

MAILSLURP_API_BASE = "https://api.mailslurp.com"
_INBOX_FILE = "mailslurp_inbox.json"


# ---------------------------------------------------------------------------
# Configuration / state
# ---------------------------------------------------------------------------

def is_mailslurp_configured() -> bool:
    """Return True if the MailSlurp API key is configured."""
    return bool(get_secret("MAILSLURP_API_KEY"))


def _headers() -> dict:
    return {
        "x-api-key": get_secret("MAILSLURP_API_KEY"),
        "Content-Type": "application/json",
    }


def _http_get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.status, resp.read()


def _http_post(url: str, payload: dict, timeout: int = 30):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(),
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.status, resp.read()


def get_inbox_state(username: str) -> dict:
    """Return the persisted inbox state (id + emailAddress + created_at)."""
    return load_user_json(username, _INBOX_FILE, default={}) or {}


def _save_inbox_state(username: str, state: dict) -> None:
    save_user_json(username, _INBOX_FILE, state)


# ---------------------------------------------------------------------------
# Inbox lifecycle
# ---------------------------------------------------------------------------

def ensure_inbox(username: str) -> tuple[bool, dict]:
    """
    Return the user's MailSlurp inbox, creating one if none exists.

    When MAILSLURP_INBOX_ID is configured it is used directly (shared inbox);
    otherwise a fresh inbox is created per user on first use and persisted.

    Returns:
        (True, {id, emailAddress}) on success
        (False, {error}) on failure
    """
    if not is_mailslurp_configured():
        return False, {"error": "MAILSLURP_API_KEY 未配置"}

    # A shared inbox id in config short-circuits entirely.
    configured_id = get_secret("MAILSLURP_INBOX_ID")
    if configured_id:
        return True, {"id": configured_id, "emailAddress": "", "shared": True}

    state = get_inbox_state(username)
    if state.get("id") and state.get("emailAddress"):
        return True, state

    try:
        status, raw = _http_post(f"{MAILSLURP_API_BASE}/v1/inboxes", {})
    except Exception as e:
        logger.error("MailSlurp create inbox failed for %s: %s", username, e)
        return False, {"error": f"创建邮箱失败: {e}"}

    if status not in (200, 201):
        return False, {"error": f"创建邮箱失败 (HTTP {status})"}

    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False, {"error": "创建邮箱返回异常数据"}

    inbox_id = data.get("id", "")
    email_address = data.get("emailAddress", "")
    if not inbox_id or not email_address:
        return False, {"error": "创建邮箱返回缺少 id/emailAddress"}

    state = {
        "id": inbox_id,
        "emailAddress": email_address,
        "created_at": data.get("createdAt", ""),
    }
    _save_inbox_state(username, state)
    logger.info("MailSlurp inbox created for %s: %s", username, email_address)
    return True, state


# ---------------------------------------------------------------------------
# Fetching received emails
# ---------------------------------------------------------------------------

def _normalize_mail(i: dict, body: str = "") -> dict:
    """Convert a MailSlurp email dict into the shared inbox message shape."""
    from_address = i.get("from", "") or ""
    received_at = i.get("receivedAt") or i.get("createdAt") or ""
    snippet = (body.strip() or i.get("body") or i.get("bodyPreview") or "").strip()
    return {
        "id": str(i.get("id", "")),
        "from": from_address,
        "subject": i.get("subject", ""),
        "date": received_at,
        "snippet": snippet[:400],
        "is_unread": True,
        "provider": "mailslurp",
    }


def fetch_received_emails(username: str, max_results: int = 20) -> tuple[bool, list | str]:
    """
    List and fetch the newest messages from the user's MailSlurp inbox.

    Returns:
        (True, [email_dict, ...]) on success — email dicts are shaped exactly
        like utils.inbox_integration.fetch_inbox results, so they can be fed
        straight into utils.inbox_ai.process_inbox.
        (False, error_message) on failure.
    """
    ok, inbox = ensure_inbox(username)
    if not ok:
        return False, inbox.get("error", "MailSlurp 未配置")

    inbox_id = inbox["id"]
    params = urllib.parse.urlencode({"limit": max_results, "sort": "DESC"})
    url = f"{MAILSLURP_API_BASE}/v1/inboxes/{inbox_id}/emails?{params}"

    try:
        status, raw = _http_get(url)
    except Exception as e:
        logger.error("MailSlurp list emails failed for %s: %s", username, e)
        return False, f"拉取邮件失败: {e}"

    if status != 200:
        return False, f"拉取邮件失败 (HTTP {status})"

    try:
        listing = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False, "拉取邮件返回异常数据"

    if isinstance(listing, dict):
        listing = listing.get("content") or listing.get("emails") or []

    emails = []
    for item in listing[:max_results]:
        email_id = item.get("id", "")
        body = _fetch_email_body(email_id)
        emails.append(_normalize_mail(item, body))

    logger.info("MailSlurp fetched %d emails for %s", len(emails), username)
    return True, emails


def _fetch_email_body(email_id: str) -> str:
    """Fetch the plain-text body of a MailSlurp email (best effort)."""
    if not email_id:
        return ""
    try:
        status, raw = _http_get(f"{MAILSLURP_API_BASE}/v1/emails/{email_id}/body", timeout=15)
        if status == 200:
            return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("MailSlurp body fetch failed for %s: %s", email_id, e)
    return ""


# ---------------------------------------------------------------------------
# Feed into the AI inbox pipeline
# ---------------------------------------------------------------------------

def process_received_inbox(
    username: str,
    max_results: int = 20,
    force_reprocess: bool = False,
) -> tuple[bool, list | str]:
    """
    Fetch a MailSlurp inbox and run the AI classification pipeline on it.

    This forwards messages into utils.inbox_ai.process_inbox so MailSlurp-received
    customer mail flows through the exact same intent/priority/reply-suggestion
    machinery as the Gmail/Outlook OAuth inbox.

    Returns:
        (True, processed_list) where each item has email + classification
        (False, error_message) on failure.
    """
    ok, emails = fetch_received_emails(username, max_results=max_results)
    if not ok:
        return False, emails if isinstance(emails, str) else "拉取邮件失败"

    if not emails:
        return True, []

    from utils.inbox_ai import process_inbox
    processed = process_inbox(username, emails, force_reprocess=force_reprocess)
    return True, processed
