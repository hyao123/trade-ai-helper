"""
tests/test_history.py
Unit tests for utils/history.py - generation history management.
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


class TestHistory:
    """Tests for utils/history.py history management functions."""

    def _setup(self):
        """Reset mock state and create auto-cleaning temp dir."""
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_add_to_history_basic(self):
        """add_to_history creates an entry with correct fields."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                add_to_history("开发信", "Test Product", "Generated content here", {"lang": "en"})
                items = get_history()
                assert len(items) == 1
                item = items[0]
                assert item["feature"] == "开发信"
                assert item["title"] == "Test Product"
                assert item["content"] == "Generated content here"
                assert item["params"] == {"lang": "en"}
                assert "timestamp" in item

    def test_add_to_history_inserts_at_front(self):
        """Newest entry is at position 0."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                add_to_history("开发信", "First", "content1")
                add_to_history("开发信", "Second", "content2")
                items = get_history()
                assert items[0]["title"] == "Second"
                assert items[1]["title"] == "First"

    def test_add_to_history_default_params_empty_dict(self):
        """When params=None, stored as empty dict."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                add_to_history("开发信", "Test", "content", None)
                items = get_history()
                assert items[0]["params"] == {}

    def test_add_to_history_caps_at_50(self):
        """Adding more than 50 items keeps only 50."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history_count
                for i in range(55):
                    add_to_history("开发信", f"Item {i}", f"content {i}")
                count = get_history_count()
                assert count == 50

    def test_get_history_all(self):
        """get_history returns all items when feature=None."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                add_to_history("开发信", "A", "content")
                add_to_history("询盘回复", "B", "content")
                add_to_history("产品上架", "C", "content")
                items = get_history(feature=None)
                assert len(items) == 3

    def test_get_history_filter_by_feature(self):
        """get_history filters by feature name."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                add_to_history("开发信", "A", "content")
                add_to_history("询盘回复", "B", "content")
                add_to_history("开发信", "C", "content")
                items = get_history(feature="开发信")
                assert len(items) == 2
                assert all(i["feature"] == "开发信" for i in items)

    def test_get_history_limit(self):
        """get_history respects limit parameter."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                for i in range(10):
                    add_to_history("开发信", f"Item {i}", "content")
                items = get_history(limit=3)
                assert len(items) == 3

    def test_clear_history(self):
        """clear_history empties the list and persists empty array."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, clear_history, get_history_count
                add_to_history("开发信", "A", "content")
                add_to_history("开发信", "B", "content")
                clear_history()
                assert get_history_count() == 0
                # Verify persisted to disk
                import json
                data = json.loads((tmp_dir / "history.json").read_text(encoding="utf-8"))
                assert data == []

    def test_get_history_count(self):
        """get_history_count returns accurate count."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history_count
                assert get_history_count() == 0
                add_to_history("开发信", "A", "content")
                assert get_history_count() == 1
                add_to_history("开发信", "B", "content")
                assert get_history_count() == 2

    def test_import_history_replaces_data(self):
        """import_history replaces existing data and persists."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, import_history, get_history, get_history_count
                add_to_history("开发信", "Old", "old content")
                new_data = [
                    {"feature": "询盘回复", "title": "New1", "content": "c1", "params": {}, "timestamp": "2024-01-01 12:00"},
                    {"feature": "询盘回复", "title": "New2", "content": "c2", "params": {}, "timestamp": "2024-01-02 12:00"},
                ]
                import_history(new_data)
                assert get_history_count() == 2
                items = get_history()
                assert items[0]["title"] == "New1"
                assert items[1]["title"] == "New2"
                # Verify persisted to disk
                import json
                data = json.loads((tmp_dir / "history.json").read_text(encoding="utf-8"))
                assert len(data) == 2

    def test_persistence_round_trip(self):
        """Data added persists to disk and survives session_state reset."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                add_to_history("开发信", "Persist Test", "my content", {"key": "val"})
                # Simulate a fresh session by clearing session_state
                _mock_st.session_state.clear()
                items = get_history()
                assert len(items) == 1
                assert items[0]["title"] == "Persist Test"
                assert items[0]["params"] == {"key": "val"}

    def test_add_to_history_timestamp_format(self):
        """Timestamp follows YYYY-MM-DD HH:MM format."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.history.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.history import add_to_history, get_history
                import re
                add_to_history("开发信", "TS Test", "content")
                items = get_history()
                ts = items[0]["timestamp"]
                assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", ts)


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestHistory()
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
