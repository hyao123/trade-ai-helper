"""Tests for unified intent taxonomy across inbox classification and auto-reply."""
from __future__ import annotations

from unittest.mock import patch


def test_normalize_reply_intent_maps_legacy_phrases():
    """Old English reply-intent phrases must map onto canonical inbox intent keys."""
    from utils.inbox_ai import normalize_reply_intent

    cases = {
        "Interested": "inquiry",
        "Needs Info": "inquiry",
        "Price Negotiation": "negotiation",
        "Sample Request": "sample_request",
        "Purchase Intent": "order_intent",
        "Not Interested": "info_only",
        "Auto-Reply": "info_only",
        "Other": "info_only",
    }
    for phrase, expected in cases.items():
        assert normalize_reply_intent(phrase) == expected, f"{phrase!r} -> {expected}"


def test_normalize_reply_intent_passes_new_keys_and_unknown_fallback():
    """Canonical keys pass through; unknown tokens fall back to info_only."""
    from utils.inbox_ai import normalize_reply_intent

    assert normalize_reply_intent("order_intent") == "order_intent"
    assert normalize_reply_intent("  complaint  ") == "complaint"
    assert normalize_reply_intent("gibberish_token") == "info_only"
    assert normalize_reply_intent("") == "info_only"


def test_intent_label_returns_chinese_label_with_fallback():
    """intent_label resolves the canonical label and falls back to the key."""
    from utils.inbox_ai import intent_label

    assert intent_label("order_intent") == "下单意向"
    assert intent_label("not_a_real_key") == "not_a_real_key"


def test_auto_reply_returns_canonical_intent_and_label():
    """auto_reply_to_customer must normalize the AI intent into a canonical key."""
    from utils import auto_outreach

    ai_output = (
        "INTENT: Purchase Intent\n"
        "REPLY_SUBJECT: Re: Your order\n"
        "REPLY_BODY: Great news, here is the PI\n"
    )
    with patch.object(auto_outreach, "get_campaign", return_value={"product_info": "P", "company_intro": "C", "name": "N", "forward_email": ""}), \
         patch("utils.ai_client.call_llm", return_value=ai_output) as mock_llm, \
         patch.object(auto_outreach, "_check_importance", return_value=True) as mock_imp, \
         patch.object(auto_outreach, "_log_outreach_event"):
        result = auto_outreach.auto_reply_to_customer(
            customer_email="buyer@x.com", customer_message="send PI please",
            campaign_id="c1", username="bob",
        )

    assert result["intent"] == "order_intent"
    assert result["intent_label"] == "下单意向"
    assert mock_llm.called
    # importance check receives the canonical key, not the raw phrase
    assert mock_imp.call_args.args[1] == "order_intent"


def test_check_importance_uses_canonical_intent_keys():
    """Importance is decided by canonical high-priority intent keys."""
    from utils.auto_outreach import _check_importance

    assert _check_importance("please send PI", "order_intent") is True
    assert _check_importance("we want a sample", "sample_request") is True
    assert _check_importance("thanks", "info_only") is False


def test_check_importance_still_uses_content_keywords():
    """Content keywords remain a signal even for low-intent classifications."""
    from utils.auto_outreach import _check_importance
    from utils.auto_outreach_config import IMPORTANT_KEYWORDS

    keyword = IMPORTANT_KEYWORDS[0]
    assert _check_importance(f"we need {keyword} urgently", "info_only") is True


def test_auto_reply_prompt_uses_canonical_intent_enum():
    """The auto-reply prompt must instruct canonical keys, not old English phrases."""
    from config.prompts import build_auto_reply_prompt

    prompt, _system = build_auto_reply_prompt(
        customer_email="a@b.com",
        customer_message="Is there a quote?",
        product_info="Product",
        company_intro="Company",
    )
    assert "order_intent" in prompt
    assert "sample_request" in prompt
    assert "Interested" not in prompt