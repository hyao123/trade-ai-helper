"""
tests/test_templates.py
Unit tests for utils/templates.py - template save/load/delete system.
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


class TestTemplates:
    """Tests for utils/templates.py template management functions."""

    def _setup(self):
        """Reset mock state and create temp dir."""
        _mock_st.session_state.clear()
        return Path(tempfile.mkdtemp())

    def test_save_template_creates_category(self):
        """save_template auto-creates a new category."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, load_templates
            save_template("email", "Welcome", {"subject": "Hi", "body": "Hello"})
            templates = load_templates("email")
            assert len(templates) == 1

    def test_save_template_stores_data_with_timestamp(self):
        """Saved template has name, data, and created_at fields."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, load_templates
            save_template("email", "Welcome", {"subject": "Hi"})
            templates = load_templates("email")
            t = templates[0]
            assert t["name"] == "Welcome"
            assert t["data"] == {"subject": "Hi"}
            assert "created_at" in t

    def test_save_template_overwrites_same_name(self):
        """Saving with same name replaces existing, list stays same length."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, load_templates
            save_template("email", "Welcome", {"subject": "Old"})
            save_template("email", "Welcome", {"subject": "New"})
            templates = load_templates("email")
            assert len(templates) == 1
            assert templates[0]["data"] == {"subject": "New"}

    def test_load_templates_returns_list(self):
        """load_templates returns list of templates for category."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, load_templates
            save_template("email", "T1", {"a": 1})
            save_template("email", "T2", {"b": 2})
            templates = load_templates("email")
            assert len(templates) == 2
            names = [t["name"] for t in templates]
            assert "T1" in names
            assert "T2" in names

    def test_load_templates_empty_category(self):
        """load_templates returns [] for non-existent category."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import load_templates
            result = load_templates("nonexistent")
            assert result == []

    def test_delete_template(self):
        """delete_template removes by name, others remain."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, delete_template, load_templates
            save_template("email", "Keep", {"a": 1})
            save_template("email", "Remove", {"b": 2})
            delete_template("email", "Remove")
            templates = load_templates("email")
            assert len(templates) == 1
            assert templates[0]["name"] == "Keep"

    def test_delete_template_nonexistent(self):
        """delete_template with nonexistent name causes no error."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, delete_template, load_templates
            save_template("email", "Keep", {"a": 1})
            # Should not raise
            delete_template("email", "DoesNotExist")
            templates = load_templates("email")
            assert len(templates) == 1

    def test_get_template_names(self):
        """get_template_names returns list of name strings."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, get_template_names
            save_template("email", "Alpha", {"a": 1})
            save_template("email", "Beta", {"b": 2})
            names = get_template_names("email")
            assert "Alpha" in names
            assert "Beta" in names
            assert len(names) == 2

    def test_get_template_data_found(self):
        """get_template_data returns the data dict when found."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, get_template_data
            save_template("email", "MyTemplate", {"subject": "Hello", "body": "World"})
            data = get_template_data("email", "MyTemplate")
            assert data == {"subject": "Hello", "body": "World"}

    def test_get_template_data_not_found(self):
        """get_template_data returns None when template not found."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import get_template_data
            data = get_template_data("email", "NonExistent")
            assert data is None

    def test_import_templates_replaces_all(self):
        """import_templates replaces all data and persists."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, import_templates, load_templates
            save_template("email", "Old", {"x": 1})
            new_data = {
                "inquiry": [
                    {"name": "Imported1", "data": {"y": 2}, "created_at": "2024-01-01 12:00"},
                    {"name": "Imported2", "data": {"z": 3}, "created_at": "2024-01-02 12:00"},
                ]
            }
            import_templates(new_data)
            # Old category gone
            assert load_templates("email") == []
            # New category present
            templates = load_templates("inquiry")
            assert len(templates) == 2
            # Verify persistence
            import json
            data = json.loads((tmp_dir / "templates.json").read_text(encoding="utf-8"))
            assert "inquiry" in data
            assert len(data["inquiry"]) == 2

    def test_multiple_categories_isolated(self):
        """Templates in different categories do not interfere."""
        tmp_dir = self._setup()
        with patch("utils.templates.st", _mock_st), \
             patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.templates import save_template, load_templates, delete_template
            save_template("email", "E1", {"a": 1})
            save_template("inquiry", "I1", {"b": 2})
            save_template("listing", "L1", {"c": 3})
            # Deleting from one category does not affect others
            delete_template("email", "E1")
            assert load_templates("email") == []
            assert len(load_templates("inquiry")) == 1
            assert len(load_templates("listing")) == 1


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestTemplates()
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
