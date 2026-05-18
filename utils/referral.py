"""
utils/referral.py
-----------------
Invite referral system for viral growth.

Mechanics:
- Each registered user gets a unique referral code
- When a new user signs up with a referral code, BOTH parties get bonus credits
- Referral stats are tracked (invites sent, signups, conversions)
- Tiered rewards: more referrals = bigger bonuses

Reward structure:
  - Referrer: +30 AI credits per successful signup
  - Invitee: +20 AI credits (welcome bonus)
  - Milestone bonuses:
    - 5 referrals: +100 credits
    - 10 referrals: +1 week Pro trial
    - 25 referrals: +1 month Pro free

Usage:
    from utils.referral import (
        get_referral_code,
        apply_referral,
        get_referral_stats,
        get_referral_leaderboard,
    )
"""
from __future__ import annotations

import secrets
from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_json, load_user_json, save_json, save_user_json

logger = get_logger("referral")

_REFERRALS_FILE = "referrals.json"

# Reward configuration
REFERRER_BONUS_CREDITS = 30
INVITEE_BONUS_CREDITS = 20

MILESTONE_REWARDS = [
    {"count": 5, "reward": "credits", "amount": 100, "label": "+100 额外额度"},
    {"count": 10, "reward": "pro_trial", "days": 7, "label": "7天 Pro 试用"},
    {"count": 25, "reward": "pro_free", "days": 30, "label": "1个月 Pro 免费"},
    {"count": 50, "reward": "credits", "amount": 500, "label": "+500 额外额度"},
]


# ---------------------------------------------------------------------------
# Referral code management
# ---------------------------------------------------------------------------

def get_referral_code(username: str) -> str:
    """
    Get or generate the user's unique referral code.

    Each user has exactly one code, generated on first request.

    Args:
        username: The referrer's username

    Returns:
        The user's referral code string (8 chars, URL-safe)
    """
    referral_data = load_user_json(username, "referral.json", default={})

    if referral_data.get("code"):
        return referral_data["code"]

    # Generate new code
    code = _generate_unique_code()
    referral_data["code"] = code
    referral_data["created_at"] = datetime.now().isoformat()
    referral_data["total_referrals"] = 0
    referral_data["total_credits_earned"] = 0
    save_user_json(username, "referral.json", referral_data)

    # Register in global lookup
    _register_code(code, username)

    logger.info("Referral code generated for %s: %s", username, code)
    return code


def get_referral_link(username: str) -> str:
    """Get the full referral URL for sharing."""
    from utils.secrets import get_secret
    code = get_referral_code(username)
    base_url = get_secret("APP_BASE_URL") or "https://trade-ai-helper.streamlit.app"
    return f"{base_url}/?ref={code}"


def _generate_unique_code() -> str:
    """Generate a unique, URL-safe referral code."""
    all_referrals = load_json(_REFERRALS_FILE, default={})
    for _ in range(100):  # Max attempts
        code = secrets.token_urlsafe(6)[:8]  # 8-char code
        if code not in all_referrals:
            return code
    # Fallback: longer code
    return secrets.token_urlsafe(10)[:12]


def _register_code(code: str, username: str) -> None:
    """Register a referral code in the global lookup table."""
    all_referrals = load_json(_REFERRALS_FILE, default={})
    if not isinstance(all_referrals, dict):
        all_referrals = {}
    all_referrals[code] = {
        "owner": username,
        "created_at": datetime.now().isoformat(),
        "uses": [],
    }
    save_json(_REFERRALS_FILE, all_referrals)


# ---------------------------------------------------------------------------
# Applying referrals (during signup)
# ---------------------------------------------------------------------------

def validate_referral_code(code: str) -> tuple[bool, str]:
    """
    Validate a referral code exists and is usable.

    Args:
        code: The referral code to validate

    Returns:
        (is_valid, referrer_username_or_error)
    """
    if not code or not code.strip():
        return False, "Empty referral code"

    all_referrals = load_json(_REFERRALS_FILE, default={})
    if not isinstance(all_referrals, dict):
        return False, "Invalid referral code"

    entry = all_referrals.get(code.strip())
    if not entry:
        return False, "Invalid referral code"

    return True, entry["owner"]


def apply_referral(code: str, new_username: str) -> tuple[bool, str]:
    """
    Apply a referral code during new user signup.

    Awards credits to both referrer and invitee.
    Should be called AFTER successful registration.

    Args:
        code: Referral code used during signup
        new_username: The newly registered user's username

    Returns:
        (success, message) tuple
    """
    if not code or not code.strip():
        return False, "No referral code"

    code = code.strip()
    is_valid, result = validate_referral_code(code)
    if not is_valid:
        return False, result

    referrer_username = result

    # Prevent self-referral
    if referrer_username == new_username:
        return False, "Cannot use your own referral code"

    # Check if this user already used a referral
    invitee_data = load_user_json(new_username, "referral.json", default={})
    if invitee_data.get("referred_by"):
        return False, "Already used a referral code"

    # Record the referral
    all_referrals = load_json(_REFERRALS_FILE, default={})
    entry = all_referrals.get(code, {})
    uses = entry.get("uses", [])

    # Prevent duplicate referral for same user
    if any(u.get("username") == new_username for u in uses):
        return False, "Referral already applied"

    uses.append({
        "username": new_username,
        "applied_at": datetime.now().isoformat(),
    })
    entry["uses"] = uses
    all_referrals[code] = entry
    save_json(_REFERRALS_FILE, all_referrals)

    # Award credits to referrer
    _award_credits(referrer_username, REFERRER_BONUS_CREDITS, f"Referral: {new_username} signed up")
    _update_referrer_stats(referrer_username)

    # Award credits to invitee
    _award_credits(new_username, INVITEE_BONUS_CREDITS, f"Welcome bonus (referred by {referrer_username})")
    invitee_data["referred_by"] = referrer_username
    invitee_data["referred_at"] = datetime.now().isoformat()
    invitee_data["bonus_received"] = INVITEE_BONUS_CREDITS
    save_user_json(new_username, "referral.json", invitee_data)

    # Check milestone rewards for referrer
    _check_milestones(referrer_username)

    logger.info("Referral applied: %s referred %s (code=%s)", referrer_username, new_username, code)
    return True, f"🎉 Welcome bonus: +{INVITEE_BONUS_CREDITS} AI credits!"


# ---------------------------------------------------------------------------
# Credit system
# ---------------------------------------------------------------------------

def _award_credits(username: str, amount: int, reason: str) -> None:
    """Award bonus AI credits to a user."""
    credits_data = load_user_json(username, "bonus_credits.json", default={
        "balance": 0,
        "history": [],
    })

    credits_data["balance"] = credits_data.get("balance", 0) + amount
    history = credits_data.get("history", [])
    history.append({
        "amount": amount,
        "reason": reason,
        "awarded_at": datetime.now().isoformat(),
    })
    # Keep last 100 entries
    credits_data["history"] = history[-100:]
    save_user_json(username, "bonus_credits.json", credits_data)
    logger.debug("Credits awarded: %s +%d (%s)", username, amount, reason)


def get_bonus_credits(username: str) -> int:
    """Get the user's current bonus credit balance."""
    credits_data = load_user_json(username, "bonus_credits.json", default={"balance": 0})
    return credits_data.get("balance", 0)


def consume_bonus_credit(username: str) -> bool:
    """
    Consume one bonus credit (called when user makes an AI request over their plan limit).

    Returns:
        True if a credit was consumed, False if no credits available
    """
    credits_data = load_user_json(username, "bonus_credits.json", default={"balance": 0})
    balance = credits_data.get("balance", 0)
    if balance <= 0:
        return False
    credits_data["balance"] = balance - 1
    save_user_json(username, "bonus_credits.json", credits_data)
    return True


# ---------------------------------------------------------------------------
# Referrer stats & milestones
# ---------------------------------------------------------------------------

def _update_referrer_stats(username: str) -> None:
    """Update the referrer's stats after a new referral."""
    referral_data = load_user_json(username, "referral.json", default={})
    referral_data["total_referrals"] = referral_data.get("total_referrals", 0) + 1
    referral_data["total_credits_earned"] = (
        referral_data.get("total_credits_earned", 0) + REFERRER_BONUS_CREDITS
    )
    referral_data["last_referral_at"] = datetime.now().isoformat()
    save_user_json(username, "referral.json", referral_data)


def _check_milestones(username: str) -> None:
    """Check and award milestone bonuses."""
    referral_data = load_user_json(username, "referral.json", default={})
    total = referral_data.get("total_referrals", 0)
    achieved = referral_data.get("milestones_achieved", [])

    for milestone in MILESTONE_REWARDS:
        milestone_key = f"milestone_{milestone['count']}"
        if total >= milestone["count"] and milestone_key not in achieved:
            # Award milestone
            if milestone["reward"] == "credits":
                _award_credits(username, milestone["amount"], f"Milestone: {milestone['count']} referrals!")
            elif milestone["reward"] in ("pro_trial", "pro_free"):
                # Grant temporary Pro access
                _grant_temporary_upgrade(username, milestone.get("days", 7))

            achieved.append(milestone_key)
            referral_data["milestones_achieved"] = achieved
            save_user_json(username, "referral.json", referral_data)
            logger.info("Milestone achieved: %s reached %d referrals", username, milestone["count"])


def _grant_temporary_upgrade(username: str, days: int) -> None:
    """Grant temporary Pro tier access as a milestone reward."""
    from datetime import timedelta
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    upgrade_data = load_user_json(username, "temp_upgrade.json", default={})
    upgrade_data["tier"] = "pro"
    upgrade_data["expires"] = expires
    upgrade_data["reason"] = "referral_milestone"
    save_user_json(username, "temp_upgrade.json", upgrade_data)
    logger.info("Temporary Pro granted to %s for %d days", username, days)


# ---------------------------------------------------------------------------
# Statistics & leaderboard
# ---------------------------------------------------------------------------

def get_referral_stats(username: str) -> dict:
    """
    Get detailed referral stats for a user.

    Returns:
        Dict with code, total_referrals, credits_earned, milestones, etc.
    """
    referral_data = load_user_json(username, "referral.json", default={})
    bonus_credits = get_bonus_credits(username)

    code = referral_data.get("code", "")
    total = referral_data.get("total_referrals", 0)

    # Next milestone
    next_milestone = None
    for milestone in MILESTONE_REWARDS:
        if total < milestone["count"]:
            next_milestone = {
                "target": milestone["count"],
                "remaining": milestone["count"] - total,
                "reward_label": milestone["label"],
            }
            break

    return {
        "code": code,
        "link": get_referral_link(username) if code else "",
        "total_referrals": total,
        "total_credits_earned": referral_data.get("total_credits_earned", 0),
        "bonus_credits_balance": bonus_credits,
        "milestones_achieved": referral_data.get("milestones_achieved", []),
        "next_milestone": next_milestone,
        "referred_by": referral_data.get("referred_by"),
        "last_referral_at": referral_data.get("last_referral_at"),
    }


def get_referral_leaderboard(limit: int = 10) -> list[dict]:
    """
    Get the top referrers ranked by total successful referrals.

    Returns:
        List of dicts with username, total_referrals, sorted descending
    """
    all_referrals = load_json(_REFERRALS_FILE, default={})
    if not isinstance(all_referrals, dict):
        return []

    # Aggregate by owner
    referrer_counts: dict[str, int] = {}
    for _code, entry in all_referrals.items():
        owner = entry.get("owner", "")
        uses = entry.get("uses", [])
        if owner:
            referrer_counts[owner] = referrer_counts.get(owner, 0) + len(uses)

    # Sort and return top N
    sorted_referrers = sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {"username": username, "total_referrals": count, "rank": i + 1}
        for i, (username, count) in enumerate(sorted_referrers[:limit])
        if count > 0
    ]
