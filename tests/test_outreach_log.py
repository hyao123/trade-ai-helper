"""Tests for the unified outreach log and outbound reply recording."""
from __future__ import annotations

from unittest.mock import patch


def test_append_outreach_log_round_trips(ws_tmp):
    """append_outreach_log persists to the user's log file; get reads it back."""
    from utils.outreach_log import append_outreach_log, get_outreach_logs

    with patch("utils.storage.get_data_dir", return_value=ws_tmp):
        append_outreach_log("bob", {
            "direction": "out",
            "source": "inbound",
            "to_email": "customer@example.com",
            "subject": "Re: Quote",
            "status": "sent",
            "timestamp": "2026-01-01T00:00:00",
        })
        logs = get_outreach_logs("bob")
        assert len(logs) == 1
        assert logs[0]["to_email"] == "customer@example.com"
        assert logs[0]["source"] == "inbound"


def test_send_via_provider_records_tracking_and_log():
    """A successful provider send must create a tracking record and log it."""
    import utils.inbox_integration as ii

    with patch.object(ii, "_get_valid_token", return_value="tok"), \
         patch("utils.inbox_integration.load_user_json", return_value={"provider": "gmail"}), \
         patch.object(ii, "_send_gmail", return_value=(True, "sent")), \
         patch("utils.inbox_integration.create_tracking_record", return_value="tid_abc") as mock_tr, \
         patch("utils.inbox_integration.append_outreach_log") as mock_log:
        ok, msg = ii.send_via_provider("bob", "c@example.com", "Re: Quote", "Body")

    assert ok is True
    mock_tr.assert_called_once_with(user_id="bob", to_email="c@example.com", subject="Re: Quote")
    mock_log.assert_called_once()
    event = mock_log.call_args.args[1]
    assert event["tracking_id"] == "tid_abc"
    assert event["source"] == "inbox"
    assert event["direction"] == "out"
    assert event["status"] == "sent"


def test_send_via_provider_failure_does_not_log():
    """A failed provider send must not create tracking or write a log entry."""
    import utils.inbox_integration as ii

    with patch.object(ii, "_get_valid_token", return_value="tok"), \
         patch("utils.inbox_integration.load_user_json", return_value={"provider": "gmail"}), \
         patch.object(ii, "_send_gmail", return_value=(False, "api error")), \
         patch("utils.inbox_integration.create_tracking_record") as mock_tr, \
         patch("utils.inbox_integration.append_outreach_log") as mock_log:
        ok, msg = ii.send_via_provider("bob", "c@example.com", "Re: Quote", "Body")

    assert ok is False
    mock_tr.assert_not_called()
    mock_log.assert_not_called()


def test_send_inbound_reply_sends_and_marks_replied():
    """send_inbound_reply sends via email_service, marks replied, and logs."""
    from utils import inbound_email

    inbound = {
        "id": "inb_1",
        "from_name": "Customer",
        "from_email": "customer@example.com",
        "subject": "Interested in LED",
        "body": "Please quote 5000 units",
    }

    with patch.object(inbound_email, "get_inbound_email", return_value=inbound), \
         patch("utils.inbound_email.send_ai_generated_email", return_value=(True, "ok")) as mock_send, \
         patch("utils.inbound_email.update_inbound_status") as mock_status, \
         patch("utils.inbound_email.append_outreach_log") as mock_log:
        ok, msg = inbound_email.send_inbound_reply("bob", "inb_1", "Here is our quote...")

    assert ok is True
    mock_send.assert_called_once()
    sent_to = mock_send.call_args.kwargs.get("to_email")
    assert sent_to == "customer@example.com"
    mock_status.assert_called_once_with("bob", "inb_1", "replied")
    mock_log.assert_called_once()
    event = mock_log.call_args.args[1]
    assert event["source"] == "inbound"
    assert event["status"] == "sent"
    assert event["to_email"] == "customer@example.com"


def test_send_inbound_reply_missing_email_returns_error():
    """send_inbound_reply must fail cleanly when the inbound record is unknown."""
    from utils import inbound_email

    with patch.object(inbound_email, "get_inbound_email", return_value=None), \
         patch("utils.inbound_email.send_ai_generated_email") as mock_send, \
         patch("utils.inbound_email.append_outreach_log") as mock_log:
        ok, msg = inbound_email.send_inbound_reply("bob", "nope", "reply")

    assert ok is False
    mock_send.assert_not_called()
    mock_log.assert_not_called()


def test_send_inbound_reply_prepends_re_subject():
    """A subject without the Re: prefix gets one; an existing prefix is kept."""
    from utils import inbound_email

    inbound = {"id": "inb_2", "from_name": "C", "from_email": "c@x.com", "subject": "Quote please"}

    with patch.object(inbound_email, "get_inbound_email", return_value=inbound), \
         patch("utils.inbound_email.send_ai_generated_email", return_value=(True, "ok")) as mock_send, \
         patch("utils.inbound_email.update_inbound_status"), \
         patch("utils.inbound_email.append_outreach_log"):
        inbound_email.send_inbound_reply("bob", "inb_2", "body")
        assert mock_send.call_args.kwargs["subject"] == "Re: Quote please"

    with patch.object(inbound_email, "get_inbound_email", return_value={**inbound, "subject": "Re: Quote please"}), \
         patch("utils.inbound_email.send_ai_generated_email", return_value=(True, "ok")) as mock_send2, \
         patch("utils.inbound_email.update_inbound_status"), \
         patch("utils.inbound_email.append_outreach_log"):
        inbound_email.send_inbound_reply("bob", "inb_2", "body")
        assert mock_send2.call_args.kwargs["subject"] == "Re: Quote please"