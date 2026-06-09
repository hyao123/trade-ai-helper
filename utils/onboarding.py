"""Home-page onboarding and next-action helpers."""

from __future__ import annotations

from typing import TypedDict

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


def build_home_next_actions(
    *,
    user: dict | None,
    prefs: dict,
    customer_count: int = 0,
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

    if not completion["complete"] or prefs.get("onboarding_completed") != "true":
        actions.append({
            "id": "quick_setup",
            "label": "完成快速设置",
            "detail": f"{completion['completed']}/{completion['total']}，{_missing_preview(completion['missing_labels'])}",
            "page": "pages/34_🚀_快速设置.py",
            "priority": "primary" if not actions else "secondary",
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
    else:
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
