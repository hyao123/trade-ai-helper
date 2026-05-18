"""
utils/marketplace.py
--------------------
Template marketplace for sharing and discovering email templates.

Features:
- Users can publish their saved templates to the marketplace
- Browse/search templates by category, language, industry
- Rating system (1-5 stars)
- Usage counter (how many times a template was used)
- Featured/trending templates
- Categories: cold_email, inquiry_reply, followup, negotiation, greeting, listing

Revenue model:
- Free templates: community-contributed
- Premium templates: curated by platform, require Pro plan
- Revenue share: template authors earn credits when their templates are used

Usage:
    from utils.marketplace import (
        publish_template,
        browse_templates,
        use_template,
        rate_template,
        get_trending,
    )
"""
from __future__ import annotations

import secrets
from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_json, save_json

logger = get_logger("marketplace")

_MARKETPLACE_FILE = "marketplace_templates.json"

# ---------------------------------------------------------------------------
# Categories & metadata
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"id": "cold_email", "name": "开发信", "name_en": "Cold Email", "icon": "📧"},
    {"id": "inquiry_reply", "name": "询盘回复", "name_en": "Inquiry Reply", "icon": "📩"},
    {"id": "followup", "name": "跟进邮件", "name_en": "Follow-up", "icon": "📬"},
    {"id": "negotiation", "name": "谈判话术", "name_en": "Negotiation", "icon": "🗣️"},
    {"id": "greeting", "name": "节日问候", "name_en": "Holiday Greeting", "icon": "🎄"},
    {"id": "listing", "name": "产品上架", "name_en": "Product Listing", "icon": "🛒"},
    {"id": "complaint", "name": "投诉处理", "name_en": "Complaint Response", "icon": "😟"},
    {"id": "social", "name": "社媒文案", "name_en": "Social Media", "icon": "💬"},
    {"id": "quotation", "name": "报价相关", "name_en": "Quotation", "icon": "💰"},
    {"id": "other", "name": "其他", "name_en": "Other", "icon": "📝"},
]

INDUSTRIES = [
    "电子产品", "LED照明", "家居用品", "五金配件", "纺织服装",
    "机械设备", "汽车配件", "食品饮料", "化工产品", "医疗器械",
    "玩具礼品", "建材", "包装材料", "通用",
]

LANGUAGES = ["English", "中文", "Spanish", "French", "German", "Portuguese", "Arabic", "Russian"]


# ---------------------------------------------------------------------------
# Template CRUD
# ---------------------------------------------------------------------------

def _load_marketplace() -> list[dict]:
    return load_json(_MARKETPLACE_FILE, default=[])


def _save_marketplace(templates: list[dict]) -> None:
    save_json(_MARKETPLACE_FILE, templates)


def publish_template(
    author: str,
    title: str,
    content: str,
    category: str,
    description: str = "",
    language: str = "English",
    industry: str = "通用",
    tags: list[str] | None = None,
    is_premium: bool = False,
    variables: list[str] | None = None,
) -> tuple[bool, str, str]:
    """
    Publish a template to the marketplace.

    Args:
        author: Username of the template author
        title: Template title
        content: Template content (with optional {variable} placeholders)
        category: Category ID (from CATEGORIES)
        description: Short description of the template
        language: Primary language of the template
        industry: Target industry
        tags: Optional list of search tags
        is_premium: Whether this is a premium (Pro-only) template
        variables: List of placeholder variable names in the template

    Returns:
        (success, message, template_id) tuple
    """
    if not title or not title.strip():
        return False, "Title is required", ""
    if not content or not content.strip():
        return False, "Content is required", ""
    if len(content) < 20:
        return False, "Template content too short (min 20 chars)", ""
    if category not in [c["id"] for c in CATEGORIES]:
        return False, f"Invalid category: {category}", ""

    templates = _load_marketplace()

    # Check for duplicate title by same author
    for t in templates:
        if t["author"] == author and t["title"].lower() == title.strip().lower():
            return False, "You already have a template with this title", ""

    template_id = secrets.token_hex(6)

    # Auto-detect variables in content ({variable_name} pattern)
    import re
    detected_vars = re.findall(r'\{(\w+)\}', content)
    all_variables = list(set((variables or []) + detected_vars))

    template = {
        "id": template_id,
        "author": author,
        "title": title.strip(),
        "description": description.strip() or _auto_description(content),
        "content": content.strip(),
        "category": category,
        "language": language,
        "industry": industry,
        "tags": tags or [],
        "variables": all_variables,
        "is_premium": is_premium,
        "status": "published",  # published / hidden / flagged
        "stats": {
            "uses": 0,
            "ratings": [],
            "avg_rating": 0.0,
            "favorites": 0,
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    templates.append(template)
    _save_marketplace(templates)
    logger.info("Template published: '%s' by %s (id=%s)", title, author, template_id)
    return True, "Template published successfully", template_id


def update_template(
    template_id: str,
    author: str,
    **updates,
) -> tuple[bool, str]:
    """
    Update an existing template (only by the original author).

    Args:
        template_id: Template to update
        author: Must match the original author
        **updates: Fields to update (title, content, description, tags, etc.)

    Returns:
        (success, message) tuple
    """
    templates = _load_marketplace()
    for t in templates:
        if t["id"] == template_id:
            if t["author"] != author:
                return False, "Only the author can update this template"

            allowed_fields = {"title", "content", "description", "category", "language", "industry", "tags", "is_premium"}
            for key, value in updates.items():
                if key in allowed_fields:
                    t[key] = value
            t["updated_at"] = datetime.now().isoformat()
            _save_marketplace(templates)
            return True, "Template updated"

    return False, "Template not found"


def delete_template(template_id: str, username: str) -> tuple[bool, str]:
    """Soft-delete a template (hide from marketplace)."""
    templates = _load_marketplace()
    for t in templates:
        if t["id"] == template_id:
            if t["author"] != username:
                return False, "Only the author can delete this template"
            t["status"] = "hidden"
            _save_marketplace(templates)
            return True, "Template removed from marketplace"
    return False, "Template not found"


# ---------------------------------------------------------------------------
# Browse & search
# ---------------------------------------------------------------------------

def browse_templates(
    category: str = "",
    language: str = "",
    industry: str = "",
    search: str = "",
    sort_by: str = "popular",  # popular, newest, rating
    include_premium: bool = True,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """
    Browse/search marketplace templates.

    Args:
        category: Filter by category ID
        language: Filter by language
        industry: Filter by industry
        search: Free-text search in title, description, tags
        sort_by: Sorting method (popular, newest, rating)
        include_premium: Whether to include premium templates
        limit: Max results
        offset: Pagination offset

    Returns:
        List of template dicts (without full content, use get_template for that)
    """
    templates = _load_marketplace()

    # Filter only published templates
    results = [t for t in templates if t.get("status") == "published"]

    # Apply filters
    if category:
        results = [t for t in results if t["category"] == category]
    if language:
        results = [t for t in results if t["language"] == language]
    if industry:
        results = [t for t in results if t["industry"] == industry]
    if not include_premium:
        results = [t for t in results if not t.get("is_premium")]
    if search:
        q = search.lower()
        results = [
            t for t in results
            if q in t["title"].lower()
            or q in t.get("description", "").lower()
            or any(q in tag.lower() for tag in t.get("tags", []))
        ]

    # Sort
    if sort_by == "popular":
        results.sort(key=lambda t: t.get("stats", {}).get("uses", 0), reverse=True)
    elif sort_by == "newest":
        results.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    elif sort_by == "rating":
        results.sort(key=lambda t: t.get("stats", {}).get("avg_rating", 0), reverse=True)

    # Paginate
    paginated = results[offset:offset + limit]

    # Return summary (without full content for performance)
    return [_template_summary(t) for t in paginated]


def get_template(template_id: str) -> dict | None:
    """Get a single template by ID (including full content)."""
    templates = _load_marketplace()
    for t in templates:
        if t["id"] == template_id and t.get("status") == "published":
            return t
    return None


def get_user_templates(username: str) -> list[dict]:
    """Get all templates published by a user."""
    templates = _load_marketplace()
    return [t for t in templates if t["author"] == username and t["status"] != "hidden"]


# ---------------------------------------------------------------------------
# Usage & rating
# ---------------------------------------------------------------------------

def use_template(template_id: str, username: str) -> tuple[bool, str, str]:
    """
    Record that a user is using a template (increment usage counter).

    Args:
        template_id: Template being used
        username: User using the template

    Returns:
        (success, message, template_content) tuple
    """
    templates = _load_marketplace()
    for t in templates:
        if t["id"] == template_id:
            if t.get("status") != "published":
                return False, "Template not available", ""

            # Check premium access
            if t.get("is_premium"):
                if not _user_has_pro(username):
                    return False, "This template requires Pro plan", ""

            # Increment usage
            stats = t.get("stats", {})
            stats["uses"] = stats.get("uses", 0) + 1
            t["stats"] = stats
            _save_marketplace(templates)

            # Award credits to author (1 credit per 10 uses)
            if stats["uses"] % 10 == 0 and t["author"] != username:
                from utils.referral import _award_credits
                _award_credits(t["author"], 1, f"Template '{t['title']}' used {stats['uses']} times")

            logger.debug("Template used: %s by %s (total=%d)", template_id, username, stats["uses"])
            return True, "Template loaded", t["content"]

    return False, "Template not found", ""


def rate_template(template_id: str, username: str, rating: int, comment: str = "") -> tuple[bool, str]:
    """
    Rate a marketplace template (1-5 stars).

    Args:
        template_id: Template to rate
        username: User rating it
        rating: 1-5 star rating
        comment: Optional review comment

    Returns:
        (success, message) tuple
    """
    if not 1 <= rating <= 5:
        return False, "Rating must be between 1 and 5"

    templates = _load_marketplace()
    for t in templates:
        if t["id"] == template_id:
            stats = t.get("stats", {})
            ratings = stats.get("ratings", [])

            # Update or add rating
            existing = next((r for r in ratings if r["username"] == username), None)
            if existing:
                existing["rating"] = rating
                existing["comment"] = comment
                existing["updated_at"] = datetime.now().isoformat()
            else:
                ratings.append({
                    "username": username,
                    "rating": rating,
                    "comment": comment,
                    "created_at": datetime.now().isoformat(),
                })

            # Recalculate average
            stats["ratings"] = ratings[-100:]  # Keep last 100
            if ratings:
                stats["avg_rating"] = round(sum(r["rating"] for r in ratings) / len(ratings), 1)
            t["stats"] = stats
            _save_marketplace(templates)
            return True, "Rating submitted"

    return False, "Template not found"


def favorite_template(template_id: str, username: str) -> tuple[bool, str]:
    """Toggle favorite status for a template."""
    templates = _load_marketplace()
    for t in templates:
        if t["id"] == template_id:
            stats = t.get("stats", {})
            favorites_list = stats.get("favorited_by", [])
            if username in favorites_list:
                favorites_list.remove(username)
                stats["favorites"] = max(0, stats.get("favorites", 0) - 1)
                msg = "Removed from favorites"
            else:
                favorites_list.append(username)
                stats["favorites"] = stats.get("favorites", 0) + 1
                msg = "Added to favorites"
            stats["favorited_by"] = favorites_list
            t["stats"] = stats
            _save_marketplace(templates)
            return True, msg
    return False, "Template not found"


# ---------------------------------------------------------------------------
# Trending & featured
# ---------------------------------------------------------------------------

def get_trending(limit: int = 10) -> list[dict]:
    """
    Get trending templates (most used in the last 7 days).

    For simplicity, uses total usage count. In production,
    would track recent usage with timestamps.
    """
    templates = _load_marketplace()
    published = [t for t in templates if t.get("status") == "published"]
    published.sort(key=lambda t: t.get("stats", {}).get("uses", 0), reverse=True)
    return [_template_summary(t) for t in published[:limit]]


def get_featured(limit: int = 5) -> list[dict]:
    """Get hand-picked featured templates (high rating + high usage)."""
    templates = _load_marketplace()
    published = [t for t in templates if t.get("status") == "published"]

    # Score = avg_rating * 2 + log(uses)
    import math
    for t in published:
        stats = t.get("stats", {})
        uses = max(stats.get("uses", 0), 1)
        rating = stats.get("avg_rating", 3.0)
        t["_score"] = rating * 2 + math.log(uses)

    published.sort(key=lambda t: t.get("_score", 0), reverse=True)
    return [_template_summary(t) for t in published[:limit]]


def get_marketplace_stats() -> dict:
    """Get overall marketplace statistics."""
    templates = _load_marketplace()
    published = [t for t in templates if t.get("status") == "published"]

    total_uses = sum(t.get("stats", {}).get("uses", 0) for t in published)
    unique_authors = len(set(t["author"] for t in published))

    category_counts = {}
    for t in published:
        cat = t["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "total_templates": len(published),
        "total_uses": total_uses,
        "unique_authors": unique_authors,
        "category_distribution": category_counts,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _template_summary(t: dict) -> dict:
    """Return a template dict without full content (for listing pages)."""
    return {
        "id": t["id"],
        "title": t["title"],
        "description": t.get("description", ""),
        "author": t["author"],
        "category": t["category"],
        "language": t["language"],
        "industry": t["industry"],
        "tags": t.get("tags", []),
        "is_premium": t.get("is_premium", False),
        "variables": t.get("variables", []),
        "stats": t.get("stats", {}),
        "created_at": t.get("created_at", ""),
    }


def _auto_description(content: str) -> str:
    """Generate a short description from template content."""
    # First 80 chars, clean up
    desc = content[:80].replace("\n", " ").strip()
    if len(content) > 80:
        desc += "..."
    return desc


def _user_has_pro(username: str) -> bool:
    """Check if a user has Pro (or higher) plan access."""
    try:
        from utils.pricing import get_user_tier
        tier = get_user_tier(username)
        return tier in ("pro", "team", "enterprise")
    except Exception:
        return False
