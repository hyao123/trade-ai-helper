"""Home-page onboarding and next-action helpers."""

from __future__ import annotations

from datetime import date
from typing import NotRequired, TypedDict

REQUIRED_PROFILE_FIELDS = (
    "company_name",
    "contact_name",
    "default_product",
    "main_products",
    "company_description",
)

FIELD_LABELS = {
    "company_name": "公司名称",
    "contact_name": "联系人",
    "default_product": "默认产品",
    "main_products": "主营产品",
    "company_description": "公司优势",
}


class ProfileCompletion(TypedDict):
    completed: int
    total: int
    missing: list[str]
    missing_labels: list[str]
    next_missing_label: str
    complete: bool


class HomeNextAction(TypedDict):
    id: str
    label: str
    detail: str
    page: str
    priority: str
    state_updates: NotRequired[dict[str, object]]


class EngagementSummary(TypedDict):
    headline: str
    detail: str
    tone: str
    metrics: list[dict[str, str]]


def _has_value(value: object) -> bool:
    return bool(str(value or "").strip())


def _missing_preview(labels: list[str], *, limit: int = 2) -> str:
    if not labels:
        return "资料已完整"
    preview = "、".join(labels[:limit])
    if len(labels) > limit:
        preview += f"等 {len(labels)} 项"
    return f"还差：{preview}"


def profile_completion(prefs: dict) -> ProfileCompletion:
    """Return completion state for the core seller profile."""
    missing = [field for field in REQUIRED_PROFILE_FIELDS if not _has_value(prefs.get(field))]
    missing_labels = [FIELD_LABELS[field] for field in missing]
    completed = len(REQUIRED_PROFILE_FIELDS) - len(missing)
    return {
        "completed": completed,
        "total": len(REQUIRED_PROFILE_FIELDS),
        "missing": missing,
        "missing_labels": missing_labels,
        "next_missing_label": missing_labels[0] if missing_labels else "",
        "complete": completed == len(REQUIRED_PROFILE_FIELDS),
    }


def is_quick_setup_complete(prefs: dict) -> bool:
    """Return True when the seller profile is complete enough for daily workflows."""
    return profile_completion(prefs)["complete"]


def count_customers_needing_attention(
    customers: list[dict],
    *,
    today: date | None = None,
    stale_days: int = 30,
) -> int:
    """Count customers without a recent contact touchpoint."""
    return len(filter_customers_needing_attention(customers, today=today, stale_days=stale_days))


def customer_needs_attention(
    customer: dict,
    *,
    today: date | None = None,
    stale_days: int = 30,
) -> bool:
    """Return True when a customer has no recent contact record."""
    today = today or date.today()
    last_contact = str(customer.get("last_contact") or "").strip()
    if not last_contact:
        return True
    try:
        days_since_contact = (today - date.fromisoformat(last_contact)).days
    except ValueError:
        return True
    return days_since_contact > stale_days


def filter_customers_needing_attention(
    customers: list[dict],
    *,
    today: date | None = None,
    stale_days: int = 30,
) -> list[dict]:
    """Return customers without a recent contact touchpoint."""
    today = today or date.today()
    return [
        customer
        for customer in customers
        if customer_needs_attention(customer, today=today, stale_days=stale_days)
    ]


def build_home_engagement_summary(
    *,
    prefs: dict,
    customer_count: int = 0,
    due_followup_count: int = 0,
    attention_customer_count: int = 0,
) -> EngagementSummary:
    """Build a compact daily work signal for the home page."""
    profile_ready = is_quick_setup_complete(prefs)
    if due_followup_count > 0:
        headline = f"今天有 {due_followup_count} 个客户待跟进"
        detail = "优先处理已到期商机，保持客户节奏不断档。"
        tone = "urgent"
        first_metric = {"label": "今日跟进", "value": str(max(due_followup_count, 0))}
    elif attention_customer_count > 0:
        headline = f"有 {attention_customer_count} 个客户需要激活"
        detail = "这些客户缺少近期联系记录，适合安排问候、跟进或重新分层。"
        tone = "attention"
        first_metric = {"label": "待激活客户", "value": str(max(attention_customer_count, 0))}
    elif customer_count <= 0:
        headline = "先建立第一个客户档案"
        detail = "把潜在客户沉淀到 CRM，后续邮件、报价和跟进才能形成闭环。"
        tone = "setup"
        first_metric = {"label": "今日跟进", "value": str(max(due_followup_count, 0))}
    elif not profile_ready:
        headline = "完善公司资料，提升生成质量"
        detail = "补齐主营产品和公司优势后，AI 输出会更贴近真实业务。"
        tone = "setup"
        first_metric = {"label": "今日跟进", "value": str(max(due_followup_count, 0))}
    else:
        headline = "工作台已就绪"
        detail = "继续开发新客户，并保持现有客户的跟进节奏。"
        tone = "steady"
        first_metric = {"label": "今日跟进", "value": str(max(due_followup_count, 0))}

    return {
        "headline": headline,
        "detail": detail,
        "tone": tone,
        "metrics": [
            first_metric,
            {"label": "客户资产", "value": str(max(customer_count, 0))},
            {"label": "资料状态", "value": "完整" if profile_ready else "待完善"},
        ],
    }


def build_home_next_actions(
    *,
    user: dict | None,
    prefs: dict,
    customer_count: int = 0,
    due_followup_count: int = 0,
    attention_customer_count: int = 0,
) -> list[HomeNextAction]:
    """Build prioritized home-page actions for a user's current setup state."""
    if not user or user.get("username") in (None, "admin"):
        return []

    completion = profile_completion(prefs)
    actions: list[HomeNextAction] = []
    email = str(user.get("email") or "").strip()

    if not email or user.get("email_verified") is not True:
        actions.append({
            "id": "verify_email",
            "label": "验证邮箱",
            "detail": "绑定并验证邮箱，解锁生成、升级和通知",
            "page": "pages/11_👤_账户管理.py",
            "priority": "primary",
        })

    if not is_quick_setup_complete(prefs):
        actions.append({
            "id": "quick_setup",
            "label": "完成快速设置",
            "detail": f"{completion['completed']}/{completion['total']}，{_missing_preview(completion['missing_labels'])}",
            "page": "pages/34_🚀_快速设置.py",
            "priority": "primary" if not actions else "secondary",
        })

    if completion["complete"] and due_followup_count > 0:
        actions.append({
            "id": "due_followups",
            "label": "今日跟进",
            "detail": f"{due_followup_count} 个客户到期，优先处理商机",
            "page": "pages/10_📅_跟进日历.py",
            "priority": "primary" if not actions else "secondary",
        })

    if completion["complete"] and due_followup_count <= 0 and attention_customer_count > 0:
        actions.append({
            "id": "activate_customers",
            "label": "激活客户",
            "detail": f"{attention_customer_count} 个客户缺少近期触达",
            "page": "pages/7_📇_客户管理.py",
            "priority": "primary" if not actions else "secondary",
            "state_updates": {"crm_attention_only": True},
        })

    if completion["complete"]:
        actions.append({
            "id": "cold_email",
            "label": "生成开发信",
            "detail": "用公司资料快速生成第一封外贸邮件",
            "page": "pages/1_📧_开发信.py",
            "priority": "primary" if not actions else "secondary",
        })

    if customer_count <= 0:
        actions.append({
            "id": "add_customer",
            "label": "添加客户",
            "detail": "建立客户档案，开始跟进和评分",
            "page": "pages/7_📇_客户管理.py",
            "priority": "secondary",
        })
    elif due_followup_count <= 0 and attention_customer_count <= 0:
        actions.append({
            "id": "follow_up",
            "label": "跟进客户",
            "detail": f"查看 {customer_count} 个客户的待办和节奏",
            "page": "pages/10_📅_跟进日历.py",
            "priority": "secondary",
        })

    actions.append({
        "id": "dashboard",
        "label": "查看仪表盘",
        "detail": "查看邮件、客户、通知和上线体检",
        "page": "pages/33_📊_仪表盘.py",
        "priority": "secondary",
    })
    return actions[:4]
