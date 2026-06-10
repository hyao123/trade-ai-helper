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
    from utils.onboarding import is_quick_setup_complete, profile_completion

    completion = profile_completion({"company_name": "ABC"})

    assert completion["completed"] == 1
    assert completion["total"] == 5
    assert completion["complete"] is False
    assert "default_product" in completion["missing"]
    assert completion["missing_labels"][:2] == ["联系人", "默认产品"]
    assert completion["next_missing_label"] == "联系人"
    assert is_quick_setup_complete({"company_name": "ABC"}) is False
    assert is_quick_setup_complete(_complete_prefs(onboarding_completed="false")) is True


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


def test_home_next_actions_prioritize_due_followups_for_retention():
    from utils.onboarding import build_home_next_actions

    actions = build_home_next_actions(
        user={"username": "seller", "email": "seller@example.com", "email_verified": True},
        prefs=_complete_prefs(),
        customer_count=5,
        due_followup_count=3,
    )

    assert [action["id"] for action in actions][:3] == ["due_followups", "cold_email", "dashboard"]
    assert actions[0]["label"] == "今日跟进"
    assert "3" in actions[0]["detail"]
    assert actions[0]["priority"] == "primary"
    assert actions[0]["page"] == "pages/10_📅_跟进日历.py"


def test_home_engagement_summary_prioritizes_daily_reactivation_signal():
    from utils.onboarding import build_home_engagement_summary

    summary = build_home_engagement_summary(
        prefs=_complete_prefs(),
        customer_count=7,
        due_followup_count=3,
    )

    assert summary["headline"] == "今天有 3 个客户待跟进"
    assert summary["tone"] == "urgent"
    assert summary["metrics"][0] == {"label": "今日跟进", "value": "3"}
    assert summary["metrics"][1] == {"label": "客户资产", "value": "7"}
    assert summary["metrics"][2] == {"label": "资料状态", "value": "完整"}


def test_home_engagement_summary_guides_empty_customer_base():
    from utils.onboarding import build_home_engagement_summary

    summary = build_home_engagement_summary(
        prefs=_complete_prefs(),
        customer_count=0,
        due_followup_count=0,
    )

    assert summary["headline"] == "先建立第一个客户档案"
    assert summary["tone"] == "setup"
    assert summary["metrics"][1] == {"label": "客户资产", "value": "0"}


def test_count_customers_needing_attention_flags_stale_or_missing_contact():
    from datetime import date

    from utils.onboarding import (
        count_customers_needing_attention,
        filter_customers_needing_attention,
    )

    customers = [
        {"company": "Fresh", "last_contact": "2026-06-01"},
        {"company": "Stale", "last_contact": "2026-04-30"},
        {"company": "Missing"},
        {"company": "Bad date", "last_contact": "not-a-date"},
    ]

    assert count_customers_needing_attention(customers, today=date(2026, 6, 10)) == 3
    assert [c["company"] for c in filter_customers_needing_attention(customers, today=date(2026, 6, 10))] == [
        "Stale",
        "Missing",
        "Bad date",
    ]


def test_home_engagement_summary_surfaces_customer_activation_signal():
    from utils.onboarding import build_home_engagement_summary

    summary = build_home_engagement_summary(
        prefs=_complete_prefs(),
        customer_count=8,
        due_followup_count=0,
        attention_customer_count=2,
    )

    assert summary["headline"] == "有 2 个客户需要激活"
    assert summary["tone"] == "attention"
    assert summary["metrics"][0] == {"label": "待激活客户", "value": "2"}


def test_home_daily_plan_prioritizes_revenue_recovery_work():
    from utils.onboarding import build_home_daily_plan

    plan = build_home_daily_plan(
        prefs=_complete_prefs(),
        customer_count=8,
        due_followup_count=2,
        attention_customer_count=3,
    )

    assert [item["id"] for item in plan] == ["due_followups", "activate_customers", "cold_email"]
    assert plan[0]["tone"] == "urgent"
    assert plan[0]["label"] == "处理今日跟进"
    assert "2" in plan[0]["detail"]
    assert plan[1]["state_updates"] == {"crm_attention_only": True}


def test_home_daily_plan_guides_setup_before_growth_work():
    from utils.onboarding import build_home_daily_plan

    plan = build_home_daily_plan(
        prefs={"company_name": "ABC"},
        customer_count=0,
        due_followup_count=0,
        attention_customer_count=0,
    )

    assert [item["id"] for item in plan] == ["quick_setup", "add_customer"]
    assert plan[0]["tone"] == "setup"
    assert plan[1]["page"] == "pages/7_📇_客户管理.py"


def test_home_next_actions_prioritize_customer_activation_when_no_due_followups():
    from utils.onboarding import build_home_next_actions

    actions = build_home_next_actions(
        user={"username": "seller", "email": "seller@example.com", "email_verified": True},
        prefs=_complete_prefs(),
        customer_count=8,
        due_followup_count=0,
        attention_customer_count=2,
    )

    assert [action["id"] for action in actions][:3] == ["activate_customers", "cold_email", "dashboard"]
    assert actions[0]["label"] == "激活客户"
    assert "2" in actions[0]["detail"]
    assert actions[0]["priority"] == "primary"
    assert actions[0]["page"] == "pages/7_📇_客户管理.py"
    assert actions[0]["state_updates"] == {"crm_attention_only": True}


def test_home_next_actions_do_not_repeat_setup_when_profile_is_complete():
    from utils.onboarding import build_home_next_actions

    actions = build_home_next_actions(
        user={"username": "seller", "email": "seller@example.com", "email_verified": True},
        prefs=_complete_prefs(onboarding_completed="false"),
        customer_count=0,
    )

    assert "quick_setup" not in [action["id"] for action in actions]
    assert actions[0]["id"] == "cold_email"


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
        {
            "user": {"username": "seller", "email": "seller@example.com", "email_verified": True},
            "prefs": _complete_prefs(),
            "customer_count": 8,
            "attention_customer_count": 2,
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
