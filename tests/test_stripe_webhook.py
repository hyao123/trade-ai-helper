"""Tests for Stripe webhook lifecycle handling."""
from __future__ import annotations

from unittest.mock import patch


def _checkout_session(session_id: str = "cs_test_123") -> dict:
    return {
        "id": session_id,
        "metadata": {"username": "paiduser", "target_tier": "pro"},
        "customer": "cus_test_123",
        "subscription": "sub_test_123",
        "amount_total": 2900,
    }


def test_checkout_completed_records_consumed_session_after_upgrade():
    from utils.stripe_webhook import _handle_checkout_completed

    with patch("utils.stripe_webhook.load_consumed_sessions", return_value=[]), \
         patch("utils.stripe_webhook.save_consumed_sessions") as save_consumed, \
         patch("utils.stripe_webhook.upgrade_user_tier", return_value=True) as upgrade, \
         patch("utils.stripe_webhook._save_subscription_info") as save_subscription, \
         patch("utils.stripe_webhook.track_event") as track, \
         patch("utils.stripe_webhook.audit_event") as audit:
        success, message = _handle_checkout_completed(_checkout_session())

    assert success is True
    assert "Upgraded paiduser" in message
    upgrade.assert_called_once_with("paiduser", "pro")
    save_subscription.assert_called_once()
    save_consumed.assert_called_once_with("paiduser", ["cs_test_123"])
    track.assert_called_once()
    audit.assert_called_once()
    assert audit.call_args.args[:2] == ("stripe_checkout_completed", "success")
    assert audit.call_args.kwargs["user_id"] == "paiduser"


def test_checkout_completed_duplicate_session_is_idempotent():
    from utils.stripe_webhook import _handle_checkout_completed

    with patch("utils.stripe_webhook.load_consumed_sessions", return_value=["cs_test_123"]), \
         patch("utils.stripe_webhook.save_consumed_sessions") as save_consumed, \
         patch("utils.stripe_webhook.upgrade_user_tier") as upgrade, \
         patch("utils.stripe_webhook._save_subscription_info") as save_subscription, \
         patch("utils.stripe_webhook.track_event") as track, \
         patch("utils.stripe_webhook.audit_event") as audit:
        success, message = _handle_checkout_completed(_checkout_session())

    assert success is True
    assert "already processed" in message
    upgrade.assert_not_called()
    save_subscription.assert_not_called()
    save_consumed.assert_not_called()
    track.assert_not_called()
    audit.assert_called_once()
    assert audit.call_args.args[:2] == ("stripe_checkout_completed", "duplicate")


def test_checkout_completed_failed_upgrade_does_not_consume_session():
    from utils.stripe_webhook import _handle_checkout_completed

    with patch("utils.stripe_webhook.load_consumed_sessions", return_value=[]), \
         patch("utils.stripe_webhook.save_consumed_sessions") as save_consumed, \
         patch("utils.stripe_webhook.upgrade_user_tier", return_value=False), \
         patch("utils.stripe_webhook._save_subscription_info") as save_subscription, \
         patch("utils.stripe_webhook.track_event") as track, \
         patch("utils.stripe_webhook.audit_event") as audit:
        success, message = _handle_checkout_completed(_checkout_session())

    assert success is False
    assert "Upgrade failed" in message
    save_subscription.assert_not_called()
    save_consumed.assert_not_called()
    track.assert_not_called()
    audit.assert_called_once()
    assert audit.call_args.args[:2] == ("stripe_checkout_completed", "upgrade_failed")


def test_subscription_info_uses_repository_backend():
    from utils.stripe_webhook import _save_subscription_info

    info = {"stripe_customer_id": "cus_test_123", "tier": "pro"}
    with patch("utils.stripe_webhook.save_user_subscription") as save_subscription:
        _save_subscription_info("paiduser", info)

    save_subscription.assert_called_once_with("paiduser", info)


def test_find_username_by_customer_id_uses_repository_backend():
    from utils.stripe_webhook import _find_username_by_customer_id

    def load_subscription(username: str) -> dict:
        return {
            "otheruser": {"stripe_customer_id": "cus_other"},
            "paiduser": {"stripe_customer_id": "cus_test_123"},
        }[username]

    with patch("utils.stripe_webhook.load_users", return_value={"otheruser": {}, "paiduser": {}}), \
         patch("utils.stripe_webhook.load_user_subscription", side_effect=load_subscription):
        username = _find_username_by_customer_id("cus_test_123")

    assert username == "paiduser"
