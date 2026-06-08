"""Tests for user preference prompt suffix helpers."""
from __future__ import annotations

import json
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


def _setup_user_session(username: str = "prefuser"):
    sys.modules["streamlit"] = _mock_st
    _mock_st.session_state.clear()
    _mock_st.session_state["current_user"] = {"username": username, "tier": "free"}


def test_user_preferences_persist_to_existing_json_layout():
    _setup_user_session("jsonuser")
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.user_prefs import get_pref, update_prefs
            update_prefs({"company_name": "Repository Export Ltd."})
            assert get_pref("company_name") == "Repository Export Ltd."
            prefs_path = tmp_dir / "users" / "jsonuser" / "prefs.json"
            assert prefs_path.exists()
            stored = json.loads(prefs_path.read_text(encoding="utf-8"))
            assert stored["company_name"] == "Repository Export Ltd."


def test_shared_preferences_persist_for_admin_or_anonymous_context():
    _mock_st.session_state.clear()
    _mock_st.session_state["current_user"] = {"username": "admin", "tier": "enterprise"}
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.user_prefs import get_pref, update_prefs
            update_prefs({"default_product": "Shared Default Product"})
            assert get_pref("default_product") == "Shared Default Product"
            prefs_path = tmp_dir / "prefs.json"
            assert prefs_path.exists()
            stored = json.loads(prefs_path.read_text(encoding="utf-8"))
            assert stored["default_product"] == "Shared Default Product"


def test_business_context_suffix_empty_without_profile_data():
    _setup_user_session()
    with tempfile.TemporaryDirectory() as tmp_str:
        with patch("utils.storage.get_data_dir", return_value=Path(tmp_str)):
            from utils.user_prefs import get_business_context_suffix
            assert get_business_context_suffix() == ""


def test_business_context_suffix_includes_onboarding_fields():
    _setup_user_session()
    with tempfile.TemporaryDirectory() as tmp_str:
        with patch("utils.storage.get_data_dir", return_value=Path(tmp_str)):
            from utils.user_prefs import get_business_context_suffix, update_prefs
            update_prefs({
                "company_name": "Shenzhen LED Technology Co., Ltd.",
                "contact_name": "Tom Chen",
                "default_product": "LED Street Light",
                "main_products": "LED street lights, flood lights, solar lights",
                "target_markets": "Europe, Middle East",
                "company_description": "ISO-certified factory with 12 production lines.",
                "default_trade_term": "FOB",
            })
            suffix = get_business_context_suffix()
            assert "Business context" in suffix
            assert "Company: Shenzhen LED Technology" in suffix
            assert "Default product: LED Street Light" in suffix
            assert "Target markets: Europe, Middle East" in suffix
            assert "trusted seller profile data" in suffix


def test_ai_style_suffix_combines_business_context_and_style():
    _setup_user_session()
    with tempfile.TemporaryDirectory() as tmp_str:
        with patch("utils.storage.get_data_dir", return_value=Path(tmp_str)):
            from utils.user_prefs import get_ai_style_suffix, update_prefs
            update_prefs({
                "company_name": "ABC Export Ltd.",
                "main_products": "Industrial pumps",
                "ai_style_tone": "简洁",
                "ai_response_length": "简短",
                "ai_forbidden_words": "cheap, inferior",
            })
            suffix = get_ai_style_suffix()
            assert "Business context" in suffix
            assert "ABC Export Ltd." in suffix
            assert "Industrial pumps" in suffix
            assert "Be extremely concise" in suffix
            assert "under 80 words" in suffix
            assert "Avoid using these words: cheap, inferior" in suffix


def test_business_context_suffix_caps_very_long_values():
    _setup_user_session()
    with tempfile.TemporaryDirectory() as tmp_str:
        with patch("utils.storage.get_data_dir", return_value=Path(tmp_str)):
            from utils.user_prefs import get_business_context_suffix, update_prefs
            update_prefs({
                "company_description": "A" * 5000,
                "main_products": "B" * 5000,
                "target_markets": "C" * 5000,
            })
            suffix = get_business_context_suffix()
            assert len(suffix) <= 1600
            assert "…" in suffix


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS: {name}")
