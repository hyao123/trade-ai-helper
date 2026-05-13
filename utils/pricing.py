"""
utils/pricing.py
----------------
Tiered pricing plan system with usage tracking and feature gating.

Tiers:
- free: 20 AI generations/day, basic features only
- pro: 100 AI generations/day, includes logo_upload and data_export
- enterprise: unlimited AI generations/day, all features
"""

from __future__ import annotations

from datetime import date

from utils.storage import load_json, save_json, load_user_json, save_user_json

# ---------------------------------------------------------------------------
# Tier Configuration
# ---------------------------------------------------------------------------
TIER_CONFIG: dict[str, dict] = {
    "free": {
        "daily_limit": 20,
        "features": ["basic"],
    },
    "pro": {
        "daily_limit": 100,
        "features": ["basic", "logo_upload", "data_export"],
    },
    "enterprise": {
        "daily_limit": None,  # unlimited
        "features": ["basic", "logo_upload", "data_export", "priority_support"],
    },
}

_USAGE_FILENAME = "usage.json"
_USERS_DB_FILENAME = "users_db.json"


# ---------------------------------------------------------------------------
# Tier lookup
# ---------------------------------------------------------------------------
def get_user_tier(username: str) -> str:
    """Read the user's tier from users_db.json. Defaults to 'free'."""
    users = load_json(_USERS_DB_FILENAME, default={})
    user = users.get(username)
    if user:
        return user.get("tier", "free")
    return "free"


# ---------------------------------------------------------------------------
# Daily usage tracking
# ---------------------------------------------------------------------------
def get_daily_usage(username: str) -> int:
    """
    Load usage.json from user's directory, return today's count.
    Resets to 0 if the stored date differs from today.
    """
    usage = load_user_json(username, _USAGE_FILENAME, default={})
    today_str = date.today().isoformat()
    if usage.get("date") != today_str:
        return 0
    return usage.get("count", 0)


def increment_usage(username: str) -> tuple[bool, str]:
    """
    Increment daily usage count for the user.

    Returns:
        (True, '') if increment succeeded (within limit).
        (False, error_message) if daily limit exceeded.
    """
    tier = get_user_tier(username)
    config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
    daily_limit = config["daily_limit"]

    today_str = date.today().isoformat()
    usage = load_user_json(username, _USAGE_FILENAME, default={})

    # Reset if date changed
    if usage.get("date") != today_str:
        usage = {"date": today_str, "count": 0}

    current_count = usage.get("count", 0)

    # Check limit (None means unlimited)
    if daily_limit is not None and current_count >= daily_limit:
        return False, f"\u26a0\ufe0f \u4eca\u65e5 AI \u751f\u6210\u6b21\u6570\u5df2\u8fbe\u4e0a\u9650 ({current_count}/{daily_limit})\uff0c\u660e\u65e5\u91cd\u7f6e\u6216\u5347\u7ea7\u5957\u9910"

    # Increment
    usage["count"] = current_count + 1
    usage["date"] = today_str
    save_user_json(username, _USAGE_FILENAME, usage)
    return True, ""


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def get_usage_display(username: str) -> str:
    """
    Return formatted usage string for sidebar display.
    Examples: '5/20', '5/100', '5/\u65e0\u9650\u5236'
    """
    count = get_daily_usage(username)
    tier = get_user_tier(username)
    config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
    daily_limit = config["daily_limit"]
    if daily_limit is None:
        return f"{count}/\u65e0\u9650\u5236"
    return f"{count}/{daily_limit}"


# ---------------------------------------------------------------------------
# Feature gating
# ---------------------------------------------------------------------------
def check_feature_access(username: str, feature: str) -> bool:
    """Check if the user's tier includes the given feature."""
    tier = get_user_tier(username)
    config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
    return feature in config["features"]


# ---------------------------------------------------------------------------
# Tier management
# ---------------------------------------------------------------------------
def upgrade_user_tier(username: str, new_tier: str) -> bool:
    """
    Update the user's tier in users_db.json.

    Returns True if successful, False if user not found or invalid tier.
    """
    if new_tier not in TIER_CONFIG:
        return False

    users = load_json(_USERS_DB_FILENAME, default={})
    if username not in users:
        return False

    users[username]["tier"] = new_tier
    save_json(_USERS_DB_FILENAME, users)
    return True
