"""Tests for repository helpers over the active database backend."""
from __future__ import annotations

from unittest.mock import Mock, patch


def test_user_subscription_round_trips_through_active_backend():
    from utils.repositories import (
        SUBSCRIPTION_COLLECTION,
        load_user_subscription,
        save_user_subscription,
    )

    db = Mock()
    db.load_user_data.return_value = {"stripe_customer_id": "cus_test_123"}

    with patch("utils.repositories.get_db", return_value=db):
        subscription = load_user_subscription("paiduser")
        save_user_subscription("paiduser", subscription)

    assert subscription == {"stripe_customer_id": "cus_test_123"}
    db.load_user_data.assert_called_once_with("paiduser", SUBSCRIPTION_COLLECTION, default={})
    db.save_user_data.assert_called_once_with("paiduser", SUBSCRIPTION_COLLECTION, subscription)


def test_user_subscription_returns_empty_dict_for_invalid_backend_shape():
    from utils.repositories import load_user_subscription

    db = Mock()
    db.load_user_data.return_value = []

    with patch("utils.repositories.get_db", return_value=db):
        assert load_user_subscription("paiduser") == {}


def test_password_reset_requests_round_trip_through_active_backend():
    from utils.repositories import (
        PASSWORD_RESET_REQUESTS_COLLECTION,
        load_password_reset_requests,
        save_password_reset_requests,
    )

    db = Mock()
    db.load_global_data.return_value = {"hashed-id": [1.0]}

    with patch("utils.repositories.get_db", return_value=db):
        requests = load_password_reset_requests()
        save_password_reset_requests(requests)

    assert requests == {"hashed-id": [1.0]}
    db.load_global_data.assert_called_once_with(PASSWORD_RESET_REQUESTS_COLLECTION, default={})
    db.save_global_data.assert_called_once_with(PASSWORD_RESET_REQUESTS_COLLECTION, requests)


def test_email_verification_requests_round_trip_through_active_backend():
    from utils.repositories import (
        EMAIL_VERIFICATION_REQUESTS_COLLECTION,
        load_email_verification_requests,
        save_email_verification_requests,
    )

    db = Mock()
    db.load_global_data.return_value = {"hashed-user": [1.0]}

    with patch("utils.repositories.get_db", return_value=db):
        requests = load_email_verification_requests()
        save_email_verification_requests(requests)

    assert requests == {"hashed-user": [1.0]}
    db.load_global_data.assert_called_once_with(EMAIL_VERIFICATION_REQUESTS_COLLECTION, default={})
    db.save_global_data.assert_called_once_with(EMAIL_VERIFICATION_REQUESTS_COLLECTION, requests)
