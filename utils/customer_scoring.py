"""
utils/customer_scoring.py
--------------------------
Automated customer behavior scoring based on email interactions,
engagement patterns, and CRM activity.

Scoring dimensions (0-100 composite score):
  - Engagement (30%): email opens, clicks, replies
  - Activity (25%): recency of last interaction
  - Intent (25%): AI-classified email intent signals
  - Profile completeness (10%): CRM data completeness
  - Relationship depth (10%): number of interactions over time

Score tiers:
  90-100: Hot lead (ready to close)
  70-89:  Warm lead (actively engaged)
  40-69:  Nurturing (needs more touchpoints)
  20-39:  Cold (low engagement)
  0-19:   Dormant (no activity)

Auto-actions triggered by score changes:
  - Score rises above 70: Notify user "Hot lead alert!"
  - Score drops below 30: Suggest re-engagement campaign
  - New inquiry from scored customer: Update score immediately

Usage:
    from utils.customer_scoring import (
        compute_behavior_score,
        batch_score_customers,
        get_score_history,
        get_hot_leads,
    )
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("customer_scoring")

_SCORES_FILE = "customer_scores.json"

# Weight configuration
WEIGHTS = {
    "engagement": 0.30,
    "activity": 0.25,
    "intent": 0.25,
    "completeness": 0.10,
    "depth": 0.10,
}

# Score tier definitions
SCORE_TIERS = [
    {"min": 90, "label": "Hot Lead", "label_zh": "热门线索", "icon": "🔥", "color": "#ef4444"},
    {"min": 70, "label": "Warm Lead", "label_zh": "活跃客户", "icon": "🌡️", "color": "#f59e0b"},
    {"min": 40, "label": "Nurturing", "label_zh": "培育中", "icon": "🌱", "color": "#3b82f6"},
    {"min": 20, "label": "Cold", "label_zh": "冷淡", "icon": "❄️", "color": "#6b7280"},
    {"min": 0, "label": "Dormant", "label_zh": "休眠", "icon": "💤", "color": "#9ca3af"},
]


# ---------------------------------------------------------------------------
# Core scoring engine
# ---------------------------------------------------------------------------

def compute_behavior_score(
    customer: dict,
    email_stats: dict | None = None,
    intent_signals: list[str] | None = None,
    interaction_count: int = 0,
) -> dict:
    """
    Compute a comprehensive behavior score for a customer.

    Args:
        customer: Customer dict from CRM (company, contact, email, stage, etc.)
        email_stats: Optional email engagement stats (opens, clicks, replies)
        intent_signals: List of detected intents from recent emails
        interaction_count: Total number of interactions with this customer

    Returns:
        Dict with: total_score, dimension_scores, tier, tier_info, breakdown
    """
    # Compute each dimension
    engagement_score = _score_engagement(email_stats or {})
    activity_score = _score_activity(customer)
    intent_score = _score_intent(intent_signals or [])
    completeness_score = _score_completeness(customer)
    depth_score = _score_depth(interaction_count)

    # Weighted total
    total = (
        engagement_score * WEIGHTS["engagement"]
        + activity_score * WEIGHTS["activity"]
        + intent_score * WEIGHTS["intent"]
        + completeness_score * WEIGHTS["completeness"]
        + depth_score * WEIGHTS["depth"]
    )
    total = min(100, max(0, int(total)))

    # Determine tier
    tier_info = _get_tier(total)

    return {
        "total_score": total,
        "dimensions": {
            "engagement": int(engagement_score),
            "activity": int(activity_score),
            "intent": int(intent_score),
            "completeness": int(completeness_score),
            "depth": int(depth_score),
        },
        "tier": tier_info["label"],
        "tier_zh": tier_info["label_zh"],
        "tier_icon": tier_info["icon"],
        "tier_color": tier_info["color"],
        "computed_at": datetime.now().isoformat(),
    }


def batch_score_customers(
    username: str,
    customers: list[dict],
) -> list[dict]:
    """
    Score all customers and persist results.

    Args:
        username: User who owns these customers
        customers: List of customer dicts from CRM

    Returns:
        List of dicts with customer + score data, sorted by score (highest first)
    """
    scored_results = []
    scores_cache = load_user_json(username, _SCORES_FILE, default={})

    for i, customer in enumerate(customers):
        customer_key = _customer_key(customer)

        # Get email stats for this customer if available
        email_stats = _get_customer_email_stats(username, customer)

        # Get intent signals from processed inbox
        intents = _get_customer_intents(username, customer)

        # Count interactions (simplified: based on workflow followups)
        interactions = _count_interactions(username, customer)

        # Compute score
        score_data = compute_behavior_score(
            customer=customer,
            email_stats=email_stats,
            intent_signals=intents,
            interaction_count=interactions,
        )

        # Check for score change alerts
        previous = scores_cache.get(customer_key, {})
        prev_score = previous.get("total_score", 0)
        _check_score_alerts(customer, prev_score, score_data["total_score"])

        # Save to cache
        scores_cache[customer_key] = score_data

        scored_results.append({
            "customer": customer,
            "score": score_data,
            "previous_score": prev_score,
            "score_change": score_data["total_score"] - prev_score,
        })

    # Persist scores
    save_user_json(username, _SCORES_FILE, scores_cache)

    # Sort by score descending
    scored_results.sort(key=lambda x: x["score"]["total_score"], reverse=True)
    logger.info("Scored %d customers for %s", len(scored_results), username)
    return scored_results


def get_score_history(username: str, customer_key: str, days: int = 30) -> list[dict]:
    """
    Get historical scores for a customer.

    Note: In production, scores would be timestamped in a DB.
    For now, returns current snapshot only.
    """
    scores_cache = load_user_json(username, _SCORES_FILE, default={})
    current = scores_cache.get(customer_key)
    if current:
        return [current]
    return []


def get_hot_leads(username: str, min_score: int = 70) -> list[dict]:
    """
    Get all customers with scores above the threshold (hot leads).

    Args:
        username: User to query
        min_score: Minimum score to be considered "hot"

    Returns:
        List of (customer_key, score_data) sorted by score
    """
    scores_cache = load_user_json(username, _SCORES_FILE, default={})
    hot = [
        {"key": key, "score": data}
        for key, data in scores_cache.items()
        if data.get("total_score", 0) >= min_score
    ]
    hot.sort(key=lambda x: x["score"]["total_score"], reverse=True)
    return hot


def get_score_summary(username: str) -> dict:
    """
    Get aggregate scoring summary for the user's customer base.

    Returns:
        Dict with tier distribution, average score, trends
    """
    scores_cache = load_user_json(username, _SCORES_FILE, default={})

    if not scores_cache:
        return {"total": 0, "avg_score": 0, "tier_distribution": {}}

    scores = [d.get("total_score", 0) for d in scores_cache.values()]
    tier_dist = {}
    for tier in SCORE_TIERS:
        label = tier["label_zh"]
        count = sum(1 for s in scores if s >= tier["min"] and (
            tier == SCORE_TIERS[-1] or s < SCORE_TIERS[SCORE_TIERS.index(tier) - 1]["min"]
            if SCORE_TIERS.index(tier) > 0 else True
        ))
        tier_dist[label] = count

    # Simpler tier counting
    tier_dist = {"🔥 热门": 0, "🌡️ 活跃": 0, "🌱 培育": 0, "❄️ 冷淡": 0, "💤 休眠": 0}
    for s in scores:
        if s >= 90:
            tier_dist["🔥 热门"] += 1
        elif s >= 70:
            tier_dist["🌡️ 活跃"] += 1
        elif s >= 40:
            tier_dist["🌱 培育"] += 1
        elif s >= 20:
            tier_dist["❄️ 冷淡"] += 1
        else:
            tier_dist["💤 休眠"] += 1

    return {
        "total": len(scores),
        "avg_score": round(sum(scores) / len(scores), 1),
        "max_score": max(scores),
        "min_score": min(scores),
        "tier_distribution": tier_dist,
        "hot_leads_count": sum(1 for s in scores if s >= 70),
    }


# ---------------------------------------------------------------------------
# Dimension scoring functions
# ---------------------------------------------------------------------------

def _score_engagement(email_stats: dict) -> float:
    """
    Score based on email engagement metrics.

    Input: {total_sent, total_opened, total_clicked, total_replied}
    Output: 0-100
    """
    sent = email_stats.get("total_sent", 0)
    if sent == 0:
        return 20  # No data = neutral

    open_rate = email_stats.get("total_opened", 0) / sent
    click_rate = email_stats.get("total_clicked", 0) / sent
    reply_rate = email_stats.get("total_replied", 0) / sent

    # Weighted engagement: reply is most valuable
    score = (open_rate * 25 + click_rate * 35 + reply_rate * 40) * 100
    return min(100, max(0, score))


def _score_activity(customer: dict) -> float:
    """
    Score based on recency of last contact.

    More recent = higher score.
    """
    last_contact = customer.get("last_contact", "")
    if not last_contact:
        return 10

    try:
        last_date = date.fromisoformat(last_contact)
        days_ago = (date.today() - last_date).days

        if days_ago <= 3:
            return 100
        elif days_ago <= 7:
            return 85
        elif days_ago <= 14:
            return 70
        elif days_ago <= 30:
            return 50
        elif days_ago <= 60:
            return 30
        elif days_ago <= 90:
            return 15
        else:
            return 5
    except (ValueError, TypeError):
        return 10


def _score_intent(intent_signals: list[str]) -> float:
    """
    Score based on AI-detected intent signals from recent emails.

    High-value intents (order_intent, inquiry) score higher.
    """
    if not intent_signals:
        return 30  # No signals = neutral-low

    intent_values = {
        "order_intent": 100,
        "inquiry": 80,
        "negotiation": 75,
        "sample_request": 70,
        "followup_needed": 50,
        "complaint": 40,  # Engaged but negative
        "info_only": 10,
        "spam": 0,
    }

    # Use the highest-value intent as primary signal
    scores = [intent_values.get(i, 30) for i in intent_signals]
    if scores:
        # Weighted: max intent counts 70%, average counts 30%
        return max(scores) * 0.7 + (sum(scores) / len(scores)) * 0.3
    return 30


def _score_completeness(customer: dict) -> float:
    """
    Score based on how complete the customer profile is.

    More data = easier to personalize = more valuable.
    """
    fields_to_check = [
        ("email", 20),
        ("contact", 15),
        ("company", 15),
        ("country", 10),
        ("product", 15),
        ("notes", 10),
        ("stage", 10),
        ("tags", 5),
    ]

    score = 0
    for field, points in fields_to_check:
        value = customer.get(field)
        if value and (isinstance(value, str) and value.strip()) or (isinstance(value, list) and value):
            score += points

    return min(100, score)


def _score_depth(interaction_count: int) -> float:
    """
    Score based on total interaction depth (number of touchpoints).

    More interactions = deeper relationship.
    """
    if interaction_count == 0:
        return 10
    elif interaction_count <= 2:
        return 30
    elif interaction_count <= 5:
        return 50
    elif interaction_count <= 10:
        return 70
    elif interaction_count <= 20:
        return 85
    else:
        return 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _customer_key(customer: dict) -> str:
    """Generate a unique key for a customer (for cache lookup)."""
    company = customer.get("company", "").lower().strip()
    contact = customer.get("contact", "").lower().strip()
    email = customer.get("email", "").lower().strip()
    return f"{company}|{contact}|{email}"


def _get_tier(score: int) -> dict:
    """Get the tier info dict for a given score."""
    for tier in SCORE_TIERS:
        if score >= tier["min"]:
            return tier
    return SCORE_TIERS[-1]


def _get_customer_email_stats(username: str, customer: dict) -> dict:
    """Get email tracking stats for a specific customer."""
    try:
        from utils.email_tracking import get_user_email_stats
        # Simplified: use overall user stats as proxy
        # In production, would filter by customer email
        return get_user_email_stats(username, days=30)
    except Exception:
        return {}


def _get_customer_intents(username: str, customer: dict) -> list[str]:
    """Get classified intents from inbox for this customer's emails."""
    try:
        processed = load_user_json(username, "inbox_processed.json", default={})
        customer_email = customer.get("email", "").lower()
        if not customer_email:
            return []

        intents = []
        for _id, data in processed.items():
            classification = data.get("classification", {})
            # Match by email domain or address (simplified)
            email_from = data.get("email", {}).get("from", "").lower()
            if customer_email in email_from:
                intents.append(classification.get("intent", "info_only"))

        return intents[-5:]  # Last 5 intents
    except Exception:
        return []


def _count_interactions(username: str, customer: dict) -> int:
    """Count total interactions with a customer."""
    try:
        from utils.workflow import get_all_workflows
        workflows = get_all_workflows()
        company = customer.get("company", "").lower()
        contact = customer.get("contact", "").lower()

        count = 0
        for wf in workflows:
            if (wf.get("company", "").lower() == company
                    and wf.get("customer", "").lower() == contact):
                count += 1
                count += len(wf.get("followups", []))
        return count
    except Exception:
        return 0


def _check_score_alerts(customer: dict, prev_score: int, new_score: int) -> None:
    """Check if score changes should trigger alerts."""
    if prev_score == 0:
        return  # First scoring, no alert

    # Hot lead alert
    if prev_score < 70 <= new_score:
        logger.info(
            "🔥 Hot lead alert: %s (%s) score rose to %d",
            customer.get("contact", ""), customer.get("company", ""), new_score,
        )

    # Cooling alert
    if prev_score >= 40 > new_score:
        logger.info(
            "❄️ Customer cooling: %s (%s) score dropped to %d",
            customer.get("contact", ""), customer.get("company", ""), new_score,
        )
