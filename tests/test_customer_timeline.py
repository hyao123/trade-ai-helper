"""Tests for the unified customer timeline event stream."""
from __future__ import annotations

from unittest.mock import patch


def test_append_event_round_trips(ws_tmp):
    """append_event persists one event; get_timeline retrieves it."""
    from utils.customer_timeline import append_event, get_timeline

    with patch("utils.storage.get_data_dir", return_value=ws_tmp):
        append_event(
            username="alice",
            customer_email="buyer@example.com",
            event_type="lead_captured",
            data={"intent": "inquiry", "source": "email_capture"},
            source="lead_capture",
        )
        timeline = get_timeline("alice", "buyer@example.com")

    assert len(timeline) == 1
    event = timeline[0]
    assert event["customer_email"] == "buyer@example.com"
    assert event["event_type"] == "lead_captured"
    assert event["data"]["intent"] == "inquiry"
    assert event["source"] == "lead_capture"
    assert "event_id" in event
    assert "timestamp" in event


def test_get_timeline_filters_by_email(ws_tmp):
    """get_timeline must return only events for the requested customer."""
    from utils.customer_timeline import append_event, get_timeline

    with patch("utils.storage.get_data_dir", return_value=ws_tmp):
        append_event("alice", "buyer1@x.com", "lead_captured", {}, "src")
        append_event("alice", "buyer2@x.com", "email_sent", {}, "src")
        append_event("alice", "buyer1@x.com", "email_replied", {}, "src")

        timeline_buyer1 = get_timeline("alice", "buyer1@x.com")
        timeline_buyer2 = get_timeline("alice", "buyer2@x.com")

    assert len(timeline_buyer1) == 2
    assert all(e["customer_email"] == "buyer1@x.com" for e in timeline_buyer1)
    assert len(timeline_buyer2) == 1
    assert timeline_buyer2[0]["customer_email"] == "buyer2@x.com"


def test_lead_capture_appends_timeline_event(ws_tmp):
    """A successful lead capture must append a timeline event."""
    from utils.lead_capture import capture_lead_from_email
    from utils.customer_timeline import get_timeline
    import types

    st = types.ModuleType("streamlit")
    st.session_state = {"current_user": {"username": "bob", "tier": "free"}}

    entry = {"id": "e1", "from": "Buyer <b@x.com>", "subject": "Quote", "snippet": ""}
    classification = {"intent": "inquiry", "priority_score": 8}

    with patch("utils.storage.get_data_dir", return_value=ws_tmp), \
         patch("utils.customers.st", st), \
         patch("utils.workflow.st", st), \
         patch("utils.lead_capture.notify_hot_lead"), \
         patch("utils.lead_capture.create_workflow_from_customer", return_value=True):
        result = capture_lead_from_email("bob", entry, classification)
        timeline = get_timeline("bob", "b@x.com")

    assert result["created"] is True
    assert len(timeline) == 1
    event = timeline[0]
    assert event["event_type"] == "lead_captured"
    assert event["customer_email"] == "b@x.com"
    assert event["data"]["intent"] == "inquiry"


def test_send_via_provider_appends_timeline_event(ws_tmp):
    """send_via_provider success must append an email_sent timeline event."""
    import utils.inbox_integration as ii
    from utils.customer_timeline import get_timeline

    with patch("utils.storage.get_data_dir", return_value=ws_tmp), \
         patch.object(ii, "_get_valid_token", return_value="tok"), \
         patch("utils.inbox_integration.load_user_json", return_value={"provider": "gmail"}), \
         patch.object(ii, "_send_gmail", return_value=(True, "sent")), \
         patch("utils.inbox_integration.create_tracking_record", return_value="tid"), \
         patch("utils.inbox_integration.append_outreach_log"):
        ok, _msg = ii.send_via_provider("bob", "customer@y.com", "Re: Quote", "Body")
        timeline = get_timeline("bob", "customer@y.com")

    assert ok is True
    assert len(timeline) == 1
    event = timeline[0]
    assert event["event_type"] == "email_sent"
    assert event["customer_email"] == "customer@y.com"
    assert event["data"]["subject"] == "Re: Quote"
    assert event["source"] == "inbox"


def test_send_inbound_reply_appends_timeline_event(ws_tmp):
    """send_inbound_reply success must append an email_replied timeline event."""
    from utils import inbound_email
    from utils.customer_timeline import get_timeline

    inbound = {"id": "inb1", "from_name": "C", "from_email": "c@z.com", "subject": "Inquiry", "body": "..."}

    with patch("utils.storage.get_data_dir", return_value=ws_tmp), \
         patch.object(inbound_email, "get_inbound_email", return_value=inbound), \
         patch("utils.inbound_email.send_ai_generated_email", return_value=(True, "ok")), \
         patch("utils.inbound_email.update_inbound_status"), \
         patch("utils.inbound_email.append_outreach_log"):
        ok, _msg = inbound_email.send_inbound_reply("bob", "inb1", "Here is the answer")
        timeline = get_timeline("bob", "c@z.com")

    assert ok is True
    assert len(timeline) == 1
    event = timeline[0]
    assert event["event_type"] == "email_replied"
    assert event["customer_email"] == "c@z.com"
    assert event["data"]["inbound_id"] == "inb1"
    assert event["source"] == "inbound"