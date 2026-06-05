"""Tests for inbound email intake phase 1."""
from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_mock_st = types.SimpleNamespace(session_state={})


def test_parse_raw_email_with_headers():
    from utils.inbound_email import parse_raw_email_text

    raw = """From: Mike Johnson <mike@example.com>
To: sales@example.com
Subject: Inquiry for LED lights
Date: Fri, 5 Jun 2026 10:00:00 +0000
Message-ID: <msg-1@example.com>

Hi,
Please quote LED street lights.
"""
    parsed = parse_raw_email_text(raw)
    assert parsed["from_name"] == "Mike Johnson"
    assert parsed["from_email"] == "mike@example.com"
    assert parsed["subject"] == "Inquiry for LED lights"
    assert "Please quote" in parsed["body"]
    assert parsed["fingerprint"]


def test_parse_body_only_text():
    from utils.inbound_email import parse_raw_email_text

    parsed = parse_raw_email_text("Hello, please send your catalog.")
    assert parsed["source"] == "pasted_body"
    assert parsed["from_email"] == ""
    assert parsed["subject"] == ""
    assert parsed["body"] == "Hello, please send your catalog."


def test_parse_eml_bytes_extracts_text_body():
    from utils.inbound_email import parse_eml_bytes

    eml = b"From: Sarah <sarah@example.com>\nTo: sales@example.com\nSubject: Price list\nMessage-ID: <msg-2@example.com>\nContent-Type: text/plain; charset=utf-8\n\nCan you share the price list?"
    parsed = parse_eml_bytes(eml)
    assert parsed["from_name"] == "Sarah"
    assert parsed["from_email"] == "sarah@example.com"
    assert parsed["subject"] == "Price list"
    assert "price list" in parsed["body"]


def test_create_inbound_record_is_idempotent_and_lists_pending():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.inbound_email import create_inbound_record, list_inbound_emails, parse_raw_email_text

            parsed = parse_raw_email_text("From: Buyer <buyer@example.com>\nSubject: Need quote\n\nPlease quote MOQ.")
            created1, record1 = create_inbound_record("seller", parsed, customer_id="cust1")
            created2, record2 = create_inbound_record("seller", parsed, customer_id="cust1")

            assert created1 is True
            assert created2 is False
            assert record1["id"] == record2["id"]
            assert record1["status"] == "pending"
            assert record1["customer_id"] == "cust1"

            pending = list_inbound_emails("seller", status="pending")
            assert len(pending) == 1
            assert pending[0]["from_email"] == "buyer@example.com"


def test_update_status_and_seed_inquiry_session_state():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            from utils.inbound_email import (
                create_inbound_record,
                get_inbound_email,
                parse_raw_email_text,
                seed_inquiry_session_state,
                update_inbound_status,
            )

            parsed = parse_raw_email_text("From: Buyer <buyer@example.com>\nSubject: Need quote\n\nPlease quote MOQ.")
            _, record = create_inbound_record("seller", parsed)
            assert update_inbound_status("seller", record["id"], "drafted") is True
            updated = get_inbound_email("seller", record["id"])
            assert updated is not None
            assert updated["status"] == "drafted"

            _mock_st.session_state.clear()
            seed_inquiry_session_state(_mock_st, updated)
            assert "Subject: Need quote" in _mock_st.session_state["inquiry_text_val"]
            assert "Please quote MOQ" in _mock_st.session_state["inquiry_text_val"]
            assert _mock_st.session_state["inquiry_customer_val"] == "Buyer"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS: {name}")
