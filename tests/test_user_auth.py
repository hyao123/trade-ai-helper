"""
tests/test_user_auth.py
Unit tests for utils/user_auth.py - multi-user authentication system.
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st

_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv


class TestUserAuth:
    """Tests for registration, login, password reset, and lockout."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def _patch_storage(self, tmp_dir: Path):
        return patch("utils.storage.get_data_dir", return_value=tmp_dir)

    def test_register_user_requires_email(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("testuser", "pass1234")
                assert success is False
                assert "email" in msg.lower()

    def test_register_user_rejects_invalid_email(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("testuser", "pass1234", email="not-an-email")
                assert success is False
                assert "email" in msg.lower()

    def test_register_user_creates_entry_and_session(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import _load_users_db, register_user
                success, msg = register_user("testuser", "pass1234", email="test@example.com")
                assert success is True
                assert "successful" in msg.lower()
                users = _load_users_db()
                assert users["testuser"]["username"] == "testuser"
                assert users["testuser"]["email"] == "test@example.com"
                assert users["testuser"]["tier"] == "free"
                assert "password_hash" in users["testuser"]
                assert users["testuser"]["email_verified"] is False
                assert "verification_token" in users["testuser"]
                assert _mock_st.session_state["authenticated"] is True
                assert _mock_st.session_state["current_user"]["username"] == "testuser"

    def test_register_duplicate_username_rejected(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                register_user("dupuser", "pass1234", email="one@example.com")
                success, msg = register_user("dupuser", "otherpass", email="two@example.com")
                assert success is False
                assert "already exists" in msg.lower()

    def test_register_duplicate_email_rejected(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                register_user("userone", "pass1234", email="same@example.com")
                success, msg = register_user("usertwo", "pass1234", email="same@example.com")
                assert success is False
                assert "email" in msg.lower()

    def test_authenticate_user_success(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("authuser", "mypassword", email="auth@example.com")
                success, user_info = authenticate_user("authuser", "mypassword")
                assert success is True
                assert user_info is not None
                assert user_info["username"] == "authuser"
                assert user_info["email"] == "auth@example.com"
                assert "password_hash" not in user_info

    def test_authenticate_user_wrong_password(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("authuser2", "correct1", email="auth2@example.com")
                success, user_info = authenticate_user("authuser2", "wrong")
                assert success is False
                assert user_info is None

    def test_change_password_success(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import authenticate_user, change_password, register_user
                register_user("chguser", "oldpass1", email="chg@example.com")
                success, msg = change_password("chguser", "oldpass1", "newpass1")
                assert success is True
                assert "successfully" in msg.lower()
                auth_ok, _ = authenticate_user("chguser", "newpass1")
                assert auth_ok is True
                auth_old, _ = authenticate_user("chguser", "oldpass1")
                assert auth_old is False

    def test_verify_email_token_success(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import _load_users_db, register_user, verify_email_token
                register_user("tokenuser", "pass1234", email="token@example.com")
                users = _load_users_db()
                token_data = users["tokenuser"]["verification_token"]
                token = token_data["token"]
                success, msg = verify_email_token("tokenuser", token)
                assert success is True
                assert "success" in msg.lower()
                users = _load_users_db()
                assert users["tokenuser"]["email_verified"] is True
                assert users["tokenuser"]["verification_token"] == ""

    def test_find_user_by_email_case_insensitive(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import find_user_by_email, register_user
                register_user("casemail", "pass1234", email="CaseTest@Example.COM")
                assert find_user_by_email("casetest@example.com") == "casemail"

    def test_request_password_reset_and_reset_password(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    authenticate_user,
                    register_user,
                    request_password_reset,
                    reset_password,
                )
                register_user("resetuser", "oldpass1", email="reset@example.com")
                success, _ = request_password_reset("reset@example.com")
                assert success is True
                users = _load_users_db()
                token = users["resetuser"]["reset_token"]["token"]
                success, msg = reset_password("resetuser", token, "newpass1")
                assert success is True
                assert "successful" in msg.lower()
                auth_ok, _ = authenticate_user("resetuser", "newpass1")
                assert auth_ok is True

    def test_login_failures_lock_account_temporarily(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import _LOGIN_FAILURE_LIMIT, _is_login_locked, authenticate_user, register_user
                register_user("lockeduser", "correct1", email="locked@example.com")
                for _ in range(_LOGIN_FAILURE_LIMIT):
                    success, _ = authenticate_user("lockeduser", "wrongpass")
                    assert success is False
                success, user = authenticate_user("lockeduser", "correct1")
                assert success is False
                assert user is None
                assert _is_login_locked("lockeduser") is True


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
