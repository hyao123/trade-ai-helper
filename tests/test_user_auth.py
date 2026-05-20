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

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that use it
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st

# Mock dotenv before importing modules that use it (not available in test env)
_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv


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
                from utils.user_auth import _load_users_db, register_user
                success, msg = register_user("testuser", "Test1234")
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
                register_user("diruser", "Test1234")
                user_dir = tmp_dir / "users" / "diruser"
                assert user_dir.exists()
                assert user_dir.is_dir()

    def test_register_user_with_email(self):
        """register_user stores email when provided."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _load_users_db, register_user
                register_user("emailuser", "Test1234", email="test@example.com")
                users = _load_users_db()
                assert users["emailuser"]["email"] == "test@example.com"

    def test_register_duplicate_username_rejected(self):
        """register_user rejects duplicate username."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                register_user("dupuser", "Test1234")
                success, msg = register_user("dupuser", "Other1234")
                assert success is False
                assert "already exists" in msg.lower()

    def test_register_username_case_insensitive(self):
        """register_user normalizes username to lowercase."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                register_user("TestUser", "Test1234")
                success, msg = register_user("testuser", "Other1234")
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
        """register_user rejects password shorter than 8 characters."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("validuser", "ab")
                assert success is False
                assert "at least 8" in msg.lower()

    def test_register_password_no_uppercase_rejected(self):
        """register_user rejects password without uppercase letter."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("validuser", "alllower1")
                assert success is False
                assert "uppercase" in msg.lower()

    def test_register_password_no_digit_rejected(self):
        """register_user rejects password without a digit."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("validuser", "NoDigitPass")
                assert success is False
                assert "digit" in msg.lower()

    def test_register_non_alphanumeric_rejected(self):
        """register_user rejects username with special characters."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user
                success, msg = register_user("user@name", "Test1234")
                assert success is False
                assert "letters and numbers" in msg.lower()

    def test_authenticate_user_success(self):
        """authenticate_user succeeds with correct credentials."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("authuser", "MyPass123")
                success, user_info = authenticate_user("authuser", "MyPass123")
                assert success is True
                assert user_info is not None
                assert user_info["username"] == "authuser"
                assert user_info["tier"] == "free"
                assert "password_hash" not in user_info

    def test_authenticate_user_wrong_password(self):
        """authenticate_user fails with wrong password (returns None info, not lockout str)."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("authuser2", "Correct9")
                success, user_info = authenticate_user("authuser2", "WrongPass1")
                assert success is False
                # First wrong attempt should return None (not lockout string)
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
                from utils.user_auth import authenticate_user, register_user
                register_user("CaseUser", "Test1234")
                success, user_info = authenticate_user("caseuser", "Test1234")
                assert success is True

    def test_password_hashing_consistent(self):
        """_hash_password with same salt produces consistent results."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _hash_password
                h1 = _hash_password("testpassword", salt="abcdef0123456789")
                h2 = _hash_password("testpassword", salt="abcdef0123456789")
                assert h1 == h2
                # Format should be salt:hash
                assert ":" in h1
                assert h1.startswith("abcdef0123456789:")

    def test_password_hashing_different_inputs(self):
        """_hash_password produces different results for different inputs."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _hash_password
                h1 = _hash_password("password1", salt="samesalt12345678")
                h2 = _hash_password("password2", salt="samesalt12345678")
                assert h1 != h2

    def test_password_hashing_random_salt(self):
        """_hash_password generates unique salts when salt is not provided."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _hash_password
                h1 = _hash_password("samepassword")
                h2 = _hash_password("samepassword")
                # Different salts produce different hashes
                assert h1 != h2
                # Both have salt:hash format
                assert ":" in h1
                assert ":" in h2

    def test_verify_password(self):
        """_verify_password correctly validates passwords against stored hashes."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _hash_password, _verify_password
                stored = _hash_password("mypassword")
                assert _verify_password("mypassword", stored) is True
                assert _verify_password("wrongpassword", stored) is False

    def test_change_password_success(self):
        """change_password works with correct old password."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import (
                    authenticate_user,
                    change_password,
                    register_user,
                )
                register_user("chguser", "OldPass1")
                success, msg = change_password("chguser", "OldPass1", "NewPass2")
                assert success is True
                assert "successfully" in msg.lower()
                # Verify new password works
                auth_ok, _ = authenticate_user("chguser", "NewPass2")
                assert auth_ok is True
                # Verify old password no longer works
                auth_old, _ = authenticate_user("chguser", "OldPass1")
                assert auth_old is False

    def test_change_password_wrong_old(self):
        """change_password fails with incorrect old password."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import change_password, register_user
                register_user("chguser2", "RealPass1")
                success, msg = change_password("chguser2", "WrongPass1", "NewPass2")
                assert success is False
                assert "incorrect" in msg.lower()

    def test_change_password_short_new(self):
        """change_password rejects new password that fails strength policy."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import change_password, register_user
                register_user("chguser3", "RealPass1")
                success, msg = change_password("chguser3", "RealPass1", "ab")
                assert success is False
                assert "at least 8" in msg.lower()

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

    def test_register_user_includes_email_verification_fields(self):
        """register_user includes email_verified=False and verification_token in user record."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import _load_users_db, register_user
                register_user("verifyuser", "Test1234", email="test@example.com")
                users = _load_users_db()
                assert users["verifyuser"]["email_verified"] is False
                assert "verification_token" in users["verifyuser"]
                assert len(users["verifyuser"]["verification_token"]) > 0

    def test_verify_email_token_success(self):
        """verify_email_token succeeds with correct token."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    register_user,
                    verify_email_token,
                )
                register_user("tokenuser", "Test1234", email="t@example.com")
                users = _load_users_db()
                token_data = users["tokenuser"]["verification_token"]
                token = token_data["token"] if isinstance(token_data, dict) else token_data
                success, msg = verify_email_token("tokenuser", token)
                assert success is True
                assert "success" in msg.lower()
                # Verify the user is now marked as verified
                users = _load_users_db()
                assert users["tokenuser"]["email_verified"] is True
                assert users["tokenuser"]["verification_token"] == ""

    def test_verify_email_token_wrong_token(self):
        """verify_email_token fails with wrong token."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import register_user, verify_email_token
                register_user("wrongtokenuser", "Test1234", email="t@example.com")
                success, msg = verify_email_token("wrongtokenuser", "wrong-token-value")
                assert success is False
                assert "invalid" in msg.lower()

    def test_verify_email_token_nonexistent_user(self):
        """verify_email_token fails for nonexistent user."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import verify_email_token
                success, msg = verify_email_token("nosuchuser", "some-token")
                assert success is False
                assert "not found" in msg.lower()

    def test_find_user_by_email_found(self):
        """find_user_by_email returns correct username when email matches."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import find_user_by_email, register_user
                register_user("emailfinder", "Test1234", email="finder@example.com")
                result = find_user_by_email("finder@example.com")
                assert result == "emailfinder"

    def test_find_user_by_email_not_found(self):
        """find_user_by_email returns None for nonexistent email."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import find_user_by_email
                result = find_user_by_email("nobody@example.com")
                assert result is None

    def test_find_user_by_email_case_insensitive(self):
        """find_user_by_email finds user regardless of email case."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import find_user_by_email, register_user
                register_user("casemail", "Test1234", email="CaseTest@Example.COM")
                result = find_user_by_email("casetest@example.com")
                assert result == "casemail"

    def test_request_password_reset_generates_token(self):
        """request_password_reset stores a reset_token with token and expires fields."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    register_user,
                    request_password_reset,
                )
                register_user("resetuser", "Test1234", email="reset@example.com")
                success, msg = request_password_reset("reset@example.com")
                assert success is True
                users = _load_users_db()
                assert "reset_token" in users["resetuser"]
                assert "token" in users["resetuser"]["reset_token"]
                assert "expires" in users["resetuser"]["reset_token"]
                assert len(users["resetuser"]["reset_token"]["token"]) > 0

    def test_request_password_reset_nonexistent_still_succeeds(self):
        """request_password_reset returns (True, ...) for nonexistent user (security)."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import request_password_reset
                success, msg = request_password_reset("nonexistent@example.com")
                assert success is True

    def test_reset_password_valid_token(self):
        """reset_password works with valid token and updates password."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    authenticate_user,
                    register_user,
                    request_password_reset,
                    reset_password,
                )
                register_user("resetok", "OldPass1", email="resetok@example.com")
                request_password_reset("resetok@example.com")
                users = _load_users_db()
                token = users["resetok"]["reset_token"]["token"]
                success, msg = reset_password("resetok", token, "NewPass2")
                assert success is True
                # Verify new password works
                auth_ok, _ = authenticate_user("resetok", "NewPass2")
                assert auth_ok is True
                # Verify old password no longer works
                auth_old, _ = authenticate_user("resetok", "OldPass1")
                assert auth_old is False

    def test_reset_password_wrong_token(self):
        """reset_password fails with wrong token."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import (
                    register_user,
                    request_password_reset,
                    reset_password,
                )
                register_user("resetwrong", "Test1234", email="wrong@example.com")
                request_password_reset("wrong@example.com")
                success, msg = reset_password("resetwrong", "wrong-token-value", "NewPass2")
                assert success is False

    def test_reset_password_expired_token(self):
        """reset_password fails when token is expired."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from datetime import datetime, timedelta, timezone

                from utils.user_auth import (
                    _load_users_db,
                    _save_users_db,
                    register_user,
                    request_password_reset,
                    reset_password,
                )
                register_user("resetexp", "Test1234", email="exp@example.com")
                request_password_reset("exp@example.com")
                # Manually set expired timestamp
                users = _load_users_db()
                token = users["resetexp"]["reset_token"]["token"]
                expired_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
                users["resetexp"]["reset_token"]["expires"] = expired_time
                _save_users_db(users)
                success, msg = reset_password("resetexp", token, "NewPass2")
                assert success is False
                assert "expired" in msg.lower()

    def test_reset_password_short_password(self):
        """reset_password fails for password that violates strength policy."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    register_user,
                    request_password_reset,
                    reset_password,
                )
                register_user("resetshort", "Test1234", email="short@example.com")
                request_password_reset("short@example.com")
                users = _load_users_db()
                token = users["resetshort"]["reset_token"]["token"]
                success, msg = reset_password("resetshort", token, "ab")
                assert success is False
                assert "at least 8" in msg.lower()


    def test_validate_password_strength_valid(self):
        """validate_password_strength accepts passwords meeting all criteria."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import validate_password_strength
                ok, msg = validate_password_strength("Test1234")
                assert ok is True
                assert msg == ""

    def test_validate_password_strength_too_short(self):
        """validate_password_strength rejects passwords under 8 characters."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import validate_password_strength
                ok, msg = validate_password_strength("Ab1")
                assert ok is False
                assert "at least 8" in msg.lower()

    def test_validate_password_strength_no_uppercase(self):
        """validate_password_strength rejects passwords without uppercase."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import validate_password_strength
                ok, msg = validate_password_strength("nouppercase1")
                assert ok is False
                assert "uppercase" in msg.lower()

    def test_validate_password_strength_no_digit(self):
        """validate_password_strength rejects passwords without a digit."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import validate_password_strength
                ok, msg = validate_password_strength("NoDigitHere")
                assert ok is False
                assert "digit" in msg.lower()

    def test_validate_password_strength_empty(self):
        """validate_password_strength rejects empty/None password."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import validate_password_strength
                ok, msg = validate_password_strength("")
                assert ok is False
                ok2, _ = validate_password_strength(None)
                assert ok2 is False

    def test_brute_force_lockout_after_5_failures(self):
        """Account is locked after 5 consecutive wrong password attempts."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("locktest", "LockMe99")
                # 5 wrong attempts
                for _ in range(5):
                    ok, info = authenticate_user("locktest", "WrongPass1")
                    assert ok is False
                # 6th attempt: account should now be locked
                ok, info = authenticate_user("locktest", "LockMe99")  # even correct pw
                assert ok is False
                assert isinstance(info, str)  # lockout message, not None
                assert "锁" in info or "locked" in info.lower() or "分钟" in info

    def test_brute_force_no_lockout_below_threshold(self):
        """Account stays unlocked after 4 wrong attempts (below threshold of 5)."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import authenticate_user, register_user
                register_user("nolocktest", "NoLock99")
                # 4 wrong attempts (one below threshold)
                for _ in range(4):
                    ok, _ = authenticate_user("nolocktest", "WrongPass1")
                    assert ok is False
                # Correct password should still work
                ok, info = authenticate_user("nolocktest", "NoLock99")
                assert ok is True
                assert info is not None
                assert info["username"] == "nolocktest"

    def test_successful_login_clears_failed_attempts(self):
        """Successful login resets the failed attempt counter."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.user_auth.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.user_auth import (
                    _load_users_db,
                    authenticate_user,
                    register_user,
                )
                register_user("cleartest", "ClearMe9")
                # 3 wrong attempts
                for _ in range(3):
                    authenticate_user("cleartest", "WrongPass1")
                # Correct login
                ok, _ = authenticate_user("cleartest", "ClearMe9")
                assert ok is True
                # Counter should be reset to 0
                users = _load_users_db()
                assert users["cleartest"].get("failed_attempts", 0) == 0
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
