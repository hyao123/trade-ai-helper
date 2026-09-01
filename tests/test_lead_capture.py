"""Tests for automatic lead capture from classified inquiry emails."""
from __future__ import annotations

import types
from unittest.mock import patch


def _make_st(username: str = "bob"):
    """Return a fresh streamlit stub with a signed-in session (no shared state)."""
    st = types.ModuleType("streamlit")
    st.session_state = {"current_user": {"username": username, "tier": "free"}}
    return st


def _entry(intent: str, from_field: str = "Acme <sales@acme.com>", priority: int = 8):
    return {
        "email_id": "e1",
        "email": {"id": "e1", "from": from_field, "subject": "Quote please", "snippet": "..."},
        "classification": {"intent": intent, "priority_score": priority},
    }


def test_capture_creates_customer_workflow_and_notifies(ws_tmp):
    """High-intent inquiry captures a CRM customer, a workflow, and a hot-lead notification."""
    from utils.lead_capture import capture_lead_from_email

    st = _make_st()
    with patch("utils.storage.get_data_dir", return_value=ws_tmp), \
         patch("utils.customers.st", st), \
         patch("utils.workflow.st", st), \
         patch("utils.lead_capture.notify_hot_lead", return_value="n1") as mock_notify, \
         patch("utils.lead_capture.create_workflow_from_customer", return_value=True) as mock_wf:
        result = capture_lead_from_email("bob", _entry("inquiry")["email"], _entry("inquiry")["classification"])

    assert result["created"] is True
    customer = result["customer"]
    assert customer["email"] == "sales@acme.com"
    assert customer["company"] == "Acme"
    assert customer["stage"] == "新客户"
    assert customer["source"] == "email_capture"
    mock_wf.assert_called_once()
    mock_notify.assert_called_once()


def test_capture_deduplicates_by_email(ws_tmp):
    """The same sender email must only be captured once."""
    from utils.lead_capture import capture_lead_from_email

    st = _make_st()
    with patch("utils.storage.get_data_dir", return_value=ws_tmp), \
         patch("utils.customers.st", st), \
         patch("utils.workflow.st", st), \
         patch("utils.lead_capture.notify_hot_lead"), \
         patch("utils.lead_capture.create_workflow_from_customer", return_value=True):
        first = capture_lead_from_email("bob", _entry("inquiry")["email"], _entry("inquiry")["classification"])
        second = capture_lead_from_email("bob", _entry("inquiry")["email"], _entry("inquiry")["classification"])

    assert first["created"] is True
    assert second["created"] is False
    assert second["reason"] == "duplicate"


def test_capture_skips_low_intent(ws_tmp):
    """info_only / low-priority mail must not create a lead."""
    from utils.lead_capture import capture_lead_from_email

    st = _make_st()
    with patch("utils.storage.get_data_dir", return_value=ws_tmp), \
         patch("utils.customers.st", st), \
         patch("utils.workflow.st", st), \
         patch("utils.lead_capture.notify_hot_lead"), \
         patch("utils.lead_capture.create_workflow_from_customer") as mock_wf:
        result = capture_lead_from_email(
            "bob",
            _entry("info_only")["email"],
            _entry("info_only")["classification"],
        )

    assert result["created"] is False
    assert result["reason"] == "low_intent"
    mock_wf.assert_not_called()


def test_capture_skips_missing_email(ws_tmp):
    """A sender without an email address cannot be captured."""
    from utils.lead_capture import capture_lead_from_email

    st = _make_st()
    entry_email = {"id": "e2", "from": "noemail", "subject": "x", "snippet": ""}
    with patch("utils.storage.get_data_dir", return_value=ws_tmp), \
         patch("utils.customers.st", st), \
         patch("utils.workflow.st", st), \
         patch("utils.lead_capture.notify_hot_lead"), \
         patch("utils.lead_capture.create_workflow_from_customer") as mock_wf:
        result = capture_lead_from_email("bob", entry_email, {"intent": "complaint"})

    assert result["created"] is False
    assert result["reason"] == "no_email"
    mock_wf.assert_not_called()


def test_process_inbox_with_lead_capture_wires_capture():
    """process_inbox_with_lead_capture classifies and captures, returning processed."""
    from utils import inbox_ai

    processed = [_entry("inquiry")]
    with patch.object(inbox_ai, "process_inbox", return_value=processed) as mock_pi, \
         patch("utils.inbox_ai.capture_leads_from_inbox") as mock_capture:
        out = inbox_ai.process_inbox_with_lead_capture("bob", [{"id": "e1"}])

    assert out == processed
    mock_pi.assert_called_once()
    mock_capture.assert_called_once_with("bob", processed)


def test_process_inbox_with_lead_capture_swallows_capture_errors():
    """Capture failures must not break the classification result."""
    from utils import inbox_ai

    processed = [_entry("inquiry")]
    with patch.object(inbox_ai, "process_inbox", return_value=processed), \
         patch("utils.inbox_ai.capture_leads_from_inbox", side_effect=RuntimeError("boom")):
        out = inbox_ai.process_inbox_with_lead_capture("bob", [{"id": "e1"}])

    assert out == processed