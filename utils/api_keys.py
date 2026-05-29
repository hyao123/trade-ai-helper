"""
utils/api_keys.py
-----------------
API Key management for the open developer platform.

Allows paying users (Team/Enterprise) to access Trade AI features
programmatically via REST API. Handles:
  - API key generation (unique, prefix-tagged)
  - Key validation and rate limiting
  - Per-key usage tracking and billing
  - Key revocation
  - Scoped permissions (read, write, generate)

Key format: tai_<tier>_<32-char-hex>
  Examples:
    tai_team_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
    tai_ent_f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3

Rate limits by tier:
  - Team:       100 requests/hour, 1000/day
  - Enterprise: 1000 requests/hour, unlimited/day

Usage:
    from utils.api_keys import (
        create_api_key, validate_api_key, revoke_api_key,
        get_user_api_keys, record_api_usage, check_api_rate_limit,
    )
"""
from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_json, load_user_json, save_json, save_user_json

logger = get_logger("api_keys")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TIER_RATE_LIMITS: dict[str, dict] = {
    "team": {
        "requests_per_hour": 100,
        "requests_per_day": 1000,
        "max_keys": 3,
    },
    "enterprise": {
        "requests_per_hour": 1000,
        "requests_per_day": None,  # Unlimited
        "max_keys": 10,
    },
}

# Available API scopes
SCOPES = {
    "generate": "Generate AI content (emails, replies, quotes)",
    "customers:read": "Read customer data",
    "customers:write": "Create/update/delete customers",
    "emails:send": "Send emails via connected providers",
    "analytics:read": "Read usage analytics and stats",
    "templates:read": "Browse marketplace templates",
}

_KEYS_FILE = "api_keys.json"
_RATE_COUNTERS_FILE = "api_rate_counters.json"


def _load_rate_counters() -> dict[str, list[float]]:
    """Load persisted per-key API request timestamps."""
    raw = load_json(_RATE_COUNTERS_FILE, default={})
    return {key: [float(t) for t in value] for key, value in raw.items() if isinstance(value, list)}


def _save_rate_counters(counters: dict[str, list[float]]) -> None:
    """Persist per-key API request timestamps."""
    save_json(_RATE_COUNTERS_FILE, counters)


def _prune_rate_counters(counters: dict[str, list[float]], key_id: str, now: float) -> list[float]:
    """Keep only timestamps within the daily rate-limit window."""
    day_ago = now - 86400
    counters[key_id] = [t for t in counters.get(key_id, []) if t > day_ago]
    return counters[key_id]

# ---------------------------------------------------------------------------
# Key generation & management
# ---------------------------------------------------------------------------

def create_api_key(
    username: str,
    name: str = "",
    scopes: list[str] | None = None,
) -> tuple[bool, str, str]:
    """
    Generate a new API key for a user.

    Args:
        username: The user creating the key
        name: Optional human-readable name for the key
        scopes: List of permission scopes (defaults to all)

    Returns:
        (success, message, raw_api_key) tuple.
        The raw key is only shown ONCE at creation time.
    """
    # Check user's tier allows API access
    tier = _get_user_tier(username)
    if tier not in TIER_RATE_LIMITS:
        return False, "API access requires Team or Enterprise plan", ""

    # Check key limit
    keys = _load_keys(username)
    active_keys = [k for k in keys if k.get("status") == "active"]
    max_keys = TIER_RATE_LIMITS[tier]["max_keys"]
    if len(active_keys) >= max_keys:
        return False, f"Maximum {max_keys} API keys allowed for {tier} plan", ""

    # Generate the key
    tier_prefix = "ent" if tier == "enterprise" else "team"
    raw_secret = secrets.token_hex(16)
    raw_key = f"tai_{tier_prefix}_{raw_secret}"

    # Store hash only (never store raw key)
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12] + "..."  # For display: tai_team_a1b2...

    key_record = {
        "id": secrets.token_hex(4),
        "name": name or f"Key {len(keys) + 1}",
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "scopes": scopes or list(SCOPES.keys()),
        "tier": tier,
        "status": "active",  # active / revoked
        "created_at": datetime.now().isoformat(),
        "last_used_at": None,
        "total_requests": 0,
        "revoked_at": None,
    }

    keys.append(key_record)
    _save_keys(username, keys)

    logger.info("API key created for %s (id=%s, name=%s)", username, key_record["id"], name)
    return True, "API key created successfully", raw_key


def validate_api_key(raw_key: str) -> tuple[bool, dict | str]:
    """
    Validate an API key and return its metadata.

    This is called on every API request to authenticate.

    Args:
        raw_key: The full API key string (tai_<tier>_<hex>)

    Returns:
        (True, key_metadata_dict) if valid
        (False, error_message) if invalid
    """
    if not raw_key or not raw_key.startswith("tai_"):
        return False, "Invalid API key format"

    key_hash = _hash_key(raw_key)

    # Search all users' keys (in production, use a global index/DB)
    # For JSON backend, we need to scan — acceptable for small scale

    from utils.storage import get_data_dir

    users_dir = get_data_dir() / "users"
    if not users_dir.exists():
        return False, "Invalid API key"

    for username_dir in users_dir.iterdir():
        if not username_dir.is_dir():
            continue
        username = username_dir.name
        keys = _load_keys(username)
        for key_record in keys:
            if key_record.get("key_hash") == key_hash:
                if key_record.get("status") != "active":
                    return False, "API key has been revoked"

                # Update last_used
                key_record["last_used_at"] = datetime.now().isoformat()
                key_record["total_requests"] = key_record.get("total_requests", 0) + 1
                _save_keys(username, keys)

                return True, {
                    "username": username,
                    "key_id": key_record["id"],
                    "key_name": key_record["name"],
                    "tier": key_record["tier"],
                    "scopes": key_record["scopes"],
                }

    return False, "Invalid API key"


def revoke_api_key(username: str, key_id: str) -> tuple[bool, str]:
    """
    Revoke (deactivate) an API key.

    Args:
        username: Owner of the key
        key_id: The key's internal ID

    Returns:
        (success, message) tuple
    """
    keys = _load_keys(username)
    for key_record in keys:
        if key_record["id"] == key_id:
            if key_record["status"] == "revoked":
                return False, "Key is already revoked"
            key_record["status"] = "revoked"
            key_record["revoked_at"] = datetime.now().isoformat()
            _save_keys(username, keys)
            logger.info("API key revoked: %s (user=%s)", key_id, username)
            return True, "API key revoked"
    return False, "Key not found"


def get_user_api_keys(username: str) -> list[dict]:
    """
    Get all API keys for a user (active and revoked).

    Returns list of key metadata (never includes the actual key/hash).
    """
    keys = _load_keys(username)
    # Return safe view (no hash)
    return [
        {
            "id": k["id"],
            "name": k["name"],
            "key_prefix": k["key_prefix"],
            "scopes": k["scopes"],
            "tier": k["tier"],
            "status": k["status"],
            "created_at": k["created_at"],
            "last_used_at": k.get("last_used_at"),
            "total_requests": k.get("total_requests", 0),
            "revoked_at": k.get("revoked_at"),
        }
        for k in keys
    ]


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def check_api_rate_limit(key_metadata: dict) -> tuple[bool, str]:
    """
    Check if an API request is within rate limits.

    Args:
        key_metadata: The dict returned by validate_api_key (contains tier, key_id)

    Returns:
        (allowed, message) tuple
    """
    tier = key_metadata.get("tier", "team")
    key_id = key_metadata.get("key_id", "unknown")
    limits = TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["team"])

    now = time.time()
    counters = _load_rate_counters()
    key_timestamps = _prune_rate_counters(counters, key_id, now)
    _save_rate_counters(counters)

    # Check hourly limit
    hour_ago = now - 3600
    hour_count = sum(1 for t in key_timestamps if t > hour_ago)
    if hour_count >= limits["requests_per_hour"]:
        return False, f"Hourly rate limit exceeded ({limits['requests_per_hour']}/hour)"

    # Check daily limit (if applicable)
    daily_limit = limits["requests_per_day"]
    if daily_limit is not None:
        day_count = len(key_timestamps)
        if day_count >= daily_limit:
            return False, f"Daily rate limit exceeded ({daily_limit}/day)"

    return True, "OK"


def record_api_usage(key_metadata: dict) -> None:
    """Record a successful API request for rate limiting."""
    key_id = key_metadata.get("key_id", "unknown")
    counters = _load_rate_counters()
    now = time.time()
    _prune_rate_counters(counters, key_id, now).append(now)
    _save_rate_counters(counters)


def get_api_usage_stats(username: str) -> dict:
    """
    Get API usage statistics for a user.

    Returns:
        Dict with total_requests, keys_active, keys_revoked, etc.
    """
    keys = _load_keys(username)
    active = [k for k in keys if k["status"] == "active"]
    revoked = [k for k in keys if k["status"] == "revoked"]

    total_requests = sum(k.get("total_requests", 0) for k in keys)

    # Per-key breakdown
    counters = _load_rate_counters()
    key_stats = []
    now = time.time()
    for k in active:
        key_id = k["id"]
        hour_count = sum(1 for t in counters.get(key_id, []) if t > now - 3600)
        key_stats.append({
            "id": k["id"],
            "name": k["name"],
            "requests_this_hour": hour_count,
            "total_requests": k.get("total_requests", 0),
            "last_used": k.get("last_used_at"),
        })

    tier = _get_user_tier(username)
    limits = TIER_RATE_LIMITS.get(tier, {})

    return {
        "tier": tier,
        "active_keys": len(active),
        "revoked_keys": len(revoked),
        "max_keys": limits.get("max_keys", 0),
        "total_requests_all_time": total_requests,
        "rate_limit_per_hour": limits.get("requests_per_hour", 0),
        "rate_limit_per_day": limits.get("requests_per_day", "unlimited"),
        "keys": key_stats,
    }


# ---------------------------------------------------------------------------
# Scope checking
# ---------------------------------------------------------------------------

def has_scope(key_metadata: dict, required_scope: str) -> bool:
    """Check if an API key has a required permission scope."""
    key_scopes = key_metadata.get("scopes", [])
    return required_scope in key_scopes


def require_scope(key_metadata: dict, scope: str) -> tuple[bool, str]:
    """
    Verify a key has the required scope, returning error if not.

    Args:
        key_metadata: Key metadata from validate_api_key
        scope: Required scope string

    Returns:
        (True, "OK") or (False, "Insufficient permissions: ...")
    """
    if has_scope(key_metadata, scope):
        return True, "OK"
    return False, f"Insufficient permissions: requires '{scope}' scope"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_keys(username: str) -> list[dict]:
    """Load API keys from user storage."""
    return load_user_json(username, _KEYS_FILE, default=[])


def _save_keys(username: str, keys: list[dict]) -> None:
    """Save API keys to user storage."""
    save_user_json(username, _KEYS_FILE, keys)


def _hash_key(raw_key: str) -> str:
    """Hash an API key for storage (SHA-256, irreversible)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _get_user_tier(username: str) -> str:
    """Get the user's subscription tier."""
    try:
        from utils.pricing import get_user_tier
        return get_user_tier(username)
    except Exception:
        return "free"
