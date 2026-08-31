"""Tests for Stripe webhook user notifications."""
from __future__ import annotations

from unittest.mock import patch


def test_payment_failed_notifies_user():
    """A failed payment must notify the matched user via the notification pipeline."""
    from utils import stripe_webhook

    with patch.object(stripe_webhook, "_find_username_by_customer_id", return_value="bob"), \
         patch("utils.stripe_webhook.notify", return_value="n1") as mock_notify, \
         patch("utils.stripe_webhook.track_event"), \
         patch("utils.stripe_webhook.audit_event"), \
         patch("utils.stripe_webhook.logger"):
        ok, msg = stripe_webhook._handle_payment_failed({"customer": "cus_xyz", "id": "in_1"})

    assert ok is True
    mock_notify.assert_called_once()
    args, kwargs = mock_notify.call_args
    assert args[0] == "bob"
    assert args[1] == "payment_failed"


def test_payment_failed_no_notify_for_unknown_customer():
    """No notification when the Stripe customer cannot be mapped to a user."""
    from utils import stripe_webhook

    with patch.object(stripe_webhook, "_find_username_by_customer_id", return_value=None), \
         patch("utils.stripe_webhook.notify") as mock_notify, \
         patch("utils.stripe_webhook.track_event"), \
         patch("utils.stripe_webhook.audit_event"), \
         patch("utils.stripe_webhook.logger"):
        ok, msg = stripe_webhook._handle_payment_failed({"customer": "cus_unknown", "id": "in_2"})

    assert ok is True
    mock_notify.assert_not_called()


def test_checkout_completed_notifies_payment_success():
    """A successful checkout must notify payment_success with the activated plan."""
    from utils import stripe_webhook

    session = {
        "id": "cs_test_1",
        "customer": "cus_bob",
        "subscription": "sub_1",
        "metadata": {"username": "bob", "target_tier": "pro"},
        "amount_total": 19900,
    }

    with patch("utils.stripe_webhook.load_consumed_sessions", return_value=[]), \
         patch("utils.stripe_webhook.upgrade_user_tier", return_value=True), \
         patch("utils.stripe_webhook._save_subscription_info"), \
         patch("utils.stripe_webhook.save_consumed_sessions"), \
         patch("utils.stripe_webhook.notify", return_value="n2") as mock_notify, \
         patch("utils.stripe_webhook.track_event"), \
         patch("utils.stripe_webhook.audit_event"), \
         patch("utils.stripe_webhook.logger"):
        ok, msg = stripe_webhook._handle_checkout_completed(session)

    assert ok is True
    mock_notify.assert_called_once()
    args, kwargs = mock_notify.call_args
    assert args[:2] == ("bob", "payment_success")
    assert kwargs.get("plan") == "Pro"