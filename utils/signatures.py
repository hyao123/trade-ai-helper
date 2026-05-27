"""
utils/signatures.py
-------------------
Email signature management.

Users can create multiple signatures (e.g. English formal, Chinese casual)
and set one as default. AI-generated emails with [Your Name]/[Your Company]
placeholders are automatically post-processed to inject the real signature.

Data stored in: data/users/{username}/prefs.json under key "signatures"

Signature dict shape:
{
    "id": "sig_abc123",
    "name": "英文正式签名",          # user-facing label
    "is_default": true,
    "body": "Best regards,\nTom Wang\nSales Director\nXYZ Lighting Co., Ltd.\n+86-755-12345678\nsales@xyz-lighting.com\nwww.xyz-lighting.com",
    "created_at": "..."
}

Public API:
    get_signatures(username) -> list[dict]
    get_default_signature(username) -> dict | None
    add_signature(username, name, body, is_default) -> dict
    update_signature(username, sig_id, updates) -> bool
    delete_signature(username, sig_id) -> bool
    set_default_signature(username, sig_id) -> bool
    apply_signature(text, username) -> str   # replace placeholders
    render_signature_text(sig) -> str        # just the text block
"""
from __future__ import annotations

import secrets
from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("signatures")

_PREFS_FILE = "prefs.json"

# Placeholders that AI models produce (case-insensitive matching)
_PLACEHOLDERS = [
    "[Your Name]",
    "[Your Company]",
    "[Your Name] / [Your Company]",
    "[Your Name]/[Your Company]",
    "[Your Name]\n[Your Company]",
]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def get_signatures(username: str) -> list[dict]:
    """Get all signatures for a user."""
    prefs = load_user_json(username, _PREFS_FILE, default={})
    return prefs.get("signatures", [])


def get_default_signature(username: str) -> dict | None:
    """Get the user's default signature, or None if not set."""
    sigs = get_signatures(username)
    for s in sigs:
        if s.get("is_default"):
            return s
    # Fallback: return first one if exists
    return sigs[0] if sigs else None


def get_signature_by_id(username: str, sig_id: str) -> dict | None:
    """Get a specific signature by ID."""
    for s in get_signatures(username):
        if s.get("id") == sig_id:
            return s
    return None


def add_signature(
    username: str,
    name: str,
    body: str,
    is_default: bool = False,
) -> dict:
    """
    Add a new signature.

    If is_default=True, clears default flag from all others.
    """
    prefs = load_user_json(username, _PREFS_FILE, default={})
    sigs = prefs.get("signatures", [])

    sig_id = f"sig_{secrets.token_hex(4)}"
    sig = {
        "id": sig_id,
        "name": name.strip(),
        "body": body.strip(),
        "is_default": is_default,
        "created_at": datetime.now().isoformat(),
    }

    if is_default:
        for s in sigs:
            s["is_default"] = False

    sigs.append(sig)
    prefs["signatures"] = sigs
    save_user_json(username, _PREFS_FILE, prefs)

    logger.info("Signature added: %s (%s) for %s", name, sig_id, username)
    return sig


def update_signature(username: str, sig_id: str, updates: dict) -> bool:
    """Update a signature (only name and body allowed)."""
    _ALLOWED = {"name", "body"}
    safe = {k: v for k, v in updates.items() if k in _ALLOWED}
    if not safe:
        return False

    prefs = load_user_json(username, _PREFS_FILE, default={})
    sigs = prefs.get("signatures", [])
    for s in sigs:
        if s.get("id") == sig_id:
            s.update(safe)
            prefs["signatures"] = sigs
            save_user_json(username, _PREFS_FILE, prefs)
            return True
    return False


def delete_signature(username: str, sig_id: str) -> bool:
    """Delete a signature by ID."""
    prefs = load_user_json(username, _PREFS_FILE, default={})
    sigs = prefs.get("signatures", [])
    original_len = len(sigs)
    sigs = [s for s in sigs if s.get("id") != sig_id]
    if len(sigs) < original_len:
        # If deleted was default, promote first remaining
        if sigs and not any(s.get("is_default") for s in sigs):
            sigs[0]["is_default"] = True
        prefs["signatures"] = sigs
        save_user_json(username, _PREFS_FILE, prefs)
        return True
    return False


def set_default_signature(username: str, sig_id: str) -> bool:
    """Set a signature as the default (clears others)."""
    prefs = load_user_json(username, _PREFS_FILE, default={})
    sigs = prefs.get("signatures", [])
    found = False
    for s in sigs:
        if s.get("id") == sig_id:
            s["is_default"] = True
            found = True
        else:
            s["is_default"] = False
    if found:
        prefs["signatures"] = sigs
        save_user_json(username, _PREFS_FILE, prefs)
    return found


# ---------------------------------------------------------------------------
# Signature rendering & application
# ---------------------------------------------------------------------------

def render_signature_text(sig: dict | None) -> str:
    """
    Render a signature dict into the text block to append to emails.

    Returns empty string if sig is None.
    """
    if not sig:
        return ""
    return sig.get("body", "").strip()


def apply_signature(text: str, username: str, sig_id: str | None = None) -> str:
    """
    Post-process AI-generated email text: replace [Your Name]/[Your Company]
    placeholders with the user's actual signature.

    Args:
        text: AI-generated email body
        username: current user (to look up their signature)
        sig_id: specific signature to use (None = default)

    Returns:
        Text with placeholders replaced. If no signature configured,
        returns text unchanged (placeholders remain).
    """
    if not text:
        return text

    # Get the signature to apply
    if sig_id:
        sig = get_signature_by_id(username, sig_id)
    else:
        sig = get_default_signature(username)

    if not sig:
        # Fallback: try to build from user_prefs basic fields
        sig_text = _build_fallback_signature(username)
        if not sig_text:
            return text  # nothing to replace with
    else:
        sig_text = render_signature_text(sig)

    if not sig_text:
        return text

    # Replace known placeholders (case-insensitive search)
    result = text
    for placeholder in _PLACEHOLDERS:
        if placeholder.lower() in result.lower():
            # Find actual case in text
            idx = result.lower().find(placeholder.lower())
            while idx >= 0:
                result = result[:idx] + sig_text + result[idx + len(placeholder):]
                idx = result.lower().find(placeholder.lower(), idx + len(sig_text))

    return result


def _build_fallback_signature(username: str) -> str:
    """
    Build a basic signature from user_prefs fields when no formal
    signature is configured.

    Uses: contact_name, company_name, email, phone from prefs.
    """
    prefs = load_user_json(username, _PREFS_FILE, default={})
    parts = []

    name = prefs.get("contact_name", "").strip() or prefs.get("signature_name", "").strip()
    company = prefs.get("company_name", "").strip()
    email = prefs.get("email", "").strip()
    phone = prefs.get("phone", "").strip()

    if name:
        parts.append(name)
    if company:
        parts.append(company)
    if email:
        parts.append(email)
    if phone:
        parts.append(phone)

    return "\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Auto-create default signature from prefs (first-run convenience)
# ---------------------------------------------------------------------------

def ensure_default_signature(username: str) -> dict | None:
    """
    If user has prefs but no signatures, auto-create one from their
    contact info. Called lazily from pages that use signatures.

    Returns the default signature (possibly just created), or None.
    """
    sigs = get_signatures(username)
    if sigs:
        return get_default_signature(username)

    # Try to build from prefs
    fallback = _build_fallback_signature(username)
    if not fallback:
        return None

    # Auto-create
    sig = add_signature(
        username=username,
        name="默认签名 (自动生成)",
        body=fallback,
        is_default=True,
    )
    logger.info("Auto-created default signature for %s", username)
    return sig
