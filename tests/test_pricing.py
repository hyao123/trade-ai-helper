"""
tests/test_pricing.py
Unit tests for utils/pricing.py - tiered pricing and usage tracking.
"""
from __future__ import annotations

import sys
import os
import types
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from datetime import date, timedelta

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that use it
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st


class TestPricing:
    """Tests for utils/pricing.py pricing and usage functions."""

    def _setup(self):
        """Reset mock state and create auto-cleaning temp dir."""
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def _create_user(self, tmp_dir: Path, username: str, tier: str = "free"):
        """Helper: create a user entry in users_db.json."""
        db_path = tmp_dir / "users_db.json"
        users = {}
        if db_path.exists():
            with open(db_path, encoding="utf-8") as f:
                users = json.load(f)
        users[username] = {
            "username": username,
            "email": "",
            "password_hash": "fakehash",
            "tier": tier,
            "created_at": "2026-01-01 00:00",
        }
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(users, f)
        # Create user data dir
        user_dir = tmp_dir / "users" / username
        user_dir.mkdir(parents=True, exist_ok=True)

    def test_get_daily_usage_returns_zero_for_new_user(self):
        """get_daily_usage returns 0 when no usage.json exists."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_daily_usage
                result = get_daily_usage("newuser123")
                assert result == 0

    def test_increment_usage_increments_count(self):
        """increment_usage increments the daily count correctly."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "testuser", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import increment_usage, get_daily_usage
                ok, msg = increment_usage("testuser")
                assert ok is True
                assert msg == ""
                assert get_daily_usage("testuser") == 1

                ok2, msg2 = increment_usage("testuser")
                assert ok2 is True
                assert get_daily_usage("testuser") == 2

    def test_increment_usage_returns_false_when_limit_exceeded(self):
        """increment_usage returns (False, error) when daily limit is hit."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "freeuser", "free")
            # Write usage.json with count at the limit (20)
            user_dir = tmp_dir / "users" / "freeuser"
            user_dir.mkdir(parents=True, exist_ok=True)
            usage = {"date": date.today().isoformat(), "count": 20}
            with open(user_dir / "usage.json", "w", encoding="utf-8") as f:
                json.dump(usage, f)

            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import increment_usage
                ok, msg = increment_usage("freeuser")
                assert ok is False
                assert "\u4e0a\u9650" in msg

    def test_usage_resets_on_new_day(self):
        """Usage count resets to 0 when date changes."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "dayuser", "free")
            # Write usage.json with yesterday's date
            user_dir = tmp_dir / "users" / "dayuser"
            user_dir.mkdir(parents=True, exist_ok=True)
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            usage = {"date": yesterday, "count": 15}
            with open(user_dir / "usage.json", "w", encoding="utf-8") as f:
                json.dump(usage, f)

            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_daily_usage
                result = get_daily_usage("dayuser")
                assert result == 0

    def test_check_feature_access_free_tier(self):
        """Free tier only has 'basic' feature access."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "freeuser2", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import check_feature_access
                assert check_feature_access("freeuser2", "basic") is True
                assert check_feature_access("freeuser2", "logo_upload") is False
                assert check_feature_access("freeuser2", "data_export") is False
                assert check_feature_access("freeuser2", "priority_support") is False

    def test_check_feature_access_pro_tier(self):
        """Pro tier has basic, logo_upload, and data_export."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "prouser", "pro")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import check_feature_access
                assert check_feature_access("prouser", "basic") is True
                assert check_feature_access("prouser", "logo_upload") is True
                assert check_feature_access("prouser", "data_export") is True
                assert check_feature_access("prouser", "priority_support") is False

    def test_check_feature_access_enterprise_tier(self):
        """Enterprise tier has all features."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "entuser", "enterprise")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import check_feature_access
                assert check_feature_access("entuser", "basic") is True
                assert check_feature_access("entuser", "logo_upload") is True
                assert check_feature_access("entuser", "data_export") is True
                assert check_feature_access("entuser", "priority_support") is True

    def test_enterprise_unlimited_daily_access(self):
        """Enterprise tier is never blocked by daily limit."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "entuser2", "enterprise")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import increment_usage
                # Increment many times - should never be blocked
                for i in range(50):
                    ok, msg = increment_usage("entuser2")
                    assert ok is True, f"Failed on iteration {i}: {msg}"
                    assert msg == ""

    def test_upgrade_user_tier(self):
        """upgrade_user_tier updates the tier in users_db.json."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "upgradeuser", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import upgrade_user_tier, get_user_tier
                assert get_user_tier("upgradeuser") == "free"
                result = upgrade_user_tier("upgradeuser", "pro")
                assert result is True
                assert get_user_tier("upgradeuser") == "pro"

    def test_upgrade_user_tier_invalid_tier(self):
        """upgrade_user_tier returns False for invalid tier."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "badtier", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import upgrade_user_tier
                result = upgrade_user_tier("badtier", "platinum")
                assert result is False

    def test_upgrade_user_tier_nonexistent_user(self):
        """upgrade_user_tier returns False for nonexistent user."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import upgrade_user_tier
                result = upgrade_user_tier("ghost", "pro")
                assert result is False

    def test_get_usage_display_free(self):
        """get_usage_display returns correct format for free tier."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "displayuser", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_usage_display, increment_usage
                display = get_usage_display("displayuser")
                assert display == "0/20"
                increment_usage("displayuser")
                display = get_usage_display("displayuser")
                assert display == "1/20"

    def test_get_usage_display_enterprise(self):
        """get_usage_display shows unlimited for enterprise."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "entdisplay", "enterprise")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_usage_display
                display = get_usage_display("entdisplay")
                assert "\u65e0\u9650\u5236" in display

    def test_get_user_tier_defaults_to_free(self):
        """get_user_tier returns 'free' for unknown user."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_user_tier
                assert get_user_tier("nobody") == "free"


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestPricing()
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
