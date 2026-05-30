"""
utils/inbox_ai.py
-----------------
AI-powered inbox management: automatic email classification, priority scoring,
and suggested reply generation.

This is the "AI Email Butler" — the killer differentiator.

Pipeline:
  1. Fetch unread emails from connected inbox
  2. AI classifies each email's intent (inquiry, negotiation, complaint, etc.)
  3. Score urgency/priority based on intent + customer profile
  4. Generate suggested reply for high-priority emails
  5. Present prioritized inbox to the user

Intent Categories:
  - inquiry: Customer asking for info/quote
  - negotiation: Price/terms discussion
  - order_intent: Ready to buy, asking for PI/contract
  - sample_request: Wants samples
  - complaint: Issue/problem reported
  - followup_needed: Waiting for our action
  - info_only: Newsletter, notification, no action needed
  - spam: Irrelevant/marketing spam

Usage:
    from utils.inbox_ai import (
        classify_email,
        process_inbox,
        generate_reply_suggestion,
        get_prioritized_inbox,
    )
"""
from __future__ import annotations

from datetime import datetime
from typing import Generator

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("inbox_ai")

# ---------------------------------------------------------------------------
# Intent definitions
# ---------------------------------------------------------------------------

INTENT_CATEGORIES = {
    "inquiry": {
        "label": "询盘/咨询",
        "label_en": "Inquiry",
        "priority": 8,
        "icon": "📩",
        "action": "回复报价或产品信息",
        "urgency_hours": 4,
    },
    "order_intent": {
        "label": "下单意向",
        "label_en": "Order Intent",
        "priority": 9,
        "icon": "💰",
        "action": "发送PI/确认订单细节",
        "urgency_hours": 2,
    },
    "negotiation": {
        "label": "价格谈判",
        "label_en": "Negotiation",
        "priority": 7,
        "icon": "🤝",
        "action": "回复报价调整或条件",
        "urgency_hours": 8,
    },
    "sample_request": {
        "label": "样品请求",
        "label_en": "Sample Request",
        "priority": 7,
        "icon": "📦",
        "action": "确认样品细节和费用",
        "urgency_hours": 12,
    },
    "complaint": {
        "label": "投诉/问题",
        "label_en": "Complaint",
        "priority": 9,
        "icon": "⚠️",
        "action": "立即回复并提出解决方案",
        "urgency_hours": 2,
    },
    "followup_needed": {
        "label": "需要跟进",
        "label_en": "Follow-up Needed",
        "priority": 6,
        "icon": "📬",
        "action": "按约定回复或提供更新",
        "urgency_hours": 24,
    },
    "info_only": {
        "label": "仅信息",
        "label_en": "Info Only",
        "priority": 2,
        "icon": "📋",
        "action": "无需回复，归档",
        "urgency_hours": 0,
    },
    "spam": {
        "label": "垃圾/无关",
        "label_en": "Spam/Irrelevant",
        "priority": 0,
        "icon": "🗑️",
        "action": "忽略或退订",
        "urgency_hours": 0,
    },
}

_PROCESSED_FILE = "inbox_processed.json"

# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

_CLASSIFICATION_SYSTEM = """You are an expert foreign trade email analyst.
Your job is to classify incoming emails into exactly one intent category
and assess urgency. You must respond ONLY in the exact JSON format specified.

Intent categories:
- inquiry: Customer asking about products, prices, MOQ, certifications
- order_intent: Customer ready to place order, asking for PI, contract, payment
- negotiation: Discussing price adjustments, payment terms, delivery conditions
- sample_request: Requesting product samples
- complaint: Reporting quality issues, delivery problems, discrepancies
- followup_needed: Customer waiting for our response/action on a previous topic
- info_only: Auto-replies, newsletters, shipping notifications, no action needed
- spam: Marketing spam, unrelated solicitations
"""

_CLASSIFICATION_PROMPT = """Analyze this email and classify it.

From: {from_email}
Subject: {subject}
Body preview: {snippet}

Respond in this exact JSON format (no markdown, no extra text):
{{"intent": "<category>", "confidence": <0.0-1.0>, "urgency": "<high|medium|low>", "key_points": ["point1", "point2"], "suggested_action": "<brief action recommendation>"}}
"""

_REPLY_SYSTEM = """You are a professional foreign trade business development representative.
Generate a suggested reply email based on the incoming email's intent and content.
Keep the reply concise (50-100 words), professional, and action-oriented.
Write in English unless the original email is in another language."""

_REPLY_PROMPT = """Generate a professional reply to this email:

Original email:
From: {from_email}
Subject: {subject}
Content: {snippet}

Detected intent: {intent} ({intent_label})
Key points: {key_points}

Requirements:
1. Address the sender professionally
2. Acknowledge their {intent_label} clearly
3. Provide a concrete next step or answer
4. Keep it concise (50-100 words)
5. Sign off with [Your Name] / [Your Company]

Output ONLY the reply text, no subject line, no markdown."""


# ---------------------------------------------------------------------------
# Core classification
# ---------------------------------------------------------------------------

def classify_email(
    from_email: str,
    subject: str,
    snippet: str,
    user_id: str = "default",
) -> dict:
    """
    Classify a single email using AI.

    Args:
        from_email: Sender email/name
        subject: Email subject line
        snippet: Body preview (first 200-500 chars)
        user_id: For rate limiting

    Returns:
        Dict with: intent, confidence, urgency, key_points, suggested_action,
                   priority_score, intent_info
    """
    from utils.ai_client import call_llm

    prompt = _CLASSIFICATION_PROMPT.format(
        from_email=from_email,
        subject=subject,
        snippet=snippet[:500],
    )

    result_text = call_llm(
        prompt=prompt,
        system_prompt=_CLASSIFICATION_SYSTEM,
        user_id=user_id,
        temperature=0.1,  # Low temp for consistent classification
        max_tokens=200,
    )

    # Parse JSON response
    classification = _parse_classification(result_text)

    # Enrich with intent metadata
    intent = classification.get("intent", "info_only")
    intent_info = INTENT_CATEGORIES.get(intent, INTENT_CATEGORIES["info_only"])

    classification["priority_score"] = _calculate_priority(classification, intent_info)
    classification["intent_info"] = intent_info

    return classification


def _parse_classification(text: str) -> dict:
    """Parse the AI classification JSON response."""
    import json

    # Try to extract JSON from the response
    text = text.strip()

    # Handle potential markdown code block wrapping
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        data = json.loads(text)
        # Validate required fields
        if "intent" not in data:
            data["intent"] = "info_only"
        if data["intent"] not in INTENT_CATEGORIES:
            data["intent"] = "info_only"
        data.setdefault("confidence", 0.5)
        data.setdefault("urgency", "medium")
        data.setdefault("key_points", [])
        data.setdefault("suggested_action", "")
        return data
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse classification JSON: %s", text[:100])
        return {
            "intent": "info_only",
            "confidence": 0.3,
            "urgency": "low",
            "key_points": [],
            "suggested_action": "Review manually",
        }


def _calculate_priority(classification: dict, intent_info: dict) -> int:
    """
    Calculate a 0-100 priority score for inbox ordering.

    Factors:
    - Base priority from intent category (0-9 → 0-45)
    - Urgency multiplier (high=2x, medium=1.5x, low=1x)
    - Confidence weight
    """
    base = intent_info.get("priority", 5) * 5  # 0-45
    urgency_mult = {"high": 2.0, "medium": 1.5, "low": 1.0}.get(
        classification.get("urgency", "medium"), 1.0
    )
    confidence = classification.get("confidence", 0.5)

    score = base * urgency_mult * (0.5 + confidence * 0.5)
    return min(100, max(0, int(score)))


# ---------------------------------------------------------------------------
# Batch inbox processing
# ---------------------------------------------------------------------------

def process_inbox(
    username: str,
    emails: list[dict],
    force_reprocess: bool = False,
) -> list[dict]:
    """
    Process a batch of emails: classify each and return prioritized list.

    Args:
        username: User whose inbox is being processed
        emails: List of email dicts (from inbox_integration.fetch_inbox)
        force_reprocess: If True, re-classify already-processed emails

    Returns:
        List of classified email dicts, sorted by priority (highest first)
    """
    processed_cache = load_user_json(username, _PROCESSED_FILE, default={})
    results = []

    for email in emails:
        email_id = email.get("id", "")

        # Use cached classification if available
        if not force_reprocess and email_id in processed_cache:
            cached = processed_cache[email_id]
            cached["email"] = email
            results.append(cached)
            continue

        # Classify this email
        classification = classify_email(
            from_email=email.get("from", ""),
            subject=email.get("subject", ""),
            snippet=email.get("snippet", ""),
            user_id=username,
        )

        # Merge email data with classification
        entry = {
            "email_id": email_id,
            "email": email,
            "classification": classification,
            "priority_score": classification.get("priority_score", 0),
            "processed_at": datetime.now().isoformat(),
        }

        # Cache the result
        processed_cache[email_id] = {
            "classification": classification,
            "priority_score": classification.get("priority_score", 0),
            "processed_at": entry["processed_at"],
        }
        results.append(entry)

    # Save cache (keep last 200 entries to prevent bloat)
    if len(processed_cache) > 200:
        # Keep only most recent 200
        sorted_items = sorted(
            processed_cache.items(),
            key=lambda x: x[1].get("processed_at", ""),
            reverse=True,
        )
        processed_cache = dict(sorted_items[:200])
    save_user_json(username, _PROCESSED_FILE, processed_cache)

    # Sort by priority (highest first)
    results.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    logger.info("Processed %d emails for %s", len(results), username)
    return results


def get_prioritized_inbox(username: str, limit: int = 20) -> list[dict]:
    """
    Get the user's prioritized inbox (previously processed emails).

    Returns cached classifications sorted by priority.
    Useful for displaying without re-running AI classification.
    """
    processed_cache = load_user_json(username, _PROCESSED_FILE, default={})

    results = []
    for email_id, data in processed_cache.items():
        entry = {
            "email_id": email_id,
            "classification": data.get("classification", {}),
            "priority_score": data.get("priority_score", 0),
            "processed_at": data.get("processed_at", ""),
        }
        results.append(entry)

    results.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    return results[:limit]


# ---------------------------------------------------------------------------
# Reply suggestion
# ---------------------------------------------------------------------------

def generate_reply_suggestion(
    from_email: str,
    subject: str,
    snippet: str,
    intent: str,
    key_points: list[str] | None = None,
    user_id: str = "default",
    stream: bool = False,
) -> str | Generator[str, None, None]:
    """
    Generate a suggested reply for a classified email.

    Args:
        from_email: Original sender
        subject: Original subject
        snippet: Original body preview
        intent: Classified intent category
        key_points: Key points from classification
        user_id: For rate limiting
        stream: Whether to stream the response

    Returns:
        Reply text string (or generator if stream=True)
    """
    from utils.ai_client import call_llm, stream_llm

    intent_info = INTENT_CATEGORIES.get(intent, INTENT_CATEGORIES["info_only"])

    prompt = _REPLY_PROMPT.format(
        from_email=from_email,
        subject=subject,
        snippet=snippet[:800],
        intent=intent,
        intent_label=intent_info["label"],
        key_points=", ".join(key_points or ["General inquiry"]),
    )

    if stream:
        return stream_llm(prompt, _REPLY_SYSTEM, user_id, temperature=0.7)
    return call_llm(prompt, _REPLY_SYSTEM, user_id, temperature=0.7)


# ---------------------------------------------------------------------------
# Inbox analytics
# ---------------------------------------------------------------------------

def get_inbox_analytics(username: str) -> dict:
    """
    Get analytics summary of the user's processed inbox.

    Returns:
        Dict with intent_distribution, avg_priority, urgent_count, etc.
    """
    processed_cache = load_user_json(username, _PROCESSED_FILE, default={})

    if not processed_cache:
        return {
            "total_processed": 0,
            "intent_distribution": {},
            "urgent_count": 0,
            "avg_priority": 0,
        }

    intent_counts: dict[str, int] = {}
    priorities = []
    urgent = 0

    for _id, data in processed_cache.items():
        classification = data.get("classification", {})
        intent = classification.get("intent", "info_only")
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        priorities.append(data.get("priority_score", 0))
        if classification.get("urgency") == "high":
            urgent += 1

    return {
        "total_processed": len(processed_cache),
        "intent_distribution": intent_counts,
        "urgent_count": urgent,
        "avg_priority": round(sum(priorities) / len(priorities), 1) if priorities else 0,
        "top_intents": sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5],
    }
