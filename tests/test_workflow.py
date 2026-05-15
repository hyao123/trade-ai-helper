"""
tests/test_workflow.py
Unit tests for utils/workflow.py - email follow-up workflow management.
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that use it
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st


class TestWorkflow:
    """Tests for utils/workflow.py workflow management functions."""

    def _setup(self):
        """Reset mock state and create auto-cleaning temp dir."""
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_add_workflow_creates_correct_structure(self):
        """add_workflow creates entry with all required fields."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import add_workflow, get_all_workflows
                add_workflow("John", "LED Lamp", "ABC Corp", "john@abc.com", "Test notes")
                wfs = get_all_workflows()
                assert len(wfs) == 1
                wf = wfs[0]
                assert "id" in wf
                assert wf["customer"] == "John"
                assert wf["product"] == "LED Lamp"
                assert wf["company"] == "ABC Corp"
                assert wf["email"] == "john@abc.com"
                assert wf["notes"] == "Test notes"
                assert "sent_at" in wf
                assert "sent_ts" in wf
                assert wf["status"] == "进行中"
                assert wf["followups"] == []

    def test_add_workflow_inserts_at_front(self):
        """Newest workflow is at position 0."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import add_workflow, get_all_workflows
                add_workflow("First", "Product1", "Co1")
                add_workflow("Second", "Product2", "Co2")
                wfs = get_all_workflows()
                assert wfs[0]["customer"] == "Second"
                assert wfs[1]["customer"] == "First"

    def test_get_all_workflows_empty(self):
        """Returns empty list when no workflows exist."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import get_all_workflows
                assert get_all_workflows() == []

    def test_get_all_workflows_returns_all(self):
        """Returns all added workflows."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import add_workflow, get_all_workflows
                add_workflow("A", "P1", "C1")
                add_workflow("B", "P2", "C2")
                add_workflow("C", "P3", "C3")
                assert len(get_all_workflows()) == 3

    def test_get_due_workflows_none_due(self):
        """Workflow just created should not be due."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import add_workflow, get_due_workflows
                add_workflow("John", "LED Lamp", "ABC")
                due = get_due_workflows()
                assert len(due) == 0

    def test_get_due_workflows_3_day_rule(self):
        """Workflow sent 4 days ago should be due (3-day rule)."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import get_due_workflows
                # Manually insert a workflow with sent_ts 4 days ago
                four_days_ago = datetime.now() - timedelta(days=4)
                _mock_st.session_state["email_workflows"] = [{
                    "id": "wf_test_1",
                    "customer": "John",
                    "product": "LED Lamp",
                    "company": "ABC",
                    "email": "john@abc.com",
                    "notes": "",
                    "sent_at": four_days_ago.strftime("%Y-%m-%d"),
                    "sent_ts": four_days_ago.timestamp(),
                    "status": "进行中",
                    "followups": [],
                }]
                _mock_st.session_state["_workflows_loaded_from_disk"] = True
                due = get_due_workflows()
                assert len(due) == 1
                assert due[0]["customer"] == "John"
                assert due[0]["_rule"]["label"] == "3天跟进"

    def test_get_due_workflows_skips_closed(self):
        """Closed workflows should not be returned as due."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import get_due_workflows
                four_days_ago = datetime.now() - timedelta(days=4)
                _mock_st.session_state["email_workflows"] = [{
                    "id": "wf_closed_1",
                    "customer": "John",
                    "product": "LED Lamp",
                    "company": "ABC",
                    "email": "",
                    "notes": "",
                    "sent_at": four_days_ago.strftime("%Y-%m-%d"),
                    "sent_ts": four_days_ago.timestamp(),
                    "status": "已关闭",
                    "followups": [],
                }]
                _mock_st.session_state["_workflows_loaded_from_disk"] = True
                due = get_due_workflows()
                assert len(due) == 0

    def test_mark_followup_done(self):
        """mark_followup_done adds entry to followups list."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import (
                    add_workflow,
                    get_all_workflows,
                    mark_followup_done,
                )
                add_workflow("John", "LED Lamp", "ABC")
                wfs = get_all_workflows()
                wf_id = wfs[0]["id"]
                mark_followup_done(wf_id, "3天跟进")
                wfs = get_all_workflows()
                assert len(wfs[0]["followups"]) == 1
                assert wfs[0]["followups"][0]["stage_label"] == "3天跟进"
                assert "done_at" in wfs[0]["followups"][0]

    def test_mark_followup_done_nonexistent_id(self):
        """mark_followup_done with nonexistent ID causes no error."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import (
                    add_workflow,
                    get_all_workflows,
                    mark_followup_done,
                )
                add_workflow("John", "LED Lamp", "ABC")
                # Should not raise
                mark_followup_done("nonexistent_id", "3天跟进")
                wfs = get_all_workflows()
                assert wfs[0]["followups"] == []

    def test_update_workflow_status(self):
        """update_workflow_status changes the status field."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import (
                    add_workflow,
                    get_all_workflows,
                    update_workflow_status,
                )
                add_workflow("John", "LED Lamp", "ABC")
                wfs = get_all_workflows()
                wf_id = wfs[0]["id"]
                update_workflow_status(wf_id, "已回复")
                wfs = get_all_workflows()
                assert wfs[0]["status"] == "已回复"

    def test_get_workflow_stats(self):
        """get_workflow_stats returns correct counts."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import (
                    add_workflow,
                    get_all_workflows,
                    get_workflow_stats,
                    update_workflow_status,
                )
                add_workflow("A", "P1", "C1")
                add_workflow("B", "P2", "C2")
                add_workflow("C", "P3", "C3")
                wfs = get_all_workflows()
                update_workflow_status(wfs[0]["id"], "已回复")
                stats = get_workflow_stats()
                assert stats["total"] == 3
                assert stats["active"] == 2
                assert stats["replied"] == 1

    def test_find_workflow_by_customer_found(self):
        """find_workflow_by_customer returns matching workflow."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import add_workflow, find_workflow_by_customer
                add_workflow("John Smith", "LED Lamp", "ABC Trading", "john@abc.com")
                result = find_workflow_by_customer("John Smith", "ABC Trading")
                assert result is not None
                assert result["customer"] == "John Smith"
                assert result["company"] == "ABC Trading"

    def test_find_workflow_by_customer_not_found(self):
        """find_workflow_by_customer returns None when not found."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import find_workflow_by_customer
                result = find_workflow_by_customer("Nobody", "Ghost Corp")
                assert result is None

    def test_create_workflow_from_customer_success(self):
        """create_workflow_from_customer returns True and creates workflow."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import (
                    create_workflow_from_customer,
                    get_all_workflows,
                )
                customer_data = {
                    "company": "ABC Trading",
                    "contact": "John Smith",
                    "email": "john@abc.com",
                    "product": "LED Lamp",
                }
                result = create_workflow_from_customer(customer_data)
                assert result is True
                wfs = get_all_workflows()
                assert len(wfs) == 1
                assert wfs[0]["customer"] == "John Smith"

    def test_create_workflow_from_customer_duplicate(self):
        """create_workflow_from_customer returns False on duplicate."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import (
                    create_workflow_from_customer,
                    get_all_workflows,
                )
                customer_data = {
                    "company": "ABC Trading",
                    "contact": "John Smith",
                    "email": "john@abc.com",
                    "product": "LED Lamp",
                }
                create_workflow_from_customer(customer_data)
                result = create_workflow_from_customer(customer_data)
                assert result is False
                assert len(get_all_workflows()) == 1

    def test_import_workflows_replaces_data(self):
        """import_workflows replaces existing data and persists."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.workflow.st", _mock_st), \
                 patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.workflow import (
                    add_workflow,
                    get_all_workflows,
                    import_workflows,
                )
                add_workflow("Old", "OldProduct", "OldCo")
                new_data = [
                    {
                        "id": "wf_imported_1",
                        "customer": "Imported",
                        "product": "NewProduct",
                        "company": "NewCo",
                        "email": "new@co.com",
                        "notes": "",
                        "sent_at": "2024-01-01",
                        "sent_ts": 1704067200.0,
                        "status": "进行中",
                        "followups": [],
                    }
                ]
                import_workflows(new_data)
                wfs = get_all_workflows()
                assert len(wfs) == 1
                assert wfs[0]["customer"] == "Imported"
                # Verify persistence
                import json
                data = json.loads((tmp_dir / "workflows.json").read_text(encoding="utf-8"))
                assert len(data) == 1
                assert data[0]["customer"] == "Imported"


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestWorkflow()
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
