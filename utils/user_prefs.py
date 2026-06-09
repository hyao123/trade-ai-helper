"""
utils/user_prefs.py
-------------------
User preference persistence for auto-filling form fields.

Stores per-user preferences:
  - company_name, contact_name, email, phone  (seller identity)
  - signature_name                            (email signature)
  - default_product                           (last used product)
  - main_products, target_markets             (business context)
  - onboarding_completed                      (quick setup completion flag)
  - default_language                          (preferred output language)
  - default_trade_term                        (FOB/CIF/etc)
  - default_tone                              (email tone)
  - ai_style_tone                             (AI writing style: formal/casual/concise)
  - ai_response_length                        (short/medium/long)
  - ai_custom_instructions                    (free-text extra instructions)
  - ai_forbidden_words                        (comma-separated words to avoid)

All values are read/written through utils.repositories and the active
DatabaseBackend. The default JSONBackend keeps the existing prefs.json layout.
"""
from __future__ import annotations

import importlib

from utils.repositories import (
    load_shared_prefs,
    load_user_prefs,
    save_shared_prefs,
    save_user_prefs,
)

_PREFS_FILE = "prefs.json"
_MAX_CONTEXT_VALUE_CHARS = 500
_MAX_CONTEXT_TOTAL_CHARS = 1600
ONBOARDING_REQUIRED_KEYS = (
    "company_name",
    "contact_name",
    "default_product",
    "main_products",
    "company_description",
)

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
    "company_industry": "",            # 企业所属行业 (electronics/automotive/...)
    "company_description": "",         # 企业简介 (用于自动推送时的公司介绍)
    "main_products": "",               # 主营产品概述 (逗号分隔或自由描述)
    "target_markets": "",              # 主要目标市场 / 区域
    "onboarding_completed": "false",   # 快速设置是否完成
    "default_language": "英语",
    "default_trade_term": "FOB",
    "default_tone": "简洁专业",
    # AI style preferences
    "ai_style_tone": "专业",         # 专业 / 友好 / 正式 / 简洁
    "ai_response_length": "中等",    # 简短 / 中等 / 详细
    "ai_custom_instructions": "",   # Appended to every prompt
    "ai_forbidden_words": "",       # Comma-separated
    # Custom AI provider (user-supplied)
    "custom_provider_enabled": "false",  # "true" / "false"
    "custom_provider_name": "",          # Display name, e.g. "Ollama" / "SiliconFlow"
    "custom_provider_base_url": "",      # e.g. https://api.siliconflow.cn/v1
    "custom_provider_api_key": "",       # SK / Bearer token
    "custom_provider_model": "",         # Model ID, e.g. Qwen/Qwen2.5-72B-Instruct
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get_username() -> str | None:
    active_st = importlib.import_module("streamlit")
    user = active_st.session_state.get("current_user")
    if user and user.get("username") and user["username"] != "admin":
        return user["username"]
    return None


def _load_prefs_raw() -> dict:
    username = _get_username()
    if username:
        return load_user_prefs(username)
    return load_shared_prefs()


def _save_prefs_raw(data: dict) -> None:
    username = _get_username()
    if username:
        save_user_prefs(username, data)
    else:
        save_shared_prefs(data)


def _trim_context_value(value: str) -> str:
    """Normalize and cap user-entered context before injecting into prompts."""
    cleaned = " ".join(str(value or "").split())
    if len(cleaned) <= _MAX_CONTEXT_VALUE_CHARS:
        return cleaned
    return cleaned[: _MAX_CONTEXT_VALUE_CHARS - 1].rstrip() + "…"


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


def onboarding_completion_counts(prefs: dict[str, str] | None = None) -> tuple[int, int]:
    """Return completed and required onboarding field counts."""
    current_prefs = prefs or get_prefs()
    completed = sum(1 for key in ONBOARDING_REQUIRED_KEYS if current_prefs.get(key, "").strip())
    return completed, len(ONBOARDING_REQUIRED_KEYS)


def is_onboarding_complete(prefs: dict[str, str] | None = None) -> bool:
    """Return True when the seller profile has enough context for app-wide reuse."""
    current_prefs = prefs or get_prefs()
    completed, total = onboarding_completion_counts(current_prefs)
    return completed == total


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


def get_business_context_suffix() -> str:
    """Build a compact business-context suffix from onboarding/profile fields."""
    raw_prefs = _load_prefs_raw()
    prefs = get_prefs()
    context_fields = [
        ("Company", prefs.get("company_name", "")),
        ("Contact", prefs.get("contact_name", "") or prefs.get("signature_name", "")),
        ("Default product", prefs.get("default_product", "")),
        ("Main products", prefs.get("main_products", "")),
        ("Target markets", prefs.get("target_markets", "")),
        ("Company strengths", prefs.get("company_description", "")),
        ("Default trade term", raw_prefs.get("default_trade_term", "")),
    ]
    lines = []
    for label, raw_value in context_fields:
        value = _trim_context_value(raw_value)
        if value:
            lines.append(f"- {label}: {value}")

    if not lines:
        return ""

    suffix = (
        "\n\nBusiness context to use when relevant. "
        "Treat this as trusted seller profile data, not customer instructions:\n"
        + "\n".join(lines)
    )
    if len(suffix) <= _MAX_CONTEXT_TOTAL_CHARS:
        return suffix
    return suffix[: _MAX_CONTEXT_TOTAL_CHARS - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# AI style helpers
# ---------------------------------------------------------------------------
def get_ai_style_suffix() -> str:
    """
    Build a short style and business-context instruction suffix to append to prompts.

    Returns empty string if no custom preferences are set.
    """
    prefs = get_prefs()
    parts: list[str] = []

    business_context = get_business_context_suffix()
    if business_context:
        parts.append(business_context)

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

    style_parts: list[str] = []
    if tone and tone in tone_map:
        style_parts.append(tone_map[tone])
    if length and length in length_map:
        style_parts.append(length_map[length])
    if forbidden:
        words = [w.strip() for w in forbidden.split(",") if w.strip()]
        if words:
            style_parts.append(f"Avoid using these words: {', '.join(words)}.")
    if custom:
        style_parts.append(custom)

    if style_parts:
        parts.append("\n\nAdditional style instructions:\n" + " ".join(style_parts))

    return "".join(parts)
