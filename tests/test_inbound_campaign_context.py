"""Tests for inbound inquiry reply with campaign product/company context (B7)."""
from __future__ import annotations

from unittest.mock import patch


def test_reply_inquiry_with_product_context():
    """reply_inquiry with product_info must include it in the prompt."""
    from utils.ai_client import reply_inquiry
    from config.prompts import build_inquiry_prompt

    inquiry = "What's your MOQ?"
    product_info = "LED Desk Lamp, 3W, USB-C, MOQ 500pcs"
    company_intro = "ABC Lighting Co., Est. 2010, ISO9001"

    prompt, _system = build_inquiry_prompt(
        inquiry,
        customer_name="John",
        your_name="Alice",
        company_name="ABC Co",
        product_info=product_info,
        company_intro=company_intro,
    )
    assert "LED Desk Lamp" in prompt
    assert "MOQ 500pcs" in prompt
    assert "ISO9001" in prompt or "ABC Lighting" in prompt


def test_reply_inquiry_without_product_context():
    """reply_inquiry without product_info must still generate a valid reply (backward compat)."""
    from config.prompts import build_inquiry_prompt

    prompt, system = build_inquiry_prompt(
        "What's your price?",
        customer_name="Bob",
        your_name="Alice",
        company_name="Trade Inc",
    )
    assert "Bob" in prompt or "客户" in prompt
    assert "Alice" in prompt or "Your Name" in prompt
    assert system  # system prompt exists


def test_seed_inquiry_with_campaign():
    """seed_inquiry_session_state with campaign_id must store it in session."""
    from utils.inbound_email import seed_inquiry_session_state
    import types

    st = types.ModuleType("streamlit")
    st.session_state = {}

    inbound = {
        "id": "inb1",
        "from_name": "Customer",
        "from_email": "c@x.com",
        "subject": "Inquiry",
        "body": "What is your MOQ?",
        "campaign_id": "camp123",
    }
    seed_inquiry_session_state(st, inbound)

    assert st.session_state["inquiry_text_val"] == "Subject: Inquiry\n\nWhat is your MOQ?"
    assert st.session_state["inquiry_customer_val"] == "Customer"
    assert st.session_state.get("inquiry_campaign_id") == "camp123"


def test_seed_inquiry_without_campaign():
    """seed_inquiry_session_state without campaign_id must not crash."""
    from utils.inbound_email import seed_inquiry_session_state
    import types

    st = types.ModuleType("streamlit")
    st.session_state = {}

    inbound = {
        "id": "inb2",
        "from_name": "Buyer",
        "from_email": "b@y.com",
        "subject": "Question",
        "body": "Price?",
    }
    seed_inquiry_session_state(st, inbound)

    assert st.session_state["inquiry_text_val"] == "Subject: Question\n\nPrice?"
    assert "inquiry_campaign_id" not in st.session_state or st.session_state["inquiry_campaign_id"] is None