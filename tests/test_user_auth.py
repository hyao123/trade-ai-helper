"""
tests/test_user_auth.py
Unit tests for utils/user_auth.py - multi-user authentication system.
"""
from __future__ import annotations

import sys
import os
import types
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that use it
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st


class TestUserAuth:
    """Tests for utils/user_auth.py authentication functions."""

    def _setup(self):
        """Reset mock state and create auto-cleaning temp dir."""
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_register_user_creates_entry(self):
        """register_user creates a user entry in users_db.json."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, _load_users_db
                success, msg = register_user("testuser", "pass1234")
                assert success is True
                assert "successful" in msg.lower()
                users = _load_users_db()
                assert "testuser" in users
                assert users["testuser"]["username"] == "testuser"
                assert users["testuser"]["tier"] == "free"
                assert "password_hash" in users["testuser"]

    def test_register_user_creates_data_directory(self):
        """register_user creates data/users/{username}/ directory."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.user_auth.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                register_user("diruser", "pass1234")
                user_dir = tmp_dir / "users" / "diruser"
                assert user_dir.exists()
                assert user_dir.is_dir()

    def test_register_user_with_email(self):
        """register_user stores email when provided."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, _load_users_db
                register_user("emailuser", "pass1234", email="test@example.com")
                users = _load_users_db()
                assert users["emailuser"]["email"] == "test@example.com"

    def test_register_duplicate_username_rejected(self):
        """register_user rejects duplicate username."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                register_user("dupuser", "pass1234")
                success, msg = register_user("dupuser", "otherpass")
                assert success is False
                assert "already exists" in msg.lower()

    def test_register_username_case_insensitive(self):
        """register_user normalizes username to lowercase."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                register_user("TestUser", "pass1234")
                success, msg = register_user("testuser", "otherpass")
                assert success is False
                assert "already exists" in msg.lower()

    def test_register_empty_username_rejected(self):
        """register_user rejects empty username."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("", "pass1234")
                assert success is False

    def test_register_short_username_rejected(self):
        """register_user rejects username shorter than 3 characters."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("ab", "pass1234")
                assert success is False
                assert "at least 3" in msg.lower()

    def test_register_short_password_rejected(self):
        """register_user rejects password shorter than 4 characters."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("validuser", "ab")
                assert success is False
                assert "at least 4" in msg.lower()

    def test_register_non_alphanumeric_rejected(self):
        """register_user rejects username with special characters."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("user@name", "pass1234")
                assert success is False
                assert "letters and numbers" in msg.lower()

    def test_authenticate_user_success(self):
        """authenticate_user succeeds with correct credentials."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, authenticate_user
                register_user("authuser", "mypassword")
                success, user_info = authenticate_user("authuser", "mypassword")
                assert success is True
                assert user_info is not None
                assert user_info["username"] == "authuser"
                assert user_info["tier"] == "free"
                assert "password_hash" not in user_info

    def test_authenticate_user_wrong_password(self):
        """authenticate_user fails with wrong password."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, authenticate_user
                register_user("authuser2", "correct")
                success, user_info = authenticate_user("authuser2", "wrong")
                assert success is False
                assert user_info is None

    def test_authenticate_user_nonexistent(self):
        """authenticate_user fails for nonexistent user."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import authenticate_user
                success, user_info = authenticate_user("nobody", "pass")
                assert success is False
                assert user_info is None

    def test_authenticate_user_case_insensitive(self):
        """authenticate_user normalizes username to lowercase."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, authenticate_user
                register_user("CaseUser", "pass1234")
                success, user_info = authenticate_user("caseuser", "pass1234")
                assert success is True

    def test_password_hashing_consistent(self):
        """_hash_password produces consistent results for same input."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _hash_password
                h1 = _hash_password("testpassword")
                h2 = _hash_password("testpassword")
                assert h1 == h2

    def test_password_hashing_different_inputs(self):
        """_hash_password produces different results for different inputs."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _hash_password
                h1 = _hash_password("password1")
                h2 = _hash_password("password2")
                assert h1 != h2

    def test_change_password_success(self):
        """change_password works with correct old password."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, change_password, authenticate_user
                register_user("chguser", "oldpass1")
                success, msg = change_password("chguser", "oldpass1", "newpass1")
                assert success is True
                assert "successfully" in msg.lower()
                # Verify new password works
                auth_ok, _ = authenticate_user("chguser", "newpass1")
                assert auth_ok is True
                # Verify old password no longer works
                auth_old, _ = authenticate_user("chguser", "oldpass1")
                assert auth_old is False

    def test_change_password_wrong_old(self):
        """change_password fails with incorrect old password."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, change_password
                register_user("chguser2", "realpass")
                success, msg = change_password("chguser2", "wrongpass", "newpass1")
                assert success is False
                assert "incorrect" in msg.lower()

    def test_change_password_short_new(self):
        """change_password rejects new password shorter than 4 characters."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, change_password
                register_user("chguser3", "realpass")
                success, msg = change_password("chguser3", "realpass", "ab")
                assert success is False
                assert "at least 4" in msg.lower()

    def test_get_user_data_dir_creates_directory(self):
        """get_user_data_dir creates the user directory if needed."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.user_auth.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import get_user_data_dir
                user_dir = get_user_data_dir("newuser")
                assert user_dir.exists()
                assert user_dir.is_dir()
                assert user_dir == tmp_dir / "users" / "newuser"

    def test_get_current_user_none_by_default(self):
        """get_current_user returns None when no user is logged in."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import get_current_user
                assert get_current_user() is None

    def test_get_current_user_returns_session_user(self):
        """get_current_user returns user dict from session_state."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import get_current_user
                _mock_st.session_state["current_user"] = {"username": "bob", "tier": "free"}
                user = get_current_user()
                assert user is not None
                assert user["username"] == "bob"


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestUserAuth()
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
