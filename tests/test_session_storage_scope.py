"""Regression tests for storage-scope-aware session JSON caches."""
from __future__ import annotations

import importlib
import tempfile
import types
from pathlib import Path
from unittest.mock import patch


def _fake_streamlit():
    module = types.SimpleNamespace()
    module.session_state = {}
    return module


def test_history_cache_invalidates_when_storage_scope_changes():
    import utils.history as history

    history = importlib.reload(history)
    fake_st = _fake_streamlit()

    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        with patch("utils.history.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(first)):
            history.add_to_history("开发信", "first", "content")
            assert [item["title"] for item in history.get_history()] == ["first"]

        with patch("utils.history.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(second)):
            assert history.get_history() == []
            history.add_to_history("开发信", "second", "content")
            assert [item["title"] for item in history.get_history()] == ["second"]

        with patch("utils.history.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(first)):
            assert [item["title"] for item in history.get_history()] == ["first"]


def test_workflow_cache_invalidates_when_storage_scope_changes():
    import utils.workflow as workflow

    workflow = importlib.reload(workflow)
    fake_st = _fake_streamlit()

    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        with patch("utils.workflow.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(first)):
            workflow.add_workflow("Alice", "LED")
            assert [item["customer"] for item in workflow.get_all_workflows()] == ["Alice"]

        with patch("utils.workflow.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(second)):
            assert workflow.get_all_workflows() == []
            workflow.add_workflow("Bob", "Solar")
            assert [item["customer"] for item in workflow.get_all_workflows()] == ["Bob"]

        with patch("utils.workflow.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(first)):
            assert [item["customer"] for item in workflow.get_all_workflows()] == ["Alice"]


def test_template_cache_invalidates_when_storage_scope_changes():
    import utils.templates as templates

    templates = importlib.reload(templates)
    fake_st = _fake_streamlit()

    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        with patch("utils.templates.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(first)):
            templates.save_template("email", "first", {"subject": "A"})
            assert [item["name"] for item in templates.load_templates("email")] == ["first"]

        with patch("utils.templates.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(second)):
            assert templates.load_templates("email") == []
            templates.save_template("email", "second", {"subject": "B"})
            assert [item["name"] for item in templates.load_templates("email")] == ["second"]

        with patch("utils.templates.st", fake_st), patch("utils.storage.get_data_dir", return_value=Path(first)):
            assert [item["name"] for item in templates.load_templates("email")] == ["first"]
