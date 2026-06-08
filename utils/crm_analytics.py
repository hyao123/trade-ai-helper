"""
utils/crm_analytics.py
-----------------------
Customer analytics engine for trade CRM data.

Provides:
- Conversion funnel analysis (stage progression)
- Response time metrics
- Customer segmentation stats
- Activity timeline

Note: This module was formerly part of utils/analytics.py.
      The event tracking system is now in utils/analytics.py (track_event).
      These CRM analysis functions remain available for backward compatibility.
"""
from __future__ import annotations

import datetime
from collections import Counter

from utils.logger import get_logger

logger = get_logger("crm_analytics")

STAGE_ORDER = [
    "新客户", "已联系", "已报价", "已发样", "谈判中", "已下单", "长期合作",
]

STAGE_LABELS_EN = {
    "新客户": "New Lead", "已联系": "Contacted", "已报价": "Quoted",
    "已发样": "Sample Sent", "谈判中": "Negotiating", "已下单": "Ordered",
    "长期合作": "Long-term",
}


def compute_funnel(customers: list[dict]) -> list[dict]:
    """Compute conversion funnel from customer stage data."""
    total = len(customers)
    if total == 0:
        return []
    stage_counts = Counter(c.get("stage", "新客户") for c in customers)
    funnel = []
    for stage in STAGE_ORDER:
        count = stage_counts.get(stage, 0)
        pct = (count / total) * 100 if total > 0 else 0
        funnel.append({
            "stage": stage,
            "label_en": STAGE_LABELS_EN.get(stage, stage),
            "count": count,
            "percentage": round(pct, 1),
        })
    for stage, count in stage_counts.items():
        if stage not in STAGE_ORDER:
            pct = (count / total) * 100
            funnel.append({"stage": stage, "label_en": stage, "count": count, "percentage": round(pct, 1)})
    return funnel


def compute_activity_metrics(customers: list[dict], today: datetime.date | None = None) -> dict:
    """Compute activity-based metrics."""
    today = today or datetime.date.today()
    active = dormant = never_contacted = 0
    days_list = []
    for c in customers:
        last_contact = c.get("last_contact", "")
        if not last_contact:
            never_contacted += 1
            continue
        try:
            contact_date = datetime.date.fromisoformat(last_contact)
            days_diff = (today - contact_date).days
            days_list.append(days_diff)
            if days_diff <= 30:
                active += 1
            else:
                dormant += 1
        except (ValueError, TypeError):
            never_contacted += 1
    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else 0.0
    return {
        "active_count": active,
        "dormant_count": dormant,
        "never_contacted": never_contacted,
        "avg_days_since_contact": avg_days,
    }


def compute_segmentation(customers: list[dict]) -> dict:
    """Compute customer segmentation by country and industry."""
    countries = Counter()
    industries = Counter()
    for c in customers:
        country = c.get("country", "").strip()
        industry = c.get("industry", "").strip()
        if country:
            countries[country] += 1
        if industry:
            industries[industry] += 1
    return {
        "top_countries": countries.most_common(10),
        "top_industries": industries.most_common(10),
    }


def compute_monthly_activity(customers: list[dict]) -> list[dict]:
    """Compute monthly activity based on last_contact dates."""
    today = datetime.date.today()
    months = []
    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year:04d}-{month:02d}")
    month_counts = Counter()
    for c in customers:
        last_contact = c.get("last_contact", "")
        if last_contact and len(last_contact) >= 7:
            month_key = last_contact[:7]
            if month_key in months:
                month_counts[month_key] += 1
    return [{"month": m, "count": month_counts.get(m, 0)} for m in months]


def generate_full_report(customers: list[dict]) -> dict:
    """Generate a complete analytics report from customer data."""
    funnel = compute_funnel(customers)
    activity = compute_activity_metrics(customers)
    segmentation = compute_segmentation(customers)
    monthly = compute_monthly_activity(customers)
    converted_stages = {"已下单", "长期合作"}
    converted = sum(1 for c in customers if c.get("stage") in converted_stages)
    conversion_rate = round((converted / len(customers)) * 100, 1) if customers else 0.0
    return {
        "total_customers": len(customers),
        "funnel": funnel,
        "conversion_rate": conversion_rate,
        "avg_days_since_contact": activity["avg_days_since_contact"],
        "active_customers": activity["active_count"],
        "dormant_customers": activity["dormant_count"],
        "top_countries": segmentation["top_countries"],
        "top_industries": segmentation["top_industries"],
        "monthly_activity": monthly,
    }
