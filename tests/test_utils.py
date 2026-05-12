"""
tests/test_utils.py
Unit tests for core utility functions (no API calls needed).
"""
from __future__ import annotations

import sys
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# Test storage module
# ---------------------------------------------------------------------------
class TestStorage:
    """Tests for utils/storage.py JSON persistence layer."""

    def _make_temp_dir(self):
        return Path(tempfile.mkdtemp())

    def test_load_json_returns_default_when_file_not_found(self):
        from utils.storage import load_json
        tmp_dir = self._make_temp_dir()
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            result = load_json("nonexistent.json")
            assert result == []

    def test_load_json_returns_custom_default(self):
        from utils.storage import load_json
        tmp_dir = self._make_temp_dir()
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            result = load_json("nonexistent.json", default={})
            assert result == {}

    def test_save_json_writes_valid_json(self):
        from utils.storage import load_json, save_json
        tmp_dir = self._make_temp_dir()
        test_data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            save_json("test.json", test_data)
            loaded = load_json("test.json")
            assert loaded == test_data

    def test_atomic_write_produces_final_file(self):
        from utils.storage import save_json
        tmp_dir = self._make_temp_dir()
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            save_json("atomic_test.json", {"key": "value"})
            # Final file should exist, .tmp should not
            assert (tmp_dir / "atomic_test.json").exists()
            assert not (tmp_dir / "atomic_test.tmp").exists()

    def test_save_json_overwrites_existing(self):
        from utils.storage import load_json, save_json
        tmp_dir = self._make_temp_dir()
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            save_json("overwrite.json", [1, 2, 3])
            save_json("overwrite.json", [4, 5, 6])
            loaded = load_json("overwrite.json")
            assert loaded == [4, 5, 6]

    def test_load_json_handles_invalid_json(self):
        from utils.storage import load_json
        tmp_dir = self._make_temp_dir()
        # Write invalid JSON
        bad_file = tmp_dir / "bad.json"
        bad_file.write_text("not valid json {{{", encoding="utf-8")
        with patch("utils.storage.get_data_dir", return_value=tmp_dir):
            result = load_json("bad.json", default=[])
            assert result == []

    def test_get_data_dir_creates_directory(self):
        from utils.storage import get_data_dir
        # Simply test the real function creates directory
        data_dir = get_data_dir()
        assert data_dir.exists()
        assert data_dir.is_dir()
