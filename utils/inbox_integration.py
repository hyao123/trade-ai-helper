"""
utils/inbox_integration.py
---------------------------
Gmail & Outlook (Microsoft Graph) inbox integration via OAuth2.

Provides:
- OAuth2 authorization flow (code exchange → access/refresh tokens)
- Fetch recent emails from inbox
- Send emails via user's own account
- Label/folder management
- Token refresh logic

Supported Providers:
  - gmail: Google Gmail API (OAuth2)
  - outlook: Microsoft Graph API (OAuth2)

Configuration (env / secrets):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET
  OUTLOOK_CLIENT_ID, OUTLOOK_CLIENT_SECRET

Usage:
    from utils.inbox_integration import (
        get_auth_url, exchange_code, fetch_inbox, send_via_provider,
    )
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime

from utils.logger import get_logger
from utils.secrets import get_secret
from utils.storage import load_user_json, save_user_json

logger = get_logger("inbox_integration")

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

PROVIDERS = {
    "gmail": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "api_base": "https://gmail.googleapis.com/gmail/v1",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.labels",
        ],
        "client_id_env": "GMAIL_CLIENT_ID",
        "client_secret_env": "GMAIL_CLIENT_SECRET",
    },
    "outlook": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "api_base": "https://graph.microsoft.com/v1.0",
        "scopes": [
            "Mail.Read",
            "Mail.Send",
            "offline_access",
        ],
        "client_id_env": "OUTLOOK_CLIENT_ID",
        "client_secret_env": "OUTLOOK_CLIENT_SECRET",
    },
}

_TOKENS_FILE = "inbox_tokens.json"


# ---------------------------------------------------------------------------
# OAuth2 flow
# ---------------------------------------------------------------------------

def is_provider_configured(provider: str) -> bool:
    """Check if OAuth credentials are configured for a provider."""
    config = PROVIDERS.get(provider)
    if not config:
        return False
    return bool(get_secret(config["client_id_env"])) and bool(get_secret(config["client_secret_env"]))


def get_available_providers() -> list[str]:
    """Return list of configured email providers."""
    return [p for p in PROVIDERS if is_provider_configured(p)]


def get_auth_url(provider: str, redirect_uri: str, state: str = "") -> str:
    """
    Generate the OAuth2 authorization URL for the user to visit.

    Args:
        provider: 'gmail' or 'outlook'
        redirect_uri: Where to redirect after authorization
        state: Optional CSRF state parameter

    Returns:
        Full authorization URL string
    """
    config = PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    client_id = get_secret(config["client_id_env"])
    scopes = " ".join(config["scopes"])

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",  # Gmail: get refresh_token
        "prompt": "consent",
        "state": state or provider,
    }

    return f"{config['auth_url']}?{urllib.parse.urlencode(params)}"


def exchange_code(
    provider: str,
    code: str,
    redirect_uri: str,
    username: str,
) -> tuple[bool, str]:
    """
    Exchange authorization code for access/refresh tokens.

    Stores tokens securely in user's data directory.

    Args:
        provider: 'gmail' or 'outlook'
        code: Authorization code from OAuth callback
        redirect_uri: Must match the one used in get_auth_url
        username: User to store tokens for

    Returns:
        (success, message) tuple
    """
    config = PROVIDERS.get(provider)
    if not config:
        return False, f"Unknown provider: {provider}"

    client_id = get_secret(config["client_id_env"])
    client_secret = get_secret(config["client_secret_env"])

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()

    try:
        req = urllib.request.Request(
            config["token_url"],
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        token_data = json.loads(resp.read().decode())
    except Exception as e:
        logger.error("Token exchange failed for %s: %s", provider, e)
        return False, f"Token exchange failed: {e}"

    # Store tokens
    tokens = {
        "provider": provider,
        "access_token": token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_in": token_data.get("expires_in", 3600),
        "token_type": token_data.get("token_type", "Bearer"),
        "obtained_at": datetime.now().isoformat(),
        "email": _get_user_email(provider, token_data.get("access_token", "")),
    }

    save_user_json(username, _TOKENS_FILE, tokens)
    logger.info("OAuth tokens stored for %s (provider=%s)", username, provider)
    return True, "Email connected successfully"


def get_connection_status(username: str) -> dict:
    """
    Check if a user has an active email connection.

    Returns:
        Dict with connected (bool), provider, email, needs_refresh
    """
    tokens = load_user_json(username, _TOKENS_FILE, default={})
    if not tokens or not tokens.get("access_token"):
        return {"connected": False, "provider": None, "email": None}

    # Check if token needs refresh
    obtained_at = tokens.get("obtained_at", "")
    expires_in = tokens.get("expires_in", 3600)
    needs_refresh = False

    if obtained_at:
        try:
            obtained = datetime.fromisoformat(obtained_at)
            elapsed = (datetime.now() - obtained).total_seconds()
            needs_refresh = elapsed > (expires_in - 300)  # Refresh 5 min early
        except (ValueError, TypeError):
            needs_refresh = True

    return {
        "connected": True,
        "provider": tokens.get("provider"),
        "email": tokens.get("email"),
        "needs_refresh": needs_refresh,
    }


def disconnect(username: str) -> bool:
    """Remove stored tokens (disconnect email)."""
    save_user_json(username, _TOKENS_FILE, {})
    logger.info("Email disconnected for %s", username)
    return True


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def _refresh_token(username: str) -> str | None:
    """
    Refresh the access token using the stored refresh token.

    Returns new access_token or None on failure.
    """
    tokens = load_user_json(username, _TOKENS_FILE, default={})
    provider = tokens.get("provider")
    refresh_token = tokens.get("refresh_token")

    if not provider or not refresh_token:
        return None

    config = PROVIDERS.get(provider)
    if not config:
        return None

    client_id = get_secret(config["client_id_env"])
    client_secret = get_secret(config["client_secret_env"])

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()

    try:
        req = urllib.request.Request(
            config["token_url"],
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        token_data = json.loads(resp.read().decode())

        # Update stored tokens
        tokens["access_token"] = token_data.get("access_token", tokens["access_token"])
        tokens["expires_in"] = token_data.get("expires_in", 3600)
        tokens["obtained_at"] = datetime.now().isoformat()
        if token_data.get("refresh_token"):
            tokens["refresh_token"] = token_data["refresh_token"]

        save_user_json(username, _TOKENS_FILE, tokens)
        logger.info("Token refreshed for %s", username)
        return tokens["access_token"]
    except Exception as e:
        logger.error("Token refresh failed for %s: %s", username, e)
        return None


def _get_valid_token(username: str) -> str | None:
    """Get a valid access token, refreshing if necessary."""
    status = get_connection_status(username)
    if not status["connected"]:
        return None

    if status["needs_refresh"]:
        return _refresh_token(username)

    tokens = load_user_json(username, _TOKENS_FILE, default={})
    return tokens.get("access_token")


# ---------------------------------------------------------------------------
# Email operations
# ---------------------------------------------------------------------------

def fetch_inbox(
    username: str,
    max_results: int = 20,
    query: str = "",
) -> tuple[bool, list[dict] | str]:
    """
    Fetch recent emails from the user's connected inbox.

    Args:
        username: User whose inbox to fetch
        max_results: Maximum emails to return
        query: Optional search query (Gmail: q parameter, Outlook: $search)

    Returns:
        (True, list_of_email_dicts) on success
        (False, error_message) on failure
    """
    token = _get_valid_token(username)
    if not token:
        return False, "Not connected. Please connect your email first."

    tokens = load_user_json(username, _TOKENS_FILE, default={})
    provider = tokens.get("provider")

    try:
        if provider == "gmail":
            return _fetch_gmail(token, max_results, query)
        elif provider == "outlook":
            return _fetch_outlook(token, max_results, query)
        else:
            return False, f"Unsupported provider: {provider}"
    except Exception as e:
        logger.error("Inbox fetch failed for %s: %s", username, e)
        return False, f"Failed to fetch emails: {e}"


def send_via_provider(
    username: str,
    to_email: str,
    subject: str,
    body: str,
) -> tuple[bool, str]:
    """
    Send an email using the user's connected account.

    Args:
        username: Sender (must have connected email)
        to_email: Recipient address
        subject: Email subject
        body: Plain text body

    Returns:
        (success, message) tuple
    """
    token = _get_valid_token(username)
    if not token:
        return False, "Not connected. Please connect your email first."

    tokens = load_user_json(username, _TOKENS_FILE, default={})
    provider = tokens.get("provider")

    try:
        if provider == "gmail":
            return _send_gmail(token, to_email, subject, body)
        elif provider == "outlook":
            return _send_outlook(token, to_email, subject, body)
        else:
            return False, f"Unsupported provider: {provider}"
    except Exception as e:
        logger.error("Send failed for %s: %s", username, e)
        return False, f"Send failed: {e}"


# ---------------------------------------------------------------------------
# Gmail implementation
# ---------------------------------------------------------------------------

def _fetch_gmail(token: str, max_results: int, query: str) -> tuple[bool, list[dict] | str]:
    """Fetch emails from Gmail API."""
    params = {"maxResults": max_results}
    if query:
        params["q"] = query

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {token}"}

    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())

    messages = data.get("messages", [])
    emails = []

    # Fetch details for each message (batch of first N)
    for msg_ref in messages[:max_results]:
        msg_id = msg_ref["id"]
        detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
        detail_req = urllib.request.Request(detail_url, headers=headers)
        detail_resp = urllib.request.urlopen(detail_req, timeout=15)
        msg_data = json.loads(detail_resp.read().decode())

        email_info = _parse_gmail_message(msg_data)
        if email_info:
            emails.append(email_info)

    return True, emails


def _parse_gmail_message(msg: dict) -> dict | None:
    """Parse a Gmail message into a standardized dict."""
    headers_list = msg.get("payload", {}).get("headers", [])
    headers = {h["name"].lower(): h["value"] for h in headers_list}

    snippet = msg.get("snippet", "")
    labels = msg.get("labelIds", [])

    return {
        "id": msg["id"],
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": snippet,
        "is_unread": "UNREAD" in labels,
        "labels": labels,
        "provider": "gmail",
    }


def _send_gmail(token: str, to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send an email via Gmail API."""
    import base64
    from email.mime.text import MIMEText

    msg = MIMEText(body, "plain", "utf-8")
    msg["to"] = to_email
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    payload = json.dumps({"raw": raw}).encode()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)

    if resp.status in (200, 201):
        return True, "Email sent via Gmail"
    return False, f"Gmail send failed (HTTP {resp.status})"


# ---------------------------------------------------------------------------
# Outlook (Microsoft Graph) implementation
# ---------------------------------------------------------------------------

def _fetch_outlook(token: str, max_results: int, query: str) -> tuple[bool, list[dict] | str]:
    """Fetch emails from Microsoft Graph API."""
    url = f"https://graph.microsoft.com/v1.0/me/messages?$top={max_results}&$orderby=receivedDateTime desc"
    if query:
        url += f"&$search=\"{urllib.parse.quote(query)}\""

    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())

    emails = []
    for msg in data.get("value", []):
        emails.append({
            "id": msg["id"],
            "from": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
            "from_name": msg.get("from", {}).get("emailAddress", {}).get("name", ""),
            "subject": msg.get("subject", ""),
            "date": msg.get("receivedDateTime", ""),
            "snippet": msg.get("bodyPreview", "")[:150],
            "is_unread": not msg.get("isRead", True),
            "provider": "outlook",
        })

    return True, emails


def _send_outlook(token: str, to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send an email via Microsoft Graph API."""
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    payload = json.dumps({
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        }
    }).encode()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)

    if resp.status == 202:
        return True, "Email sent via Outlook"
    return False, f"Outlook send failed (HTTP {resp.status})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_email(provider: str, access_token: str) -> str:
    """Fetch the user's email address using the access token."""
    if not access_token:
        return ""
    try:
        if provider == "gmail":
            url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
            headers = {"Authorization": f"Bearer {access_token}"}
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            return data.get("emailAddress", "")
        elif provider == "outlook":
            url = "https://graph.microsoft.com/v1.0/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            return data.get("mail", "") or data.get("userPrincipalName", "")
    except Exception as e:
        logger.debug("Could not fetch user email for %s: %s", provider, e)
    return ""
