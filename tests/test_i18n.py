"""
tests/test_i18n.py
Unit tests for config/i18n.py - internationalization module.
"""
from __future__ import annotations

import os
import sys
import types

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

from config.i18n import TRANSLATIONS, get_lang, t  # noqa: E402


class TestI18n:
    """Tests for config/i18n.py translation functions."""

    def _setup(self):
        """Reset mock session state."""
        _mock_st.session_state.clear()

    def test_t_returns_zh_translation_for_known_key(self):
        """t() returns Chinese translation for a known key when language is zh."""
        self._setup()
        _mock_st.session_state["language"] = "zh"
        result = t("login")
        assert result == TRANSLATIONS["zh"]["login"]
        assert result == "\u767b\u5f55"

    def test_t_returns_en_translation_for_known_key(self):
        """t() returns English translation for a known key when language is en."""
        self._setup()
        _mock_st.session_state["language"] = "en"
        result = t("login")
        assert result == TRANSLATIONS["en"]["login"]
        assert result == "Login"

    def test_t_returns_key_for_unknown_key(self):
        """t() returns the key itself as fallback for unknown keys."""
        self._setup()
        _mock_st.session_state["language"] = "zh"
        result = t("nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_zh_and_en_have_same_keys(self):
        """zh and en translation dicts have the same set of keys (key parity)."""
        zh_keys = set(TRANSLATIONS["zh"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())
        missing_in_en = zh_keys - en_keys
        missing_in_zh = en_keys - zh_keys
        assert missing_in_en == set(), f"Keys in zh but not en: {missing_in_en}"
        assert missing_in_zh == set(), f"Keys in en but not zh: {missing_in_zh}"

    def test_get_lang_returns_zh_by_default(self):
        """get_lang() returns 'zh' when no language is set in session state."""
        self._setup()
        result = get_lang()
        assert result == "zh"

    def test_get_lang_returns_session_language(self):
        """get_lang() returns language from session state when set."""
        self._setup()
        _mock_st.session_state["language"] = "en"
        result = get_lang()
        assert result == "en"


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestI18n()
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
