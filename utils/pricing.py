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

from utils.repositories import get_user, load_usage, load_users, save_usage, save_users

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
    """Read the user's tier through the active repository backend."""
    user = get_user(username)
    if user:
        return user.get("tier", "free")
    return "free"


# ---------------------------------------------------------------------------
# Daily usage tracking
# ---------------------------------------------------------------------------
def get_daily_usage(username: str) -> int:
    """Return today's AI generation count for the user."""
    usage = load_usage(username)
    today_str = date.today().isoformat()
    if usage.get("date") != today_str:
        return 0
    return usage.get("count", 0)


def increment_usage(username: str) -> tuple[bool, str]:
    """Increment daily usage count for the user if within their tier limit."""
    tier = get_user_tier(username)
    config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
    daily_limit = config["daily_limit"]

    today_str = date.today().isoformat()
    usage = load_usage(username)

    if usage.get("date") != today_str:
        usage = {"date": today_str, "count": 0}

    current_count = usage.get("count", 0)
    if daily_limit is not None and current_count >= daily_limit:
        return False, f"⚠️ 今日 AI 生成次数已达上限 ({current_count}/{daily_limit})，明日重置或升级套餐"

    usage["count"] = current_count + 1
    usage["date"] = today_str

    history = usage.get("history", [])
    today_entry = None
    for entry in history:
        if entry.get("date") == today_str:
            today_entry = entry
            break
    if today_entry is not None:
        today_entry["count"] = usage["count"]
    else:
        history.append({"date": today_str, "count": usage["count"]})
    if len(history) > 7:
        history = history[-7:]
    usage["history"] = history

    save_usage(username, usage)
    return True, ""


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def decrement_usage(username: str) -> None:
    """Decrease today's usage count by 1, used when an API call fails."""
    today_str = date.today().isoformat()
    usage = load_usage(username)
    if usage.get("date") != today_str:
        return

    current_count = usage.get("count", 0)
    if current_count <= 0:
        return

    usage["count"] = current_count - 1
    history = usage.get("history", [])
    for entry in history:
        if entry.get("date") == today_str:
            entry["count"] = usage["count"]
            break
    usage["history"] = history

    save_usage(username, usage)


def get_usage_display(username: str) -> str:
    """Return formatted usage string for sidebar display."""
    count = get_daily_usage(username)
    tier = get_user_tier(username)
    config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
    daily_limit = config["daily_limit"]
    if daily_limit is None:
        return f"{count}/无限制"
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
    """Update the user's tier through the active repository backend."""
    if new_tier not in TIER_CONFIG:
        return False

    users = load_users()
    if username not in users:
        return False

    users[username]["tier"] = new_tier
    save_users(users)
    return True


# ---------------------------------------------------------------------------
# Usage history
# ---------------------------------------------------------------------------
def get_usage_history(username: str) -> list[dict]:
    """Return the user's 7-day AI usage history."""
    usage = load_usage(username)
    history = usage.get("history", [])
    return history[-7:]
