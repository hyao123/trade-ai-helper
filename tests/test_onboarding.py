"""Tests for onboarding and home next-action helpers."""
from __future__ import annotations

from pathlib import Path


def _complete_prefs(**extra):
    prefs = {
        "company_name": "ABC Export Ltd.",
        "contact_name": "Alice",
        "default_product": "LED Street Light",
        "main_products": "LED lights, flood lights",
        "company_description": "ISO-certified exporter.",
        "onboarding_completed": "true",
    }
    prefs.update(extra)
    return prefs


def test_profile_completion_reports_missing_fields():
    from utils.onboarding import profile_completion

    completion = profile_completion({"company_name": "ABC"})

    assert completion["completed"] == 1
    assert completion["total"] == 5
    assert completion["complete"] is False
    assert "default_product" in completion["missing"]
    assert completion["missing_labels"][:2] == ["联系人", "默认产品"]
    assert completion["next_missing_label"] == "联系人"


def test_home_next_actions_prioritize_email_verification_and_setup():
    from utils.onboarding import build_home_next_actions

    actions = build_home_next_actions(
        user={"username": "seller", "email": "seller@example.com", "email_verified": False},
        prefs={"company_name": "ABC"},
        customer_count=0,
    )

    assert [action["id"] for action in actions] == [
        "verify_email",
        "quick_setup",
        "add_customer",
        "dashboard",
    ]
    assert actions[0]["priority"] == "primary"
    assert actions[1]["detail"].startswith("1/5，还差：")


def test_home_next_actions_require_email_even_when_empty():
    from utils.onboarding import build_home_next_actions

    actions = build_home_next_actions(
        user={"username": "seller", "email": "", "email_verified": False},
        prefs=_complete_prefs(),
        customer_count=1,
    )

    assert actions[0]["id"] == "verify_email"
    assert actions[0]["priority"] == "primary"


def test_home_next_actions_offer_generation_after_profile_completion():
    from utils.onboarding import build_home_next_actions

    actions = build_home_next_actions(
        user={"username": "seller", "email": "seller@example.com", "email_verified": True},
        prefs=_complete_prefs(),
        customer_count=0,
    )

    assert [action["id"] for action in actions] == ["cold_email", "add_customer", "dashboard"]
    assert actions[0]["priority"] == "primary"


def test_home_next_actions_skip_customer_prompt_when_customers_exist():
    from utils.onboarding import build_home_next_actions

    actions = build_home_next_actions(
        user={"username": "seller", "email": "seller@example.com", "email_verified": True},
        prefs=_complete_prefs(),
        customer_count=2,
    )

    assert [action["id"] for action in actions] == ["cold_email", "follow_up", "dashboard"]
    assert "2 个客户" in actions[1]["detail"]


def test_home_next_actions_hidden_for_admin_or_anonymous():
    from utils.onboarding import build_home_next_actions

    assert build_home_next_actions(user=None, prefs={}, customer_count=0) == []
    assert build_home_next_actions(user={"username": "admin"}, prefs={}, customer_count=0) == []


def test_home_next_action_pages_exist():
    from utils.onboarding import build_home_next_actions

    repo_root = Path(__file__).resolve().parents[1]
    scenarios = [
        {
            "user": {"username": "seller", "email": "seller@example.com", "email_verified": False},
            "prefs": {"company_name": "ABC"},
            "customer_count": 0,
        },
        {
            "user": {"username": "seller", "email": "seller@example.com", "email_verified": True},
            "prefs": _complete_prefs(),
            "customer_count": 2,
        },
    ]

    pages = {
        action["page"]
        for scenario in scenarios
        for action in build_home_next_actions(**scenario)
    }

    assert pages
    for page in pages:
        assert (repo_root / page).exists(), page
