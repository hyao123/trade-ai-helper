"""Tests for verified-email feature gating."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEmailGate:
    def _setup(self):
        return tempfile.TemporaryDirectory()

    def _create_user(self, tmp_dir: Path, username: str, verified: bool, email: str | None = None):
        users_path = tmp_dir / "users_db.json"
        users = {}
        if users_path.exists():
            users = json.loads(users_path.read_text(encoding="utf-8"))
        users[username] = {
            "username": username,
            "email": email if email is not None else f"{username}@example.com",
            "email_verified": verified,
            "password_hash": "fakehash",
            "tier": "free",
        }
        users_path.write_text(json.dumps(users), encoding="utf-8")

    def test_admin_bypasses_verified_email_gate(self):
        from utils.email_gate import require_verified_email
        allowed, message = require_verified_email("admin")
        assert allowed is True
        assert message == ""

    def test_verified_user_allowed(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "verified", verified=True)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.email_gate import require_verified_email
                allowed, message = require_verified_email("verified")
                assert allowed is True
                assert message == ""

    def test_unverified_user_blocked(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "pending", verified=False)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.email_service.has_email_provider_configured", return_value=True):
                from utils.email_gate import require_verified_email
                allowed, message = require_verified_email("pending")
                assert allowed is False
                assert "验证邮箱" in message

    def test_unverified_user_allowed_without_provider(self):
        """Without any mail provider the gate cannot send tokens, so it must not lock users out."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "pending2", verified=False)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.email_service.has_email_provider_configured", return_value=False):
                from utils.email_gate import require_verified_email
                allowed, message = require_verified_email("pending2")
                assert allowed is True
                assert message == ""

    def test_verified_user_blocked_when_no_email(self):
        """A user without any email stays blocked even without a mail provider."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "noemail2", verified=True, email="")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.email_service.has_email_provider_configured", return_value=False):
                from utils.email_gate import require_verified_email
                allowed, message = require_verified_email("noemail2")
                assert allowed is False
                assert "验证邮箱" in message

    def test_user_without_email_blocked(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            self._create_user(tmp_dir, "noemail", verified=True, email="")
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.email_gate import require_verified_email
                allowed, message = require_verified_email("noemail")
                assert allowed is False
                assert "验证邮箱" in message

    def test_unknown_user_blocked(self):
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.email_gate import require_verified_email
                allowed, message = require_verified_email("missing")
                assert allowed is False
                assert "验证邮箱" in message


if __name__ == "__main__":
    import traceback
    cls = TestEmailGate()
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
