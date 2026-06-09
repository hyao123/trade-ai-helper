"""Tests for account backup bundle construction."""
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


def test_backup_bundle_loads_persisted_user_data_without_session_preload():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        _mock_st.session_state.clear()
        _mock_st.session_state["current_user"] = {"username": "backupuser", "tier": "pro"}

        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.storage import save_user_json

            save_user_json("backupuser", "customers.json", [{"company": "ABC Trading"}])
            save_user_json("backupuser", "history.json", [{"title": "Inquiry reply"}])
            save_user_json("backupuser", "templates.json", {"email": [{"name": "Intro"}]})
            save_user_json("backupuser", "workflows.json", [{"customer": "Ada"}])

            from utils import backup, customers, history, templates, workflow

            with patch.object(customers, "st", _mock_st), \
                 patch.object(history, "st", _mock_st), \
                 patch.object(templates, "st", _mock_st), \
                 patch.object(workflow, "st", _mock_st):
                bundle = backup.build_backup_bundle()

        assert bundle["version"] == "1.0"
        assert bundle["customers"] == [{"company": "ABC Trading"}]
        assert bundle["history"] == [{"title": "Inquiry reply"}]
        assert bundle["templates"] == {"email": [{"name": "Intro"}]}
        assert bundle["workflows"] == [{"customer": "Ada"}]
        assert "customers_backupuser" in _mock_st.session_state
        assert "email_workflows_backupuser" in _mock_st.session_state
