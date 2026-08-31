"""
utils/stripe_webhook.py
-----------------------
Stripe webhook handling for subscription lifecycle events.
Handles:
  - checkout.session.completed: Upgrade user tier after payment
  - customer.subscription.updated: Plan changes
  - customer.subscription.deleted: Downgrade to free
  - invoice.payment_failed: Notify user

Integration:
  In production, expose this via a FastAPI/Flask endpoint.
  For Streamlit Cloud, use the verify_and_process() function
  called from a dedicated webhook receiver.

Requires:
  STRIPE_SECRET_KEY: Stripe API key
  STRIPE_WEBHOOK_SECRET: Webhook endpoint signing secret
"""
from __future__ import annotations

from utils.analytics import track_event
from utils.logger import get_logger
from utils.notifications import notify
from utils.pricing import upgrade_user_tier
from utils.repositories import (
    load_consumed_sessions,
    load_user_subscription,
    load_users,
    save_consumed_sessions,
    save_user_subscription,
)
from utils.secrets import get_secret
from utils.security_audit import audit_event

logger = get_logger("stripe_webhook")


def verify_and_process(payload: bytes, signature: str) -> tuple[bool, str]:
    """
    Verify a Stripe webhook signature and process the event.

    Args:
        payload: Raw request body bytes
        signature: Stripe-Signature header value

    Returns:
        (success, message) tuple
    """
    try:
        import stripe
    except ImportError:
        return False, "Stripe not installed"

    webhook_secret = get_secret("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        return False, "STRIPE_WEBHOOK_SECRET not configured"

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook signature verification failed")
        audit_event("stripe_webhook_verification_failed", "invalid_signature", severity="warning")
        return False, "Invalid signature"
    except Exception as e:
        logger.error("Webhook parsing failed: %s", e)
        audit_event("stripe_webhook_parse_failed", "parse_error", severity="warning")
        return False, f"Parse error: {e}"

    # Route to handler
    event_type = event["type"]
    logger.info("Processing webhook: %s", event_type)

    handlers = {
        "checkout.session.completed": _handle_checkout_completed,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "invoice.payment_failed": _handle_payment_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        return handler(event["data"]["object"])
    else:
        logger.debug("Unhandled event type: %s", event_type)
        return True, f"Ignored event: {event_type}"


def _handle_checkout_completed(session: dict) -> tuple[bool, str]:
    """
    Handle successful checkout - upgrade user tier.

    Expected metadata on the session:
      - username: the app username to upgrade
      - target_tier: 'pro' or 'team'
    """
    metadata = session.get("metadata", {})
    username = metadata.get("username") or session.get("client_reference_id")
    target_tier = metadata.get("target_tier")
    session_id = session.get("id", "")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not username or not target_tier:
        logger.warning("Checkout completed but missing metadata: %s", metadata)
        audit_event(
            "stripe_checkout_completed",
            "missing_metadata",
            severity="warning",
            metadata={"has_username": bool(username), "has_target_tier": bool(target_tier)},
        )
        return False, "Missing username or target_tier in metadata"

    consumed_sessions = load_consumed_sessions(username)
    if session_id and session_id in consumed_sessions:
        logger.info("Duplicate checkout webhook ignored: session=%s user=%s", session_id, username)
        audit_event(
            "stripe_checkout_completed",
            "duplicate",
            user_id=username,
            metadata={"target_tier": target_tier, "session_id": session_id},
        )
        return True, f"Checkout session already processed for {username}"

    # Upgrade the user
    success = upgrade_user_tier(username, target_tier)
    if not success:
        logger.error("Failed to upgrade user %s to %s", username, target_tier)
        audit_event(
            "stripe_checkout_completed",
            "upgrade_failed",
            user_id=username,
            severity="warning",
            metadata={"target_tier": target_tier, "session_id": session_id},
        )
        return False, f"Upgrade failed for {username}"

    # Store subscription info for future management
    _save_subscription_info(username, {
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "tier": target_tier,
        "status": "active",
        "checkout_session_id": session_id,
    })

    if session_id:
        consumed_sessions.append(session_id)
        save_consumed_sessions(username, consumed_sessions)

    track_event("subscription_created", {
        "username": username,
        "tier": target_tier,
        "amount": session.get("amount_total", 0) / 100,
    })

    logger.info("User %s upgraded to %s (subscription=%s)", username, target_tier, subscription_id)
    audit_event(
        "stripe_checkout_completed",
        "success",
        user_id=username,
        metadata={"target_tier": target_tier, "session_id": session_id},
    )
    try:
        plan_display = {"pro": "Pro", "team": "Team", "enterprise": "Enterprise"}.get(target_tier, target_tier)
        notify(username, "payment_success", plan=plan_display)
    except Exception as exc:  # noqa: BLE001 - notification failure must not break webhook ack
        logger.error("Checkout notification error for %s: %s", username, exc)
    return True, f"Upgraded {username} to {target_tier}"


def _handle_subscription_updated(subscription: dict) -> tuple[bool, str]:
    """Handle subscription plan changes (upgrade/downgrade)."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")

    username = _find_username_by_customer_id(customer_id)
    if not username:
        logger.warning("No user found for customer %s", customer_id)
        audit_event("stripe_subscription_updated", "unknown_customer", severity="warning")
        return True, "No matching user"

    # Determine new tier from the price
    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        new_tier = _price_id_to_tier(price_id)
        if new_tier and status == "active":
            upgrade_user_tier(username, new_tier)
            track_event("subscription_updated", {"username": username, "tier": new_tier})
            logger.info("Subscription updated: %s -> %s", username, new_tier)
            audit_event(
                "stripe_subscription_updated",
                "success",
                user_id=username,
                metadata={"new_tier": new_tier, "status": status},
            )

    return True, "Subscription updated"


def _handle_subscription_deleted(subscription: dict) -> tuple[bool, str]:
    """Handle subscription cancellation - downgrade to free."""
    customer_id = subscription.get("customer")
    username = _find_username_by_customer_id(customer_id)

    if not username:
        audit_event("stripe_subscription_deleted", "unknown_customer", severity="warning")
        return True, "No matching user"

    upgrade_user_tier(username, "free")
    track_event("subscription_cancelled", {"username": username})
    logger.info("Subscription cancelled, user %s downgraded to free", username)
    audit_event("stripe_subscription_deleted", "success", user_id=username, metadata={"new_tier": "free"})
    return True, f"Downgraded {username} to free"


def _handle_payment_failed(invoice: dict) -> tuple[bool, str]:
    """Handle failed payment - notify the user and record the event."""
    customer_id = invoice.get("customer")
    username = _find_username_by_customer_id(customer_id)

    if username:
        track_event("payment_failed", {"username": username})
        logger.warning("Payment failed for user %s", username)
        audit_event("stripe_payment_failed", "recorded", user_id=username, severity="warning")
        try:
            notify(
                username,
                "payment_failed",
                data={"invoice_id": invoice.get("id", ""), "customer_id": customer_id},
            )
        except Exception as exc:  # noqa: BLE001 - notification failure must not break webhook ack
            logger.error("Payment-failed notification error for %s: %s", username, exc)

    return True, "Payment failure recorded"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_subscription_info(username: str, info: dict) -> None:
    """Save Stripe subscription info to user's data."""
    save_user_subscription(username, info)


def _find_username_by_customer_id(customer_id: str) -> str | None:
    """Look up username by Stripe customer ID."""
    if not customer_id:
        return None

    users = load_users()
    for username, _data in users.items():
        sub_info = load_user_subscription(username)
        if sub_info.get("stripe_customer_id") == customer_id:
            return username
    return None


def _price_id_to_tier(price_id: str) -> str | None:
    """Map a Stripe price ID to our tier name."""
    pro_price = get_secret("STRIPE_PRICE_ID_PRO")
    team_price = get_secret("STRIPE_PRICE_ID_TEAM")
    enterprise_price = get_secret("STRIPE_PRICE_ID_ENTERPRISE")

    if price_id == pro_price:
        return "pro"
    if price_id == team_price:
        return "team"
    if price_id == enterprise_price:
        return "enterprise"
    return None


def create_subscription_checkout(
    username: str,
    target_tier: str,
    email: str = "",
) -> tuple[bool, str]:
    """
    Create a Stripe Checkout Session for subscription-based billing.

    Returns:
        (True, checkout_url) on success
        (False, error_message) on failure
    """
    try:
        import stripe
    except ImportError:
        return False, "Stripe not installed"

    secret_key = get_secret("STRIPE_SECRET_KEY")
    if not secret_key:
        return False, "Payment not configured"

    stripe.api_key = secret_key

    # Get price ID for the target tier
    price_id_map = {
        "pro": get_secret("STRIPE_PRICE_ID_PRO"),
        "team": get_secret("STRIPE_PRICE_ID_TEAM"),
        "enterprise": get_secret("STRIPE_PRICE_ID_ENTERPRISE"),
    }
    price_id = price_id_map.get(target_tier)
    if not price_id:
        return False, f"No price configured for tier: {target_tier}"

    base_url = get_secret("APP_BASE_URL") or "https://localhost:8501"
    base_url = base_url.rstrip("/")

    try:
        session_params = {
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "mode": "subscription",
            "metadata": {"username": username, "target_tier": target_tier},
            "client_reference_id": username,
            "success_url": f"{base_url}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base_url}/?payment=cancelled",
        }
        if email:
            session_params["customer_email"] = email

        session = stripe.checkout.Session.create(**session_params)
        track_event("checkout_started", {"username": username, "tier": target_tier})
        return True, session.url
    except Exception as e:
        logger.error("Stripe checkout creation failed: %s", e)
        return False, str(e)
