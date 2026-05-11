"""
tests/test_utils.py
Unit tests for core utility functions (no API calls needed).
"""
import sys
import os
import time

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Test extract_subject
# ---------------------------------------------------------------------------
class TestExtractSubject:
    """Tests for ui_helpers.extract_subject()."""

    def _extract(self, text):
        from utils.ui_helpers import extract_subject
        return extract_subject(text)

    def test_basic_subject(self):
        text = "Subject: Hello World\n\nDear John,\nHope this finds you well."
        subject, body = self._extract(text)
        assert subject == "Hello World"
        assert body.startswith("Dear John")

    def test_subject_no_space(self):
        text = "Subject:Quick Offer\nBody here"
        subject, body = self._extract(text)
        assert subject == "Quick Offer"
        assert body == "Body here"

    def test_subject_with_bold_markdown(self):
        text = "**Subject:** Special Offer for LED Lamps\n\nHi there"
        subject, body = self._extract(text)
        assert subject == "Special Offer for LED Lamps"
        assert body == "Hi there"

    def test_subject_line_variant(self):
        text = "Subject Line: Great Deal Inside\n\nBody"
        subject, body = self._extract(text)
        assert subject == "Great Deal Inside"

    def test_no_subject(self):
        text = "Dear John,\nI am writing to inquire..."
        subject, body = self._extract(text)
        assert subject == ""
        assert body == text.strip()

    def test_empty_input(self):
        subject, body = self._extract("")
        assert subject == ""

    def test_skips_blank_lines_after_subject(self):
        text = "Subject: Test\n\n\n\nActual body"
        subject, body = self._extract(text)
        assert subject == "Test"
        assert body == "Actual body"


# ---------------------------------------------------------------------------
# Test rate limiting
# ---------------------------------------------------------------------------
class TestRateLimiting:
    """Tests for ai_client rate limiting functions."""

    def test_rate_limit_check_allows_within_limit(self):
        from utils.ai_client import _rate_limit_check, _call_times, RATE_LIMIT_MAX_CALLS
        # Reset state
        test_user = "test_user_allow"
        _call_times[test_user] = []

        allowed, remaining = _rate_limit_check(test_user)
        assert allowed is True
        assert remaining == RATE_LIMIT_MAX_CALLS - 1

    def test_rate_limit_check_blocks_at_limit(self):
        from utils.ai_client import _rate_limit_check, _call_times, RATE_LIMIT_MAX_CALLS, RATE_LIMIT_WINDOW
        test_user = "test_user_block"
        # Fill up all slots
        now = time.time()
        _call_times[test_user] = [now - 1] * RATE_LIMIT_MAX_CALLS

        allowed, remaining = _rate_limit_check(test_user)
        assert allowed is False
        assert remaining == 0

    def test_rate_limit_expired_slots_freed(self):
        from utils.ai_client import _rate_limit_check, _call_times, RATE_LIMIT_MAX_CALLS, RATE_LIMIT_WINDOW
        test_user = "test_user_expired"
        # All slots expired
        _call_times[test_user] = [time.time() - RATE_LIMIT_WINDOW - 10] * RATE_LIMIT_MAX_CALLS

        allowed, remaining = _rate_limit_check(test_user)
        assert allowed is True

    def test_get_rate_limit_remaining(self):
        from utils.ai_client import get_rate_limit_remaining, _call_times, RATE_LIMIT_MAX_CALLS
        test_user = "test_user_remaining"
        _call_times[test_user] = []
        assert get_rate_limit_remaining(test_user) == RATE_LIMIT_MAX_CALLS


# ---------------------------------------------------------------------------
# Test PDF generation
# ---------------------------------------------------------------------------
class TestPdfGeneration:
    """Tests for pdf_gen.generate_quote_pdf()."""

    def test_generates_valid_pdf_bytes(self):
        from utils.pdf_gen import generate_quote_pdf
        skus = [
            {"product": "LED Lamp", "model": "XR-100", "price": 5.50, "quantity": 200, "unit": "PCS"},
            {"product": "Solar Panel", "model": "SP-200W", "price": 45.0, "quantity": 50, "unit": "SETS"},
        ]
        result = generate_quote_pdf(skus=skus)
        # PDF starts with %PDF
        assert result[:4] == b"%PDF"
        assert len(result) > 1000  # Non-trivial size

    def test_single_sku(self):
        from utils.pdf_gen import generate_quote_pdf
        skus = [{"product": "Test Product", "model": "", "price": 10.0, "quantity": 1, "unit": "PCS"}]
        result = generate_quote_pdf(skus=skus)
        assert result[:4] == b"%PDF"

    def test_long_product_name_truncated(self):
        from utils.pdf_gen import generate_quote_pdf
        long_name = "A" * 100  # Way longer than 38 chars
        skus = [{"product": long_name, "model": "X" * 50, "price": 1.0, "quantity": 1, "unit": "PCS"}]
        # Should not raise, PDF generated successfully with truncation
        result = generate_quote_pdf(skus=skus)
        assert result[:4] == b"%PDF"

    def test_buyer_info_included(self):
        from utils.pdf_gen import generate_quote_pdf
        skus = [{"product": "Widget", "model": "W1", "price": 2.0, "quantity": 10, "unit": "PCS"}]
        result = generate_quote_pdf(
            skus=skus,
            buyer_company="ABC Corp",
            buyer_contact="John",
            buyer_email="john@abc.com",
        )
        assert result[:4] == b"%PDF"
        assert len(result) > 1000

    def test_zero_price_allowed(self):
        """Free sample quotation should work."""
        from utils.pdf_gen import generate_quote_pdf
        skus = [{"product": "Free Sample", "model": "FS-01", "price": 0.0, "quantity": 5, "unit": "PCS"}]
        result = generate_quote_pdf(skus=skus)
        assert result[:4] == b"%PDF"
