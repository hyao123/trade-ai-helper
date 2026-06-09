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

GOOD_PASSWORD = "securepass123"
ALT_PASSWORD = "anotherpass123"


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
                success, msg = register_user("testuser", GOOD_PASSWORD)
                assert success is False
                assert "email" in msg.lower()

    def test_register_user_rejects_invalid_email(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("testuser", GOOD_PASSWORD, email="not-an-email")
                assert success is False
                assert "email" in msg.lower()

    def test_register_user_rejects_short_or_common_password(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                short_ok, short_msg = register_user("shortpw", "pass1234", email="short@example.com")
                assert short_ok is False
                assert "password" in short_msg.lower()
                weak_ok, weak_msg = register_user("weakpw", "password123", email="weak@example.com")
                assert weak_ok is False
                assert "password" in weak_msg.lower()

    def test_register_user_creates_entry_and_session(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import _load_users_db, register_user
                success, msg = register_user("testuser", GOOD_PASSWORD, email="test@example.com")
                assert success is True
                assert "successful" in msg.lower()
                users = _load_users_db()
                assert users["testuser"]["username"] == "testuser"
                assert users["testuser"]["email"] == "test@example.com"
                assert users["testuser"]["tier"] == "free"
                assert "password_hash" in users["testuser"]
                assert users["testuser"]["password_hash"].startswith("pbkdf2_sha256$v2$310000$")
                assert users["testuser"]["email_verified"] is False
                assert "verification_token" in users["testuser"]
                assert "token_hash" in users["testuser"]["verification_token"]
                assert "token" not in users["testuser"]["verification_token"]
                assert _mock_st.session_state["authenticated"] is True
                assert _mock_st.session_state["current_user"]["username"] == "testuser"

    def test_is_current_admin_requires_authenticated_enterprise_admin(self):
        with self._setup():
            with patch("utils.user_auth.st", _mock_st):
                from utils.user_auth import is_current_admin

                _mock_st.session_state["current_user"] = {"username": "admin", "tier": "enterprise"}
                assert is_current_admin() is False

                _mock_st.session_state["authenticated"] = True
                assert is_current_admin() is True

                _mock_st.session_state["current_user"] = {"username": "admin", "tier": "free"}
                assert is_current_admin() is False

                _mock_st.session_state["current_user"] = {"username": "regular", "tier": "enterprise"}
                assert is_current_admin() is False

    def test_register_duplicate_username_rejected(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                register_user("dupuser", GOOD_PASSWORD, email="one@example.com")
                success, msg = register_user("dupuser", ALT_PASSWORD, email="two@example.com")
                assert success is False
                assert "already exists" in msg.lower()

    def test_register_duplicate_email_rejected(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user
                register_user("userone", GOOD_PASSWORD, email="same@example.com")
                success, msg = register_user("usertwo", GOOD_PASSWORD, email="same@example.com")
                assert success is False
                assert "email" in msg.lower()

    def test_authenticate_user_success(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("authuser", GOOD_PASSWORD, email="auth@example.com")
                success, user_info = authenticate_user("authuser", GOOD_PASSWORD)
                assert success is True
                assert user_info is not None
                assert user_info["username"] == "authuser"
                assert user_info["email"] == "auth@example.com"
                assert "password_hash" not in user_info

    def test_authentication_flows_emit_security_audit_events(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 self._patch_storage(tmp_dir), \
                 patch("utils.user_auth.audit_event") as audit, \
                 patch("utils.user_auth.secrets.token_urlsafe", side_effect=["verify-token", "reset-token"]):
                from utils.user_auth import (
                    authenticate_user,
                    register_user,
                    request_password_reset,
                    reset_password,
                )

                register_user("audituser", GOOD_PASSWORD, email="audit@example.com")
                authenticate_user("audituser", "wrong-password")
                authenticate_user("audituser", GOOD_PASSWORD)
                request_password_reset("audit@example.com")
                reset_password("audituser", "reset-token", ALT_PASSWORD)

        observed = [(call.args[0], call.args[1]) for call in audit.call_args_list]
        assert ("user_registered", "success") in observed
        assert ("login_failed", "invalid_password") in observed
        assert ("login_succeeded", "success") in observed
        assert ("password_reset_requested", "success") in observed
        assert ("password_reset_completed", "success") in observed

    def test_authenticate_legacy_hash_upgrades_to_current_format(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    _pbkdf2_hex,
                    _save_users_db,
                    authenticate_user,
                )
                salt = "abc123salt"
                users = {
                    "legacyuser": {
                        "username": "legacyuser",
                        "email": "legacy@example.com",
                        "password_hash": f"{salt}:{_pbkdf2_hex(GOOD_PASSWORD, salt, 100000)}",
                        "tier": "free",
                        "created_at": "2026-01-01 00:00",
                        "email_verified": True,
                    }
                }
                _save_users_db(users)
                success, user_info = authenticate_user("legacyuser", GOOD_PASSWORD)
                assert success is True
                assert user_info is not None
                upgraded = _load_users_db()["legacyuser"]["password_hash"]
                assert upgraded.startswith("pbkdf2_sha256$v2$310000$")
                assert ":" not in upgraded

    def test_authenticate_user_wrong_password(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("authuser2", GOOD_PASSWORD, email="auth2@example.com")
                success, user_info = authenticate_user("authuser2", "wrong")
                assert success is False
                assert user_info is None

    def test_change_password_success(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import (
                    authenticate_user,
                    change_password,
                    register_user,
                )
                register_user("chguser", GOOD_PASSWORD, email="chg@example.com")
                success, msg = change_password("chguser", GOOD_PASSWORD, ALT_PASSWORD)
                assert success is True
                assert "successfully" in msg.lower()
                auth_ok, _ = authenticate_user("chguser", ALT_PASSWORD)
                assert auth_ok is True
                auth_old, _ = authenticate_user("chguser", GOOD_PASSWORD)
                assert auth_old is False

    def test_update_account_email_requires_new_verification(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 self._patch_storage(tmp_dir), \
                 patch("utils.user_auth.secrets.token_urlsafe", side_effect=["initial-token", "new-email-token"]), \
                 patch("utils.email_service.is_email_configured", return_value=True), \
                 patch("utils.email_service.send_verification_email", return_value=(True, "sent")) as send_email:
                from utils.user_auth import (
                    _load_users_db,
                    register_user,
                    update_account_email,
                )

                register_user("emailuser", GOOD_PASSWORD, email="old@example.com")
                users = _load_users_db()
                users["emailuser"]["email_verified"] = True
                users["emailuser"]["verification_token"] = ""
                from utils.user_auth import _save_users_db
                _save_users_db(users)
                _mock_st.session_state["current_user"]["email_verified"] = True

                success, msg = update_account_email("emailuser", "New@Example.COM")

                assert success is True
                assert "verification" in msg.lower()
                users = _load_users_db()
                assert users["emailuser"]["email"] == "new@example.com"
                assert users["emailuser"]["email_verified"] is False
                assert users["emailuser"]["verification_token"]["token_hash"] != "new-email-token"
                assert _mock_st.session_state["current_user"]["email"] == "new@example.com"
                assert _mock_st.session_state["current_user"]["email_verified"] is False

        assert send_email.call_count == 2

    def test_update_account_email_rejects_duplicate_email(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    register_user,
                    update_account_email,
                )

                register_user("firstuser", GOOD_PASSWORD, email="first@example.com")
                register_user("seconduser", ALT_PASSWORD, email="second@example.com")
                success, msg = update_account_email("firstuser", "SECOND@example.com")

                assert success is False
                assert "email" in msg.lower()
                users = _load_users_db()
                assert users["firstuser"]["email"] == "first@example.com"

    def test_update_account_email_rejects_invalid_email(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import register_user, update_account_email

                register_user("invalidmail", GOOD_PASSWORD, email="valid@example.com")
                success, msg = update_account_email("invalidmail", "not-an-email")

                assert success is False
                assert "email" in msg.lower()

    def test_verify_email_token_success(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 self._patch_storage(tmp_dir), \
                 patch("utils.user_auth.secrets.token_urlsafe", return_value="email-token"):
                from utils.user_auth import (
                    _load_users_db,
                    register_user,
                    verify_email_token,
                )
                register_user("tokenuser", GOOD_PASSWORD, email="token@example.com")
                users = _load_users_db()
                token_data = users["tokenuser"]["verification_token"]
                assert token_data["token_hash"] != "email-token"
                assert "token" not in token_data
                success, msg = verify_email_token("tokenuser", "email-token")
                assert success is True
                assert "success" in msg.lower()
                users = _load_users_db()
                assert users["tokenuser"]["email_verified"] is True
                assert users["tokenuser"]["verification_token"] == ""

    def test_verify_email_token_accepts_legacy_raw_token_record(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    _save_users_db,
                    register_user,
                    verify_email_token,
                )

                register_user("legacytoken", GOOD_PASSWORD, email="legacytoken@example.com")
                users = _load_users_db()
                users["legacytoken"]["verification_token"] = {"token": "legacy-email-token", "expires": ""}
                _save_users_db(users)

                success, msg = verify_email_token("legacytoken", "legacy-email-token")

                assert success is True
                assert "success" in msg.lower()

    def test_resend_verification_email_rate_limit_prevents_email_burst(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 self._patch_storage(tmp_dir), \
                 patch(
                     "utils.user_auth.secrets.token_urlsafe",
                     side_effect=["initial-token", "resend-1", "resend-2", "resend-3"],
                 ), \
                 patch("utils.email_service.is_email_configured", return_value=True), \
                 patch("utils.email_service.send_verification_email", return_value=(True, "sent")) as send_email, \
                 patch("utils.user_auth.audit_event") as audit:
                from utils.user_auth import register_user, resend_verification_email

                register_user("verifyburst", GOOD_PASSWORD, email="verifyburst@example.com")
                messages = [
                    resend_verification_email("verifyburst")
                    for _ in range(4)
                ]

        assert all(success is True for success, _msg in messages)
        assert len({msg for _success, msg in messages}) == 1
        assert send_email.call_count == 4  # 1 registration email + 3 allowed resends
        observed = [(call.args[0], call.args[1]) for call in audit.call_args_list]
        assert ("email_verification_resend", "rate_limited") in observed

    def test_resend_verification_email_limit_uses_hashed_username_key(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 self._patch_storage(tmp_dir), \
                 patch("utils.user_auth.secrets.token_urlsafe", side_effect=["initial-token", "resend-token"]), \
                 patch("utils.email_service.is_email_configured", return_value=True), \
                 patch("utils.email_service.send_verification_email", return_value=(True, "sent")):
                from utils.user_auth import (
                    _email_verification_request_key,
                    _load_email_verification_requests,
                    register_user,
                    resend_verification_email,
                )

                register_user("verifykey", GOOD_PASSWORD, email="verifykey@example.com")
                resend_verification_email("VerifyKey")
                requests = _load_email_verification_requests()
                expected_key = _email_verification_request_key("verifykey")

        assert list(requests) == [expected_key]
        assert "verifykey" not in requests
        assert "VerifyKey" not in requests

    def test_find_user_by_email_case_insensitive(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import find_user_by_email, register_user
                register_user("casemail", GOOD_PASSWORD, email="CaseTest@Example.COM")
                assert find_user_by_email("casetest@example.com") == "casemail"

    def test_request_password_reset_and_reset_password(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 self._patch_storage(tmp_dir), \
                 patch("utils.user_auth.secrets.token_urlsafe", side_effect=["email-token", "reset-token"]):
                from utils.user_auth import (
                    _load_users_db,
                    authenticate_user,
                    register_user,
                    request_password_reset,
                    reset_password,
                )
                register_user("resetuser", GOOD_PASSWORD, email="reset@example.com")
                success, _ = request_password_reset("reset@example.com")
                assert success is True
                users = _load_users_db()
                reset_record = users["resetuser"]["reset_token"]
                assert reset_record["token_hash"] != "reset-token"
                assert "token" not in reset_record
                success, msg = reset_password("resetuser", "reset-token", ALT_PASSWORD)
                assert success is True
                assert "successful" in msg.lower()
                users = _load_users_db()
                assert users["resetuser"]["password_hash"].startswith("pbkdf2_sha256$v2$310000$")
                auth_ok, _ = authenticate_user("resetuser", ALT_PASSWORD)
                assert auth_ok is True

    def test_password_reset_request_rate_limit_prevents_email_burst(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 self._patch_storage(tmp_dir), \
                 patch(
                     "utils.user_auth.secrets.token_urlsafe",
                     side_effect=["email-token", "reset-1", "reset-2", "reset-3"],
                 ), \
                 patch("utils.email_service.is_email_configured", return_value=True), \
                 patch("utils.email_service.send_verification_email", return_value=(True, "sent")), \
                 patch("utils.email_service.send_password_reset_email", return_value=(True, "sent")) as send_email, \
                 patch("utils.user_auth.audit_event") as audit:
                from utils.user_auth import register_user, request_password_reset

                register_user("burstuser", GOOD_PASSWORD, email="burst@example.com")
                messages = [
                    request_password_reset("burst@example.com")
                    for _ in range(4)
                ]

        assert all(success is True for success, _msg in messages)
        assert len({msg for _success, msg in messages}) == 1
        assert send_email.call_count == 3
        observed = [(call.args[0], call.args[1]) for call in audit.call_args_list]
        assert ("password_reset_requested", "rate_limited") in observed

    def test_password_reset_request_limit_uses_hashed_identifier_key(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import (
                    _load_password_reset_requests,
                    _password_reset_request_key,
                    request_password_reset,
                )

                request_password_reset("Unknown@Example.COM")
                requests = _load_password_reset_requests()
                expected_key = _password_reset_request_key("unknown@example.com")

        assert list(requests) == [expected_key]
        assert "Unknown@Example.COM" not in requests
        assert "unknown@example.com" not in requests

    def test_windowed_rate_limit_counters_prune_expired_and_invalid_keys(self):
        from utils.user_auth import _consume_windowed_request

        requests = {
            "active": [990.0],
            "expired": [1.0],
            "invalid_shape": "bad",
            "invalid_timestamp": ["not-a-number"],
        }

        allowed, updated = _consume_windowed_request(
            requests,
            "active",
            limit=3,
            window_seconds=100,
            now=1000.0,
        )

        assert allowed is True
        assert updated == {"active": [990.0, 1000.0]}

    def test_login_failure_counters_prune_expired_and_invalid_keys(self):
        with patch("utils.user_auth._load_login_failures", return_value={
            "alice": [999.0, 1.0],
            "bob": [1.0],
            "bad": ["not-a-number"],
        }), patch("utils.user_auth._save_login_failures") as save_failures:
            from utils.user_auth import _active_failures

            active = _active_failures("alice", now=1000.0)

        assert active == [999.0]
        save_failures.assert_called_once_with({"alice": [999.0]})

    def test_login_failures_lock_account_temporarily(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), self._patch_storage(tmp_dir):
                from utils.user_auth import (
                    _LOGIN_FAILURE_LIMIT,
                    _is_login_locked,
                    authenticate_user,
                    register_user,
                )
                register_user("lockeduser", GOOD_PASSWORD, email="locked@example.com")
                for _ in range(_LOGIN_FAILURE_LIMIT):
                    success, _ = authenticate_user("lockeduser", "wrongpass")
                    assert success is False
                success, user = authenticate_user("lockeduser", GOOD_PASSWORD)
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
