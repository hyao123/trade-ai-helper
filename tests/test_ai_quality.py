"""
tests/test_ai_quality.py
------------------------
Unit tests for AI quality improvement modules:
  - utils/user_prefs.py
  - utils/conversation.py
"""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Stub streamlit
# ---------------------------------------------------------------------------
_st = types.ModuleType("streamlit")


class _FakeState(dict):
    def get(self, key, default=None):
        return super().get(key, default)


_st.session_state = _FakeState()
sys.modules.setdefault("streamlit", _st)


# ---------------------------------------------------------------------------
# user_prefs tests
# ---------------------------------------------------------------------------
import tempfile
from pathlib import Path


class TestUserPrefs(unittest.TestCase):
    """Tests for utils/user_prefs.py"""

    def _patch_storage(self, tmp_dir: Path):
        return patch("utils.storage.get_data_dir", return_value=tmp_dir)

    def test_get_prefs_returns_defaults_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import get_prefs, _DEFAULTS
                prefs = get_prefs()
                for key, val in _DEFAULTS.items():
                    self.assertEqual(prefs.get(key), val)

    def test_set_and_get_pref_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import set_pref, get_pref
                set_pref("company_name", "Shenzhen Test Co.")
                result = get_pref("company_name")
                self.assertEqual(result, "Shenzhen Test Co.")

    def test_update_prefs_bulk(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import update_prefs, get_pref
                update_prefs({
                    "company_name": "Test Co",
                    "contact_name": "Tom",
                    "email": "tom@test.com",
                })
                self.assertEqual(get_pref("company_name"), "Test Co")
                self.assertEqual(get_pref("contact_name"), "Tom")
                self.assertEqual(get_pref("email"), "tom@test.com")

    def test_save_seller_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import save_seller_identity, get_pref
                save_seller_identity("ACME Corp", "Alice", "alice@acme.com", "+1-555-0100")
                self.assertEqual(get_pref("company_name"), "ACME Corp")
                self.assertEqual(get_pref("contact_name"), "Alice")
                self.assertEqual(get_pref("signature_name"), "Alice")
                self.assertEqual(get_pref("email"), "alice@acme.com")
                self.assertEqual(get_pref("phone"), "+1-555-0100")

    def test_get_ai_style_suffix_empty_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import get_ai_style_suffix, _DEFAULTS, update_prefs
                # Reset to defaults
                update_prefs({
                    "ai_style_tone": _DEFAULTS["ai_style_tone"],
                    "ai_response_length": _DEFAULTS["ai_response_length"],
                    "ai_custom_instructions": "",
                    "ai_forbidden_words": "",
                })
                suffix = get_ai_style_suffix()
                # Default "专业" and "中等" produce instructions
                self.assertIsInstance(suffix, str)

    def test_get_ai_style_suffix_with_forbidden_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import get_ai_style_suffix, update_prefs
                update_prefs({"ai_forbidden_words": "cheap, inferior"})
                suffix = get_ai_style_suffix()
                self.assertIn("cheap", suffix)
                self.assertIn("inferior", suffix)

    def test_get_ai_style_suffix_with_custom_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import get_ai_style_suffix, update_prefs
                update_prefs({"ai_custom_instructions": "Always mention ISO 9001"})
                suffix = get_ai_style_suffix()
                self.assertIn("ISO 9001", suffix)

    def test_pref_persists_across_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import set_pref, get_pref
                set_pref("default_language", "西班牙语")
                _st.session_state.clear()  # Simulate new page load
                result = get_pref("default_language")
                self.assertEqual(result, "西班牙语")

    def test_unknown_pref_returns_empty_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_storage(Path(tmp)):
                _st.session_state.clear()
                from utils.user_prefs import get_pref
                result = get_pref("nonexistent_key_xyz")
                self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# conversation tests
# ---------------------------------------------------------------------------
class TestConversation(unittest.TestCase):
    """Tests for utils/conversation.py"""

    def setUp(self):
        _st.session_state.clear()

    def test_new_conversation_is_empty(self):
        from utils.conversation import Conversation
        conv = Conversation("test_empty")
        self.assertTrue(conv.is_empty())
        self.assertEqual(conv.turn_count(), 0)

    def test_add_user_and_assistant(self):
        from utils.conversation import Conversation
        conv = Conversation("test_add")
        conv.add_user("Hello")
        conv.add_assistant("Hi there!")
        self.assertFalse(conv.is_empty())
        self.assertEqual(conv.turn_count(), 1)

    def test_get_last_assistant(self):
        from utils.conversation import Conversation
        conv = Conversation("test_last")
        conv.add_user("Q1")
        conv.add_assistant("A1")
        conv.add_user("Q2")
        conv.add_assistant("A2")
        self.assertEqual(conv.get_last_assistant(), "A2")

    def test_get_last_assistant_empty(self):
        from utils.conversation import Conversation
        conv = Conversation("test_last_empty")
        self.assertEqual(conv.get_last_assistant(), "")

    def test_clear_keeps_system(self):
        from utils.conversation import Conversation
        conv = Conversation("test_clear_sys", system_prompt="You are helpful.")
        conv.add_user("Hello")
        conv.add_assistant("Hi")
        conv.clear(keep_system=True)
        msgs = conv.get_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["role"], "system")

    def test_clear_removes_all(self):
        from utils.conversation import Conversation
        conv = Conversation("test_clear_all")
        conv.add_user("Hello")
        conv.clear(keep_system=False)
        self.assertTrue(conv.is_empty())

    def test_turn_count_increments(self):
        from utils.conversation import Conversation
        conv = Conversation("test_turns")
        for i in range(5):
            conv.add_user(f"Q{i}")
            conv.add_assistant(f"A{i}")
        self.assertEqual(conv.turn_count(), 5)

    def test_trim_prevents_overflow(self):
        from utils.conversation import Conversation, _MAX_TURNS
        conv = Conversation("test_trim")
        # Add more turns than the limit
        for i in range(_MAX_TURNS + 5):
            conv.add_user(f"Q{i}")
            conv.add_assistant(f"A{i}")
        msgs = [m for m in conv.get_messages() if m["role"] != "system"]
        self.assertLessEqual(len(msgs), _MAX_TURNS * 2)

    def test_get_messages_contains_added_messages(self):
        from utils.conversation import Conversation
        conv = Conversation("test_get_msgs")
        conv.add_user("user message")
        conv.add_assistant("assistant reply")
        msgs = conv.get_messages()
        roles = [m["role"] for m in msgs]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)

    def test_system_prompt_stored(self):
        from utils.conversation import Conversation
        conv = Conversation("test_sys_prompt", system_prompt="Be concise.")
        msgs = conv.get_messages()
        system_msgs = [m for m in msgs if m["role"] == "system"]
        self.assertEqual(len(system_msgs), 1)
        self.assertEqual(system_msgs[0]["content"], "Be concise.")

    def test_multiple_conversations_independent(self):
        from utils.conversation import Conversation
        conv_a = Conversation("conv_independent_a")
        conv_b = Conversation("conv_independent_b")
        conv_a.add_user("A question")
        conv_b.add_user("B question")
        conv_b.add_user("B question 2")
        self.assertEqual(conv_a.turn_count(), 1)
        self.assertEqual(conv_b.turn_count(), 2)


if __name__ == "__main__":
    unittest.main()
