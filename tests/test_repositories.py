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


def test_save_user_calls_upsert_user_without_loading_all_users():
    from utils.repositories import save_user

    db = Mock()
    user = {"username": "alice", "tier": "pro"}
    with patch("utils.repositories.get_db", return_value=db):
        save_user("alice", user)

    db.upsert_user.assert_called_once_with("alice", user)
    db.get_all_users.assert_not_called()
    db.save_all_users.assert_not_called()


def test_customers_round_trip_per_user_backend():
    from utils.repositories import CUSTOMERS_COLLECTION, load_customers, save_customers

    db = Mock()
    db.load_user_data.return_value = [{"company": "Acme"}]
    with patch("utils.repositories.get_db", return_value=db):
        rows = load_customers("alice")
        save_customers("alice", rows)

    assert rows == [{"company": "Acme"}]
    db.load_user_data.assert_called_once_with("alice", CUSTOMERS_COLLECTION, default=[])
    db.save_user_data.assert_called_once_with("alice", CUSTOMERS_COLLECTION, rows)


def test_customers_round_trip_global_backend_for_shared_scope():
    from utils.repositories import CUSTOMERS_COLLECTION, load_customers, save_customers

    db = Mock()
    db.load_global_data.return_value = []
    with patch("utils.repositories.get_db", return_value=db):
        rows = load_customers(None)
        save_customers(None, [{"company": "Shared"}])

    assert rows == []
    db.load_global_data.assert_called_once_with(CUSTOMERS_COLLECTION, default=[])
    db.save_global_data.assert_called_once_with(CUSTOMERS_COLLECTION, [{"company": "Shared"}])


def test_campaign_results_and_tracking_use_repository_collections():
    from utils.repositories import (
        TRACKING_COLLECTION,
        campaign_results_collection,
        load_campaign_results,
        load_email_tracking,
        save_campaign_results,
        save_email_tracking,
    )

    db = Mock()
    db.load_user_data.return_value = [{"email": "a@example.com", "status": "sent"}]
    db.load_global_data.return_value = [{"tracking_id": "t1"}]
    with patch("utils.repositories.get_db", return_value=db):
        results = load_campaign_results("alice", "campaign-1")
        save_campaign_results("alice", "campaign-1", results)
        tracking = load_email_tracking()
        save_email_tracking(tracking)

    db.load_user_data.assert_called_once_with(
        "alice", campaign_results_collection("campaign-1"), default=[]
    )
    db.save_user_data.assert_called_once_with(
        "alice", campaign_results_collection("campaign-1"), results
    )
    db.load_global_data.assert_called_once_with(TRACKING_COLLECTION, default=[])
    db.save_global_data.assert_called_once_with(TRACKING_COLLECTION, tracking)
