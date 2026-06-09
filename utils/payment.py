"""
utils/payment.py
----------------
Stripe payment integration for tier upgrades.
Wraps stripe in try/except since it may not be installed locally.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from utils.pricing import get_user_tier, upgrade_user_tier
from utils.repositories import load_consumed_sessions, load_user, save_consumed_sessions
from utils.secrets import get_secret

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None  # type: ignore[assignment]
    STRIPE_AVAILABLE = False

_TIER_ORDER = {"free": 0, "pro": 1, "enterprise": 2}


def is_payment_configured() -> bool:
    """Return True only if STRIPE_SECRET_KEY and at least one price ID are set."""
    secret_key = get_secret("STRIPE_SECRET_KEY")
    if not secret_key:
        return False
    pro_price = get_secret("STRIPE_PRICE_ID_PRO")
    enterprise_price = get_secret("STRIPE_PRICE_ID_ENTERPRISE")
    if not pro_price and not enterprise_price:
        return False
    return True


def get_price_id(tier: str) -> str:
    """Return the Stripe price ID for a given tier."""
    if tier == "pro":
        return get_secret("STRIPE_PRICE_ID_PRO")
    if tier == "enterprise":
        return get_secret("STRIPE_PRICE_ID_ENTERPRISE")
    return ""


def create_checkout_session(username: str, target_tier: str) -> tuple[bool, str]:
    """Create a Stripe Checkout Session for tier upgrade."""
    from utils.email_gate import require_verified_email

    allowed, message = require_verified_email(username)
    if not allowed:
        return (False, message)
    if not STRIPE_AVAILABLE:
        return (False, "Stripe not installed")
    if not is_payment_configured():
        return (False, "Payment not configured")

    price_id = get_price_id(target_tier)
    if not price_id:
        return (False, f"No price configured for tier: {target_tier}")

    try:
        stripe.api_key = get_secret("STRIPE_SECRET_KEY")
        base_url = get_secret("APP_BASE_URL") or "https://localhost:8501"
        base_url = base_url.rstrip("/")
        session_params = {
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "mode": "payment",
            "metadata": {"username": username, "target_tier": target_tier},
            "client_reference_id": username,
            "success_url": f"{base_url}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base_url}/?payment=cancelled",
        }
        user = load_user(username) or {}
        customer_email = user.get("email", "").strip()
        if customer_email:
            session_params["customer_email"] = customer_email
        session = stripe.checkout.Session.create(**session_params)
        return (True, session.url)
    except Exception as e:
        return (False, str(e))


def verify_checkout_session(session_id: str) -> tuple[bool, dict]:
    """Return ``(True, metadata)`` only when Stripe reports a paid session."""
    if not STRIPE_AVAILABLE:
        return (False, {})
    try:
        stripe.api_key = get_secret("STRIPE_SECRET_KEY")
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            return (True, dict(session.metadata))
        return (False, {})
    except Exception:
        return (False, {})


def _tier_at_least(current_tier: str, target_tier: str) -> bool:
    """Return True when current_tier already includes target_tier access."""
    return _TIER_ORDER.get(current_tier, -1) >= _TIER_ORDER.get(target_tier, 999)


def complete_upgrade(username: str, session_id: str) -> tuple[bool, str]:
    """Complete a tier upgrade after payment verification."""
    from utils.email_gate import require_verified_email

    allowed, message = require_verified_email(username)
    if not allowed:
        return (False, message)

    is_paid, metadata = verify_checkout_session(session_id)
    if not is_paid:
        return (False, "Payment not verified")

    meta_username = metadata.get("username", "")
    target_tier = metadata.get("target_tier", "")

    if meta_username != username:
        return (False, "Username mismatch")
    if not target_tier:
        return (False, "No target tier in session metadata")

    consumed = load_consumed_sessions(username)
    if session_id in consumed:
        current_tier = get_user_tier(username)
        if _tier_at_least(current_tier, target_tier):
            return (True, f"Already upgraded to {current_tier}")
        return (False, "Session already consumed but tier is not active")

    success = upgrade_user_tier(username, target_tier)
    if success:
        consumed.append(session_id)
        save_consumed_sessions(username, consumed)
        return (True, f"Upgraded to {target_tier}")
    return (False, "Upgrade failed")


def _first_query_value(value: Any) -> str:
    """Return a normalized first value from Streamlit-style query params."""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value or "").strip()


def checkout_session_id_from_query(query_params: Mapping[str, Any]) -> str:
    """Extract a paid-checkout session ID from a Stripe success return URL."""
    payment_status = _first_query_value(query_params.get("payment")).lower()
    session_id = _first_query_value(query_params.get("session_id"))
    if payment_status != "success" or not session_id:
        return ""
    return session_id


def complete_upgrade_from_query(username: str, query_params: Mapping[str, Any]) -> tuple[bool, bool, str]:
    """Complete a Stripe upgrade from return query params.

    Returns ``(handled, success, message)``. ``handled`` is False when the
    current URL does not contain a Stripe success session.
    """
    session_id = checkout_session_id_from_query(query_params)
    if not session_id:
        return (False, False, "")
    success, message = complete_upgrade(username, session_id)
    return (True, success, message)
