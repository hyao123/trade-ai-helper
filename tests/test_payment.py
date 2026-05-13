"""
tests/test_payment.py
Unit tests for utils/payment.py - Stripe payment integration.
"""
from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, patch

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that use it
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
_mock_st.secrets = {}
sys.modules["streamlit"] = _mock_st

# Mock dotenv before importing modules that use it (not available in test env)
_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv

# Import the module under test (must be after mocks are set up)
import utils.payment  # noqa: E402
from utils.payment import (
    complete_upgrade,
    create_checkout_session,
    is_payment_configured,
    verify_checkout_session,
)


class TestPayment:
    """Tests for utils/payment.py Stripe payment functions."""

    def _setup(self):
        """Reset mock state."""
        _mock_st.session_state.clear()

    def test_stripe_not_available(self):
        """When STRIPE_AVAILABLE is False, create_checkout_session returns error."""
        self._setup()
        with patch.object(utils.payment, "STRIPE_AVAILABLE", False):
            success, msg = create_checkout_session("testuser", "pro")
            assert success is False
            assert "Stripe not installed" in msg

    def test_is_payment_configured_false_when_not_set(self):
        """is_payment_configured returns False when secrets are not set."""
        self._setup()
        with patch.object(utils.payment, "get_secret", return_value=""):
            result = is_payment_configured()
            assert result is False

    def test_is_payment_configured_true_when_set(self):
        """is_payment_configured returns True when key and at least one price ID are set."""
        self._setup()

        def mock_get_secret(key, default=""):
            secrets = {
                "STRIPE_SECRET_KEY": "sk_test_abc123",
                "STRIPE_PRICE_ID_PRO": "price_pro_123",
                "STRIPE_PRICE_ID_ENTERPRISE": "price_ent_456",
            }
            return secrets.get(key, default)

        with patch.object(utils.payment, "get_secret", side_effect=mock_get_secret):
            result = is_payment_configured()
            assert result is True

    def test_create_checkout_session_not_configured(self):
        """When payment not configured, returns (False, error)."""
        self._setup()
        with patch.object(utils.payment, "STRIPE_AVAILABLE", True), \
             patch.object(utils.payment, "is_payment_configured", return_value=False):
            success, msg = create_checkout_session("testuser", "pro")
            assert success is False
            assert "not configured" in msg

    def test_create_checkout_session_success(self):
        """With mocked stripe, create_checkout_session returns (True, url)."""
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
             patch.object(utils.payment, "get_secret", side_effect=mock_get_secret):
            success, url = create_checkout_session("testuser", "pro")
            assert success is True
            assert "checkout.stripe.com" in url
            mock_stripe.checkout.Session.create.assert_called_once()

    def test_verify_checkout_session_paid(self):
        """Mocked stripe returns paid session - verify returns (True, metadata)."""
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
        """Mocked stripe returns unpaid session - verify returns (False, {})."""
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

    def test_complete_upgrade_success(self):
        """complete_upgrade calls upgrade_user_tier when payment verified."""
        self._setup()
        with patch.object(utils.payment, "verify_checkout_session", return_value=(True, {"username": "testuser", "target_tier": "pro"})), \
             patch.object(utils.payment, "upgrade_user_tier", return_value=True) as mock_upgrade, \
             patch.object(utils.payment, "load_user_json", return_value=[]), \
             patch.object(utils.payment, "save_user_json") as mock_save:
            success, msg = complete_upgrade("testuser", "cs_test_123")
            assert success is True
            assert "pro" in msg.lower() or "Pro" in msg
            mock_upgrade.assert_called_once_with("testuser", "pro")
            mock_save.assert_called_once_with("testuser", "consumed_sessions.json", ["cs_test_123"])

    def test_complete_upgrade_username_mismatch(self):
        """complete_upgrade fails if metadata username doesn't match."""
        self._setup()
        with patch.object(utils.payment, "verify_checkout_session", return_value=(True, {"username": "otheruser", "target_tier": "pro"})):
            success, msg = complete_upgrade("testuser", "cs_test_123")
            assert success is False
            assert "mismatch" in msg.lower()


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
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
