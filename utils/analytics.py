"""
utils/analytics.py
------------------
Customer analytics engine for trade CRM data.

Provides:
- Conversion funnel analysis (stage progression)
- Response time metrics
- Customer segmentation stats
- Revenue estimation by stage
- Activity timeline
"""

from __future__ import annotations

import datetime
from collections import Counter
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger("analytics")

# ---------------------------------------------------------------------------
# Stage definitions (matching customers.py)
# ---------------------------------------------------------------------------
STAGE_ORDER = [
    "新客户",
    "已联系",
    "已报价",
    "已发样",
    "谈判中",
    "已下单",
    "长期合作",
]

STAGE_LABELS_EN = {
    "新客户": "New Lead",
    "已联系": "Contacted",
    "已报价": "Quoted",
    "已发样": "Sample Sent",
    "谈判中": "Negotiating",
    "已下单": "Ordered",
    "长期合作": "Long-term",
}


@dataclass
class FunnelStage:
    """A single stage in the conversion funnel."""
    stage: str
    label_en: str
    count: int
    percentage: float  # of total


@dataclass
class AnalyticsReport:
    """Complete analytics report for customer data."""
    total_customers: int
    funnel: list[FunnelStage]
    conversion_rate: float  # % that reached "已下单" or beyond
    avg_days_since_contact: float
    active_customers: int  # contacted within 30 days
    dormant_customers: int  # no contact > 30 days
    top_countries: list[tuple[str, int]]
    top_industries: list[tuple[str, int]]
    stage_distribution: dict[str, int]
    monthly_activity: list[dict]  # [{month: str, count: int}]


def compute_funnel(customers: list[dict]) -> list[FunnelStage]:
    """
    Compute conversion funnel from customer stage data.

    Returns list of FunnelStage sorted by stage order.
    """
    total = len(customers)
    if total == 0:
        return []

    stage_counts = Counter(c.get("stage", "新客户") for c in customers)

    funnel = []
    for stage in STAGE_ORDER:
        count = stage_counts.get(stage, 0)
        pct = (count / total) * 100 if total > 0 else 0
        funnel.append(FunnelStage(
            stage=stage,
            label_en=STAGE_LABELS_EN.get(stage, stage),
            count=count,
            percentage=round(pct, 1),
        ))

    # Add any stages not in STAGE_ORDER
    for stage, count in stage_counts.items():
        if stage not in STAGE_ORDER:
            pct = (count / total) * 100
            funnel.append(FunnelStage(
                stage=stage,
                label_en=stage,
                count=count,
                percentage=round(pct, 1),
            ))

    return funnel


def compute_conversion_rate(customers: list[dict]) -> float:
    """
    Calculate conversion rate: % of customers that reached 已下单 or 长期合作.
    """
    if not customers:
        return 0.0
    converted_stages = {"已下单", "长期合作"}
    converted = sum(1 for c in customers if c.get("stage") in converted_stages)
    return round((converted / len(customers)) * 100, 1)


def compute_activity_metrics(customers: list[dict]) -> dict:
    """
    Compute activity-based metrics.

    Returns dict with:
    - active_count: customers contacted within 30 days
    - dormant_count: customers with no contact > 30 days
    - avg_days_since_contact: average days since last contact
    - never_contacted: customers with no last_contact date
    """
    today = datetime.date.today()
    active = 0
    dormant = 0
    never_contacted = 0
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
    """
    Compute customer segmentation by country and industry.

    Returns dict with:
    - top_countries: list of (country, count) tuples, top 10
    - top_industries: list of (industry, count) tuples, top 10
    """
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
    """
    Compute monthly activity based on last_contact dates.

    Returns list of {month: 'YYYY-MM', count: N} for last 6 months.
    """
    today = datetime.date.today()
    months = []
    for i in range(5, -1, -1):
        # Calculate month offset
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


def generate_full_report(customers: list[dict]) -> AnalyticsReport:
    """
    Generate a complete analytics report from customer data.
    """
    logger.info("Generating analytics report for %d customers", len(customers))

    funnel = compute_funnel(customers)
    conversion_rate = compute_conversion_rate(customers)
    activity = compute_activity_metrics(customers)
    segmentation = compute_segmentation(customers)
    monthly = compute_monthly_activity(customers)

    stage_dist = {s.stage: s.count for s in funnel}

    report = AnalyticsReport(
        total_customers=len(customers),
        funnel=funnel,
        conversion_rate=conversion_rate,
        avg_days_since_contact=activity["avg_days_since_contact"],
        active_customers=activity["active_count"],
        dormant_customers=activity["dormant_count"],
        top_countries=segmentation["top_countries"],
        top_industries=segmentation["top_industries"],
        stage_distribution=stage_dist,
        monthly_activity=monthly,
    )

    logger.info("Report generated: %d customers, %.1f%% conversion",
                report.total_customers, report.conversion_rate)
    return report
