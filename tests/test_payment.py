"""
tests/test_payment.py
Unit tests for utils/payment.py - Stripe payment integration.
"""
from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
_mock_st.secrets = {}
sys.modules["streamlit"] = _mock_st

_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv

import utils.payment  # noqa: E402
from utils.payment import (  # noqa: E402
    checkout_session_id_from_query,
    complete_upgrade,
    complete_upgrade_from_query,
    create_checkout_session,
    is_payment_configured,
    verify_checkout_session,
)


class TestPayment:
    """Tests for utils/payment.py Stripe payment functions."""

    def _setup(self):
        _mock_st.session_state.clear()

    def test_stripe_not_available(self):
        self._setup()
        with patch.object(utils.payment, "STRIPE_AVAILABLE", False), \
             patch("utils.email_gate.require_verified_email", return_value=(True, "")):
            success, msg = create_checkout_session("testuser", "pro")
            assert success is False
            assert "Stripe not installed" in msg

    def test_create_checkout_session_requires_verified_email(self):
        self._setup()
        with patch("utils.email_gate.require_verified_email", return_value=(False, "verify first")):
            success, msg = create_checkout_session("testuser", "pro")
            assert success is False
            assert msg == "verify first"

    def test_is_payment_configured_false_when_not_set(self):
        self._setup()
        with patch.object(utils.payment, "get_secret", return_value=""):
            assert is_payment_configured() is False

    def test_is_payment_configured_true_when_set(self):
        self._setup()

        def mock_get_secret(key, default=""):
            secrets = {
                "STRIPE_SECRET_KEY": "sk_test_abc123",
                "STRIPE_PRICE_ID_PRO": "price_pro_123",
                "STRIPE_PRICE_ID_ENTERPRISE": "price_ent_456",
            }
            return secrets.get(key, default)

        with patch.object(utils.payment, "get_secret", side_effect=mock_get_secret):
            assert is_payment_configured() is True

    def test_create_checkout_session_not_configured(self):
        self._setup()
        with patch.object(utils.payment, "STRIPE_AVAILABLE", True), \
             patch.object(utils.payment, "is_payment_configured", return_value=False), \
             patch("utils.email_gate.require_verified_email", return_value=(True, "")):
            success, msg = create_checkout_session("testuser", "pro")
            assert success is False
            assert "not configured" in msg

    def test_create_checkout_session_success(self):
        self._setup()
        mock_stripe = MagicMock()
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
        mock_stripe.checkout.Session.create.return_value = mock_session

        def mock_get_secret(key, default=""):
            secrets = {
                "STRIPE_SECRET_KEY": "sk_test_abc123",
                "STRIPE_PRICE_ID_PRO": "price_pro_123",
                "STRIPE_PRICE_ID_ENTERPRISE": "price_ent_456",
            }
            return secrets.get(key, default)

        with patch.object(utils.payment, "STRIPE_AVAILABLE", True), \
             patch.object(utils.payment, "stripe", mock_stripe), \
             patch.object(utils.payment, "get_secret", side_effect=mock_get_secret), \
             patch("utils.email_gate.require_verified_email", return_value=(True, "")):
            success, url = create_checkout_session("testuser", "pro")
            assert success is True
            assert "checkout.stripe.com" in url
            mock_stripe.checkout.Session.create.assert_called_once()

    def test_verify_checkout_session_paid(self):
        self._setup()
        mock_stripe = MagicMock()
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.metadata = {"username": "testuser", "target_tier": "pro"}
        mock_stripe.checkout.Session.retrieve.return_value = mock_session

        with patch.object(utils.payment, "STRIPE_AVAILABLE", True), \
             patch.object(utils.payment, "stripe", mock_stripe), \
             patch.object(utils.payment, "get_secret", return_value="sk_test_abc123"):
            is_paid, metadata = verify_checkout_session("cs_test_123")
            assert is_paid is True
            assert metadata["username"] == "testuser"
            assert metadata["target_tier"] == "pro"

    def test_verify_checkout_session_unpaid(self):
        self._setup()
        mock_stripe = MagicMock()
        mock_session = MagicMock()
        mock_session.payment_status = "unpaid"
        mock_stripe.checkout.Session.retrieve.return_value = mock_session

        with patch.object(utils.payment, "STRIPE_AVAILABLE", True), \
             patch.object(utils.payment, "stripe", mock_stripe), \
             patch.object(utils.payment, "get_secret", return_value="sk_test_abc123"):
            is_paid, metadata = verify_checkout_session("cs_test_123")
            assert is_paid is False
            assert metadata == {}

    def test_complete_upgrade_requires_verified_email(self):
        self._setup()
        with patch("utils.email_gate.require_verified_email", return_value=(False, "verify first")):
            success, msg = complete_upgrade("testuser", "cs_test_123")
            assert success is False
            assert msg == "verify first"

    def test_complete_upgrade_success(self):
        self._setup()
        with patch.object(utils.payment, "verify_checkout_session", return_value=(True, {"username": "testuser", "target_tier": "pro"})), \
             patch.object(utils.payment, "upgrade_user_tier", return_value=True) as mock_upgrade, \
             patch.object(utils.payment, "load_consumed_sessions", return_value=[]), \
             patch.object(utils.payment, "save_consumed_sessions") as mock_save, \
             patch("utils.email_gate.require_verified_email", return_value=(True, "")):
            success, msg = complete_upgrade("testuser", "cs_test_123")
            assert success is True
            assert "pro" in msg.lower() or "Pro" in msg
            mock_upgrade.assert_called_once_with("testuser", "pro")
            mock_save.assert_called_once_with("testuser", ["cs_test_123"])

    def test_complete_upgrade_username_mismatch(self):
        self._setup()
        with patch.object(utils.payment, "verify_checkout_session", return_value=(True, {"username": "otheruser", "target_tier": "pro"})), \
             patch("utils.email_gate.require_verified_email", return_value=(True, "")):
            success, msg = complete_upgrade("testuser", "cs_test_123")
            assert success is False
            assert "mismatch" in msg.lower()

    def test_checkout_session_id_from_query_accepts_streamlit_values(self):
        assert checkout_session_id_from_query({"payment": "success", "session_id": "cs_test_123"}) == "cs_test_123"
        assert checkout_session_id_from_query({"payment": ["success"], "session_id": ["cs_test_456"]}) == "cs_test_456"

    def test_checkout_session_id_from_query_ignores_non_success_returns(self):
        assert checkout_session_id_from_query({"payment": "cancelled", "session_id": "cs_test_123"}) == ""
        assert checkout_session_id_from_query({"payment": "success"}) == ""

    def test_complete_upgrade_from_query_only_handles_success_session(self):
        with patch.object(utils.payment, "complete_upgrade", return_value=(True, "Upgraded to pro")) as complete:
            handled, success, msg = complete_upgrade_from_query(
                "testuser",
                {"payment": "success", "session_id": "cs_test_123"},
            )

        assert handled is True
        assert success is True
        assert msg == "Upgraded to pro"
        complete.assert_called_once_with("testuser", "cs_test_123")

        handled, success, msg = complete_upgrade_from_query("testuser", {"payment": "cancelled"})
        assert handled is False
        assert success is False
        assert msg == ""


if __name__ == "__main__":
    import traceback
    cls = TestPayment()
    methods = [m for m in dir(cls) if m.startswith("test_")]
    passed = failed = 0
    for m in sorted(methods):
        try:
            getattr(cls, m)()
            passed += 1
            print(f"  PASS: {m}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {m}: {e}")
            traceback.print_exc()
    print(f"\nResults: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
