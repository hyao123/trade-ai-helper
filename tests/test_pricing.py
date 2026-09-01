"""
tests/test_pricing.py
Unit tests for utils/pricing.py - tiered pricing and usage tracking.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st


class TestPricing:
    """Tests for utils/pricing.py pricing and usage functions."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def _create_user(self, tmp_dir: Path, username: str, tier: str = "free", verified: bool = True):
        """Helper: create a user entry in users_db.json."""
        db_path = tmp_dir / "users_db.json"
        users = {}
        if db_path.exists():
            with open(db_path, encoding="utf-8") as f:
                users = json.load(f)
        users[username] = {
            "username": username,
            "email": f"{username}@example.com",
            "email_verified": verified,
            "password_hash": "fakehash",
            "tier": tier,
            "created_at": "2026-01-01 00:00",
        }
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(users, f)
        user_dir = tmp_dir / "users" / username
        user_dir.mkdir(parents=True, exist_ok=True)

    def test_get_daily_usage_returns_zero_for_new_user(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_daily_usage
                assert get_daily_usage("newuser123") == 0

    def test_increment_usage_requires_verified_email(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "unverified", "free", verified=False)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.email_service.has_email_provider_configured", return_value=True):
                from utils.pricing import get_daily_usage, increment_usage
                ok, msg = increment_usage("unverified")
                assert ok is False
                assert "验证邮箱" in msg
                assert get_daily_usage("unverified") == 0

    def test_increment_usage_increments_count(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "testuser", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_daily_usage, increment_usage
                ok, msg = increment_usage("testuser")
                assert ok is True
                assert msg == ""
                assert get_daily_usage("testuser") == 1

                ok2, _ = increment_usage("testuser")
                assert ok2 is True
                assert get_daily_usage("testuser") == 2

    def test_increment_usage_returns_false_when_limit_exceeded(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "freeuser", "free")
            user_dir = tmp_dir / "users" / "freeuser"
            usage = {"date": date.today().isoformat(), "count": 20}
            with open(user_dir / "usage.json", "w", encoding="utf-8") as f:
                json.dump(usage, f)

            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import increment_usage
                ok, msg = increment_usage("freeuser")
                assert ok is False
                assert "上限" in msg

    def test_usage_resets_on_new_day(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "dayuser", "free")
            user_dir = tmp_dir / "users" / "dayuser"
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            usage = {"date": yesterday, "count": 15}
            with open(user_dir / "usage.json", "w", encoding="utf-8") as f:
                json.dump(usage, f)

            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_daily_usage
                assert get_daily_usage("dayuser") == 0

    def test_check_feature_access_requires_verified_email(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "unverified2", "enterprise", verified=False)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.email_service.has_email_provider_configured", return_value=True):
                from utils.pricing import check_feature_access
                assert check_feature_access("unverified2", "basic") is False
                assert check_feature_access("unverified2", "priority_support") is False

    def test_check_feature_access_free_tier(self):
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
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "entuser2", "enterprise")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import increment_usage
                for i in range(50):
                    ok, msg = increment_usage("entuser2")
                    assert ok is True, f"Failed on iteration {i}: {msg}"
                    assert msg == ""

    def test_upgrade_user_tier(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "upgradeuser", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_user_tier, upgrade_user_tier
                assert get_user_tier("upgradeuser") == "free"
                assert upgrade_user_tier("upgradeuser", "pro") is True
                assert get_user_tier("upgradeuser") == "pro"

    def test_upgrade_user_tier_invalid_tier(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "badtier", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import upgrade_user_tier
                assert upgrade_user_tier("badtier", "platinum") is False

    def test_upgrade_user_tier_nonexistent_user(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import upgrade_user_tier
                assert upgrade_user_tier("ghost", "pro") is False

    def test_get_usage_display_free(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "displayuser", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_usage_display, increment_usage
                assert get_usage_display("displayuser") == "0/20"
                increment_usage("displayuser")
                assert get_usage_display("displayuser") == "1/20"

    def test_get_usage_display_enterprise(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "entdisplay", "enterprise")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_usage_display
                assert "无限制" in get_usage_display("entdisplay")

    def test_get_user_tier_defaults_to_free(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_user_tier
                assert get_user_tier("nobody") == "free"

    def test_get_usage_history_empty_for_new_user(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_usage_history
                assert get_usage_history("newuser999") == []

    def test_increment_usage_populates_history(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "histuser", "free")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_usage_history, increment_usage
                increment_usage("histuser")
                history = get_usage_history("histuser")
                assert len(history) == 1
                assert history[0]["date"] == date.today().isoformat()
                assert history[0]["count"] == 1

                increment_usage("histuser")
                history = get_usage_history("histuser")
                assert len(history) == 1
                assert history[0]["count"] == 2

    def test_usage_history_capped_at_7_entries(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "capuser", "free")
            user_dir = tmp_dir / "users" / "capuser"
            today_str = date.today().isoformat()
            history = []
            for i in range(8):
                d = (date.today() - timedelta(days=8 - i)).isoformat()
                history.append({"date": d, "count": i + 1})
            usage = {"date": today_str, "count": 5, "history": history}
            with open(user_dir / "usage.json", "w", encoding="utf-8") as f:
                json.dump(usage, f)

            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.pricing import get_usage_history, increment_usage
                increment_usage("capuser")
                assert len(get_usage_history("capuser")) <= 7


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
