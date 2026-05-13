"""
utils/payment.py
----------------
Stripe payment integration for tier upgrades.
Wraps stripe in try/except since it may not be installed locally.
"""
from __future__ import annotations

from utils.pricing import upgrade_user_tier
from utils.secrets import get_secret
from utils.storage import load_user_json, save_user_json

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None  # type: ignore[assignment]
    STRIPE_AVAILABLE = False


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
    elif tier == "enterprise":
        return get_secret("STRIPE_PRICE_ID_ENTERPRISE")
    return ""


def create_checkout_session(username: str, target_tier: str) -> tuple[bool, str]:
    """
    Create a Stripe Checkout Session for tier upgrade.

    Returns:
        (True, session_url) on success.
        (False, error_message) on failure.
    """
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
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            metadata={"username": username, "target_tier": target_tier},
            success_url=f"{base_url}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/?payment=cancelled",
        )
        return (True, session.url)
    except Exception as e:
        return (False, str(e))


def verify_checkout_session(session_id: str) -> tuple[bool, dict]:
    """
    Verify a Stripe Checkout Session payment status.

    Returns:
        (True, metadata) if payment_status is 'paid'.
        (False, {}) otherwise.
    """
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


def complete_upgrade(username: str, session_id: str) -> tuple[bool, str]:
    """
    Complete a tier upgrade after payment verification.

    Verifies the checkout session, checks username matches metadata,
    checks that the session has not already been consumed,
    and calls upgrade_user_tier.

    Returns:
        (True, success_message) on success.
        (False, error_message) on failure.
    """
    is_paid, metadata = verify_checkout_session(session_id)
    if not is_paid:
        return (False, "Payment not verified")

    meta_username = metadata.get("username", "")
    target_tier = metadata.get("target_tier", "")

    if meta_username != username:
        return (False, "Username mismatch")

    if not target_tier:
        return (False, "No target tier in session metadata")

    # Check if session was already consumed (prevent replay)
    consumed = load_user_json(username, "consumed_sessions.json", default=[])
    if session_id in consumed:
        return (False, "Session already consumed")

    success = upgrade_user_tier(username, target_tier)
    if success:
        # Mark session as consumed
        consumed.append(session_id)
        save_user_json(username, "consumed_sessions.json", consumed)
        return (True, f"Upgraded to {target_tier}")
    return (False, "Upgrade failed")
