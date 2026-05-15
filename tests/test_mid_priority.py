"""
tests/test_mid_priority.py
--------------------------
Unit tests for mid-priority features:
  - Customer scoring & tagging (utils/customers.py extensions)
  - HS Code & Intent recognition prompts (config/prompts.py)
  - Email service extensions (utils/email_service.py)
  - Workflow reminder extension (utils/workflow.py)
"""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Stub streamlit + dotenv
# ---------------------------------------------------------------------------
_st = types.ModuleType("streamlit")

_dotenv = types.ModuleType("dotenv")
_dotenv.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", _dotenv)


class _FakeState(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def pop(self, key, *args):
        return super().pop(key, *args) if args else super().pop(key)


_st.session_state = _FakeState()
sys.modules.setdefault("streamlit", _st)


# ---------------------------------------------------------------------------
# Customer scoring & tagging tests
# ---------------------------------------------------------------------------
import tempfile
from pathlib import Path


class TestCustomerScoring(unittest.TestCase):
    """Tests for compute_customer_score and tag helpers."""

    def _patch_storage(self, tmp_dir: Path):
        return patch("utils.storage.get_data_dir", return_value=tmp_dir)

    def test_score_increases_with_stage(self):
        from utils.customers import compute_customer_score
        low = compute_customer_score({"stage": "新客户", "last_contact": "2026-05-14"})
        mid = compute_customer_score({"stage": "已报价", "last_contact": "2026-05-14"})
        high = compute_customer_score({"stage": "已下单", "last_contact": "2026-05-14"})
        self.assertLess(low, mid)
        self.assertLess(mid, high)

    def test_score_range_0_to_100(self):
        from utils.customers import compute_customer_score
        for stage in ["新客户", "已询盘", "已下单", "长期合作"]:
            score = compute_customer_score({
                "stage": stage,
                "last_contact": "2026-05-14",
                "email": "test@test.com",
                "contact": "Tom",
                "product": "LED",
            })
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_recent_contact_gives_higher_score(self):
        from utils.customers import compute_customer_score
        recent = compute_customer_score({
            "stage": "已报价",
            "last_contact": "2026-05-13",  # 1 day ago
        })
        old = compute_customer_score({
            "stage": "已报价",
            "last_contact": "2025-01-01",  # > 90 days
        })
        self.assertGreater(recent, old)

    def test_complete_data_adds_score(self):
        from utils.customers import compute_customer_score
        incomplete = compute_customer_score({"stage": "新客户"})
        complete = compute_customer_score({
            "stage": "新客户",
            "email": "x@x.com",
            "contact": "Tom",
            "product": "LED",
            "last_contact": "2026-05-14",
        })
        self.assertGreater(complete, incomplete)

    def test_unknown_stage_defaults(self):
        from utils.customers import compute_customer_score
        score = compute_customer_score({"stage": "未知阶段", "last_contact": ""})
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_add_and_remove_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            _st.session_state.clear()
            with self._patch_storage(Path(tmp)):
                from utils.customers import (
                    add_customer,
                    add_tag,
                    get_customer_tags,
                    get_customers,
                    remove_tag,
                )
                add_customer({
                    "company": "Test Co", "contact": "Alice",
                    "email": "", "country": "USA", "product": "LED",
                    "stage": "新客户", "notes": "",
                    "created_at": "2026-05-14", "last_contact": "2026-05-14",
                })
                customers = get_customers()
                self.assertEqual(len(customers), 1)
                add_tag(0, "VIP")
                tags = get_customer_tags(0)
                self.assertIn("VIP", tags)
                remove_tag(0, "VIP")
                tags = get_customer_tags(0)
                self.assertNotIn("VIP", tags)

    def test_add_tag_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            _st.session_state.clear()
            with self._patch_storage(Path(tmp)):
                from utils.customers import add_customer, add_tag, get_customer_tags
                add_customer({
                    "company": "Dup Co", "contact": "Bob",
                    "email": "", "country": "UK", "product": "P",
                    "stage": "新客户", "notes": "",
                    "created_at": "2026-05-14", "last_contact": "2026-05-14",
                })
                add_tag(0, "高潜力")
                add_tag(0, "高潜力")
                tags = get_customer_tags(0)
                self.assertEqual(tags.count("高潜力"), 1)

    def test_get_customers_by_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            _st.session_state.clear()
            with self._patch_storage(Path(tmp)):
                from utils.customers import add_customer, add_tag, get_customers_by_tag
                add_customer({
                    "company": "A", "contact": "X", "email": "", "country": "USA",
                    "product": "P", "stage": "新客户", "notes": "",
                    "created_at": "2026-05-14", "last_contact": "2026-05-14",
                })
                add_customer({
                    "company": "B", "contact": "Y", "email": "", "country": "UK",
                    "product": "Q", "stage": "新客户", "notes": "",
                    "created_at": "2026-05-14", "last_contact": "2026-05-14",
                })
                add_tag(0, "VIP")
                result = get_customers_by_tag("VIP")
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["company"], "A")


# ---------------------------------------------------------------------------
# HS Code & Intent prompt tests
# ---------------------------------------------------------------------------
class TestNewPrompts(unittest.TestCase):

    def test_hs_code_prompt_contains_product(self):
        from config.prompts import build_hs_code_prompt
        prompt, system = build_hs_code_prompt("LED Street Light", "100W aluminum", "USA")
        self.assertIn("LED Street Light", prompt)
        self.assertIn("USA", prompt)
        self.assertIn("100W aluminum", prompt)
        self.assertIn("HS Code", prompt)
        self.assertIsNotNone(system)

    def test_hs_code_prompt_without_optional_fields(self):
        from config.prompts import build_hs_code_prompt
        prompt, system = build_hs_code_prompt("Solar Panel")
        self.assertIn("Solar Panel", prompt)
        self.assertNotIn("Target Import Country", prompt)
        self.assertNotIn("Detailed Description", prompt)

    def test_hs_code_prompt_has_required_sections(self):
        from config.prompts import build_hs_code_prompt
        prompt, _ = build_hs_code_prompt("Electric Motor")
        self.assertIn("Primary HS Code", prompt)
        self.assertIn("Classification Reasoning", prompt)
        self.assertIn("Alternative HS Codes", prompt)

    def test_intent_recognition_prompt_contains_email(self):
        from config.prompts import build_intent_recognition_prompt
        email = "Hi, can you send me your best price for 1000 units?"
        prompt, system = build_intent_recognition_prompt(email)
        self.assertIn(email, prompt)
        self.assertIn("Primary Intent", prompt)
        self.assertIn("Recommended Next Action", prompt)
        self.assertIsNotNone(system)

    def test_intent_recognition_with_context(self):
        from config.prompts import build_intent_recognition_prompt
        prompt, _ = build_intent_recognition_prompt(
            "We already ordered 500 pcs", context="This is a repeat customer"
        )
        self.assertIn("repeat customer", prompt)

    def test_intent_recognition_sanitizes_long_input(self):
        from config.prompts import build_intent_recognition_prompt
        long_email = "A" * 5000
        prompt, _ = build_intent_recognition_prompt(long_email)
        # Sanitized to max 3000 chars
        self.assertNotIn("A" * 5000, prompt)
        self.assertGreater(len(prompt), 100)

    def test_intent_recognition_has_sentiment_section(self):
        from config.prompts import build_intent_recognition_prompt
        prompt, _ = build_intent_recognition_prompt("Interested in your product")
        self.assertIn("Sentiment Analysis", prompt)
        self.assertIn("Urgency Level", prompt)


# ---------------------------------------------------------------------------
# Email service extension tests
# ---------------------------------------------------------------------------
import importlib

import utils.email_service as _email_svc_mod


class TestEmailServiceExtensions(unittest.TestCase):

    def setUp(self):
        importlib.reload(_email_svc_mod)

    def test_send_followup_reminder_not_configured(self):
        with patch.object(_email_svc_mod, "is_email_configured", return_value=False):
            success, msg = _email_svc_mod.send_followup_reminder(
                "test@test.com", "John", "ABC Co", "LED Light", 7, "Share case study"
            )
            self.assertFalse(success)
            self.assertIn("not configured", msg.lower())

    def test_send_ai_generated_email_not_configured(self):
        with patch.object(_email_svc_mod, "is_email_configured", return_value=False):
            success, msg = _email_svc_mod.send_ai_generated_email("to@test.com", "Subject", "Body")
            self.assertFalse(success)

    def test_send_ai_generated_email_invalid_port(self):
        with patch.object(_email_svc_mod, "is_email_configured", return_value=True), \
             patch.object(_email_svc_mod, "get_secret", side_effect=lambda k: {
                 "SMTP_HOST": "smtp.test.com", "SMTP_PORT": "invalid",
                 "SMTP_USER": "user", "SMTP_PASSWORD": "pass",
                 "SMTP_FROM_EMAIL": "from@test.com",
             }.get(k, "")):
            success, msg = _email_svc_mod.send_ai_generated_email("to@test.com", "Subject", "Body")
            self.assertFalse(success)
            self.assertIn("SMTP_PORT", msg)

    def test_send_followup_reminder_calls_send_email(self):
        with patch.object(_email_svc_mod, "is_email_configured", return_value=True), \
             patch.object(_email_svc_mod, "send_email", return_value=(True, "sent")) as mock_send:
            _email_svc_mod.send_followup_reminder(
                "sales@test.com", "Mike", "ABC Trading", "LED Light", 7, "Share new samples"
            )
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            self.assertEqual(args[0], "sales@test.com")
            self.assertIn("Mike", args[1])
            self.assertIn("LED Light", args[2])


# ---------------------------------------------------------------------------
# Workflow reminder extension tests
# ---------------------------------------------------------------------------
import utils.workflow as _wf_mod


class TestWorkflowReminders(unittest.TestCase):

    def setUp(self):
        importlib.reload(_wf_mod)

    def test_send_due_reminders_email_not_configured(self):
        with patch("utils.email_service.is_email_configured", return_value=False), \
             patch.object(_wf_mod, "get_due_workflows", return_value=[]):
            sent, failed = _wf_mod.send_due_reminders("test@test.com")
            self.assertEqual(sent, 0)
            self.assertEqual(failed, 0)

    def test_send_due_reminders_no_due_items(self):
        with patch("utils.email_service.is_email_configured", return_value=True), \
             patch.object(_wf_mod, "get_due_workflows", return_value=[]):
            sent, failed = _wf_mod.send_due_reminders("test@test.com")
            self.assertEqual(sent, 0)
            self.assertEqual(failed, 0)

    def test_send_due_reminders_sends_per_due_item(self):
        due_items = [
            {"customer": "John", "company": "ABC", "product": "LED",
             "_rule": {"hint": "Follow up"}, "_days_elapsed": 7},
            {"customer": "Mary", "company": "XYZ", "product": "Solar",
             "_rule": {"hint": "Resend samples"}, "_days_elapsed": 3},
        ]
        with patch("utils.email_service.is_email_configured", return_value=True), \
             patch.object(_wf_mod, "get_due_workflows", return_value=due_items), \
             patch("utils.email_service.send_followup_reminder", return_value=(True, "ok")) as mock:
            sent, failed = _wf_mod.send_due_reminders("sales@test.com")
            self.assertEqual(sent, 2)
            self.assertEqual(failed, 0)
            self.assertEqual(mock.call_count, 2)

    def test_send_due_reminders_counts_failures(self):
        due_items = [
            {"customer": "John", "company": "ABC", "product": "LED",
             "_rule": {"hint": "Follow up"}, "_days_elapsed": 7},
        ]
        with patch("utils.email_service.is_email_configured", return_value=True), \
             patch.object(_wf_mod, "get_due_workflows", return_value=due_items), \
             patch("utils.email_service.send_followup_reminder", return_value=(False, "error")):
            sent, failed = _wf_mod.send_due_reminders("sales@test.com")
            self.assertEqual(sent, 0)
            self.assertEqual(failed, 1)


if __name__ == "__main__":
    unittest.main()
