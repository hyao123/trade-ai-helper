"""
utils/ab_testing.py
-------------------
A/B Testing framework for email subject lines and content variants.

Features:
- Generate multiple variants of email subject lines / content
- Track open rates and click rates (simulated for demo)
- Statistical significance calculation
- Persist test results per user
"""

from __future__ import annotations

import datetime
import random
import uuid
from dataclasses import dataclass, field

import streamlit as st

from utils.logger import get_logger
from utils.storage import load_json, load_user_json, save_json, save_user_json

logger = get_logger("ab_testing")

_AB_FILENAME = "ab_tests.json"

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class ABVariant:
    """A single variant in an A/B test."""
    variant_id: str
    label: str  # e.g. "A", "B", "C"
    content: str
    subject_line: str = ""
    sends: int = 0
    opens: int = 0
    clicks: int = 0
    replies: int = 0

    @property
    def open_rate(self) -> float:
        return (self.opens / self.sends * 100) if self.sends > 0 else 0.0

    @property
    def click_rate(self) -> float:
        return (self.clicks / self.sends * 100) if self.sends > 0 else 0.0

    @property
    def reply_rate(self) -> float:
        return (self.replies / self.sends * 100) if self.sends > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "label": self.label,
            "content": self.content,
            "subject_line": self.subject_line,
            "sends": self.sends,
            "opens": self.opens,
            "clicks": self.clicks,
            "replies": self.replies,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ABVariant":
        return cls(
            variant_id=d.get("variant_id", str(uuid.uuid4())[:8]),
            label=d.get("label", "A"),
            content=d.get("content", ""),
            subject_line=d.get("subject_line", ""),
            sends=d.get("sends", 0),
            opens=d.get("opens", 0),
            clicks=d.get("clicks", 0),
            replies=d.get("replies", 0),
        )


@dataclass
class ABTest:
    """An A/B test with multiple variants."""
    test_id: str
    name: str
    product: str
    created_at: str
    status: str = "draft"  # draft, running, completed
    variants: list[ABVariant] = field(default_factory=list)
    winner: str | None = None  # variant_id of winner

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "product": self.product,
            "created_at": self.created_at,
            "status": self.status,
            "variants": [v.to_dict() for v in self.variants],
            "winner": self.winner,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ABTest":
        return cls(
            test_id=d.get("test_id", str(uuid.uuid4())[:8]),
            name=d.get("name", ""),
            product=d.get("product", ""),
            created_at=d.get("created_at", ""),
            status=d.get("status", "draft"),
            variants=[ABVariant.from_dict(v) for v in d.get("variants", [])],
            winner=d.get("winner"),
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _get_current_username() -> str | None:
    """Get current logged-in username."""
    user = st.session_state.get("current_user")
    if user and user.get("username") and user["username"] != "admin":
        return user["username"]
    return None


def load_ab_tests() -> list[ABTest]:
    """Load all A/B tests for the current user."""
    username = _get_current_username()
    if username:
        data = load_user_json(username, _AB_FILENAME, default=[])
    else:
        data = load_json(_AB_FILENAME, default=[])
    return [ABTest.from_dict(d) for d in data]


def save_ab_tests(tests: list[ABTest]) -> None:
    """Save all A/B tests for the current user."""
    data = [t.to_dict() for t in tests]
    username = _get_current_username()
    if username:
        save_user_json(username, _AB_FILENAME, data)
    else:
        save_json(_AB_FILENAME, data)


def get_ab_test(test_id: str) -> ABTest | None:
    """Get a specific A/B test by ID."""
    tests = load_ab_tests()
    for t in tests:
        if t.test_id == test_id:
            return t
    return None


def create_ab_test(name: str, product: str, variants: list[ABVariant]) -> ABTest:
    """Create and persist a new A/B test."""
    test = ABTest(
        test_id=str(uuid.uuid4())[:8],
        name=name,
        product=product,
        created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        status="draft",
        variants=variants,
    )
    tests = load_ab_tests()
    tests.insert(0, test)
    # Keep max 20 tests
    if len(tests) > 20:
        tests = tests[:20]
    save_ab_tests(tests)
    logger.info("Created A/B test: %s with %d variants", test.test_id, len(variants))
    return test


def update_ab_test(test: ABTest) -> None:
    """Update an existing A/B test."""
    tests = load_ab_tests()
    for i, t in enumerate(tests):
        if t.test_id == test.test_id:
            tests[i] = test
            break
    save_ab_tests(tests)


def delete_ab_test(test_id: str) -> bool:
    """Delete an A/B test by ID."""
    tests = load_ab_tests()
    original_len = len(tests)
    tests = [t for t in tests if t.test_id != test_id]
    if len(tests) < original_len:
        save_ab_tests(tests)
        return True
    return False


# ---------------------------------------------------------------------------
# Simulation helpers (for demo/testing without real email sending)
# ---------------------------------------------------------------------------
def simulate_results(test: ABTest, total_sends: int = 100) -> ABTest:
    """
    Simulate A/B test results for demo purposes.

    Each variant gets `total_sends` simulated sends with randomized
    open/click/reply rates based on content quality heuristics.
    """
    for variant in test.variants:
        # Base rates with some randomness
        subject_length = len(variant.subject_line)

        # Heuristic: shorter subjects tend to have higher open rates
        base_open = random.uniform(15, 45)
        if subject_length < 40:
            base_open += random.uniform(2, 8)
        if subject_length > 60:
            base_open -= random.uniform(2, 5)

        # Heuristic: content with questions tends to get more replies
        has_question = "?" in variant.content
        base_reply = random.uniform(2, 12)
        if has_question:
            base_reply += random.uniform(1, 5)

        variant.sends = total_sends
        variant.opens = int(total_sends * base_open / 100)
        variant.clicks = int(variant.opens * random.uniform(0.1, 0.4))
        variant.replies = int(total_sends * base_reply / 100)

    test.status = "completed"

    # Determine winner by reply rate
    if test.variants:
        best = max(test.variants, key=lambda v: v.reply_rate)
        test.winner = best.variant_id

    update_ab_test(test)
    return test


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------
def compute_confidence(variant_a: ABVariant, variant_b: ABVariant) -> float:
    """
    Compute approximate statistical confidence between two variants
    using a simplified z-test for proportions.

    Returns confidence level as percentage (0-100).
    """
    if variant_a.sends == 0 or variant_b.sends == 0:
        return 0.0

    p1 = variant_a.open_rate / 100
    p2 = variant_b.open_rate / 100
    n1 = variant_a.sends
    n2 = variant_b.sends

    # Pooled proportion
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2) if (n1 + n2) > 0 else 0

    if p_pool == 0 or p_pool == 1:
        return 0.0

    # Standard error
    se = (p_pool * (1 - p_pool) * (1/n1 + 1/n2)) ** 0.5
    if se == 0:
        return 0.0

    # Z-score
    z = abs(p1 - p2) / se

    # Approximate confidence from z-score
    # z=1.65 -> 90%, z=1.96 -> 95%, z=2.58 -> 99%
    if z >= 2.58:
        return 99.0
    elif z >= 1.96:
        return 95.0
    elif z >= 1.65:
        return 90.0
    elif z >= 1.28:
        return 80.0
    else:
        return round(min(z / 1.96 * 95, 79.0), 1)


def get_test_summary(test: ABTest) -> dict:
    """Get a summary dict for display purposes."""
    return {
        "test_id": test.test_id,
        "name": test.name,
        "product": test.product,
        "status": test.status,
        "variants_count": len(test.variants),
        "created_at": test.created_at,
        "winner": test.winner,
        "best_open_rate": max((v.open_rate for v in test.variants), default=0),
        "best_reply_rate": max((v.reply_rate for v in test.variants), default=0),
    }
