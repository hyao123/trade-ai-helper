"""
utils/user_prefs.py
-------------------
User preference persistence for auto-filling form fields.

Stores per-user preferences:
  - company_name, contact_name, email, phone  (seller identity)
  - signature_name                            (email signature)
  - default_product                           (last used product)
  - default_language                          (preferred output language)
  - default_trade_term                        (FOB/CIF/etc)
  - default_tone                              (email tone)
  - ai_style_tone                             (AI writing style: formal/casual/concise)
  - ai_response_length                        (short/medium/long)
  - ai_custom_instructions                    (free-text extra instructions)
  - ai_forbidden_words                        (comma-separated words to avoid)

All values are read/written from data/users/{username}/prefs.json.
"""
from __future__ import annotations

import streamlit as st

from utils.storage import load_json, load_user_json, save_json, save_user_json

_PREFS_FILE = "prefs.json"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULTS: dict[str, str] = {
    "company_name": "",
    "contact_name": "",
    "email": "",
    "phone": "",
    "signature_name": "",
    "default_product": "",
    "default_language": "英语",
    "default_trade_term": "FOB",
    "default_tone": "简洁专业",
    # AI style preferences
    "ai_style_tone": "专业",         # 专业 / 友好 / 正式 / 简洁
    "ai_response_length": "中等",    # 简短 / 中等 / 详细
    "ai_custom_instructions": "",   # Appended to every prompt
    "ai_forbidden_words": "",       # Comma-separated
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get_username() -> str | None:
    user = st.session_state.get("current_user")
    if user and user.get("username") and user["username"] != "admin":
        return user["username"]
    return None


def _load_prefs_raw() -> dict:
    username = _get_username()
    if username:
        return load_user_json(username, _PREFS_FILE, default={})
    return load_json(_PREFS_FILE, default={})


def _save_prefs_raw(data: dict) -> None:
    username = _get_username()
    if username:
        save_user_json(username, _PREFS_FILE, data)
    else:
        save_json(_PREFS_FILE, data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_prefs() -> dict[str, str]:
    """Return all preferences merged with defaults."""
    raw = _load_prefs_raw()
    return {**_DEFAULTS, **raw}


def get_pref(key: str) -> str:
    """Get a single preference value."""
    prefs = get_prefs()
    return prefs.get(key, _DEFAULTS.get(key, ""))


def set_pref(key: str, value: str) -> None:
    """Set a single preference and persist immediately."""
    raw = _load_prefs_raw()
    raw[key] = value
    _save_prefs_raw(raw)


def update_prefs(updates: dict[str, str]) -> None:
    """Bulk-update multiple preferences at once."""
    raw = _load_prefs_raw()
    raw.update(updates)
    _save_prefs_raw(raw)


def save_seller_identity(
    company_name: str,
    contact_name: str,
    email: str = "",
    phone: str = "",
) -> None:
    """Shortcut to persist seller identity fields used across many pages."""
    update_prefs({
        "company_name": company_name,
        "contact_name": contact_name,
        "email": email,
        "phone": phone,
        "signature_name": contact_name,
    })


# ---------------------------------------------------------------------------
# AI style helpers
# ---------------------------------------------------------------------------
def get_ai_style_suffix() -> str:
    """
    Build a short style instruction suffix to append to prompts.

    Returns empty string if no custom preferences are set.
    """
    prefs = get_prefs()
    parts: list[str] = []

    tone = prefs.get("ai_style_tone", "")
    length = prefs.get("ai_response_length", "")
    custom = prefs.get("ai_custom_instructions", "").strip()
    forbidden = prefs.get("ai_forbidden_words", "").strip()

    tone_map = {
        "专业": "Use a professional B2B business tone.",
        "友好": "Use a warm, friendly and approachable tone.",
        "正式": "Use a formal, conservative corporate tone.",
        "简洁": "Be extremely concise and to the point.",
    }
    length_map = {
        "简短": "Keep the response brief (under 80 words).",
        "中等": "Keep the response moderate length (100-150 words).",
        "详细": "Provide a detailed, thorough response (150-250 words).",
    }

    if tone and tone in tone_map:
        parts.append(tone_map[tone])
    if length and length in length_map:
        parts.append(length_map[length])
    if forbidden:
        words = [w.strip() for w in forbidden.split(",") if w.strip()]
        if words:
            parts.append(f"Avoid using these words: {', '.join(words)}.")
    if custom:
        parts.append(custom)

    if not parts:
        return ""
    return "\n\nAdditional style instructions:\n" + " ".join(parts)
