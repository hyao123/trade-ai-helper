"""
tests/test_tier2.py
-------------------
Unit tests for Tier 2 features:
  - container_calc
  - analytics
  - ab_testing (non-streamlit parts)
  - config/prompts (smart_quote, ab_variants)
"""
from __future__ import annotations

import sys
import types
import unittest

# ---------------------------------------------------------------------------
# Stub out streamlit before importing modules that import it
# ---------------------------------------------------------------------------
_st = types.ModuleType("streamlit")
_st.session_state = {}


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)


_st.session_state = _FakeSessionState()
sys.modules.setdefault("streamlit", _st)


# ---------------------------------------------------------------------------
# container_calc tests
# ---------------------------------------------------------------------------
from utils.container_calc import (
    CONTAINER_SPECS,
    CartonSpec,
    calculate_all_containers,
    calculate_loading,
    recommend_container,
)


class TestContainerCalc(unittest.TestCase):

    def _make_carton(self, length=600, w=400, h=350, kg=15.0, qty=24):
        return CartonSpec(length_mm=length, width_mm=w, height_mm=h,
                          gross_weight_kg=kg, quantity_per_carton=qty)

    def test_40hq_gives_most_cartons(self):
        carton = self._make_carton()
        results = calculate_all_containers(carton)
        self.assertTrue(len(results) > 0)
        # Results are sorted descending by total_cartons
        self.assertGreaterEqual(results[0].total_cartons, results[-1].total_cartons)
        # 40HQ should be first (most capacity)
        self.assertEqual(results[0].container_type, "40HQ")

    def test_volume_utilisation_is_between_0_and_100(self):
        carton = self._make_carton()
        for ct in CONTAINER_SPECS:
            result = calculate_loading(carton, ct)
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result.volume_utilization_pct, 0)
            self.assertLessEqual(result.volume_utilization_pct, 100)

    def test_weight_not_exceeded(self):
        carton = self._make_carton(kg=25.0)
        for ct in CONTAINER_SPECS:
            result = calculate_loading(carton, ct)
            if result:
                self.assertLessEqual(
                    result.total_weight_kg,
                    CONTAINER_SPECS[ct]["max_payload_kg"] + 0.01,
                )

    def test_total_units_equals_cartons_times_qty(self):
        carton = self._make_carton(qty=50)
        result = calculate_loading(carton, "40HQ")
        self.assertIsNotNone(result)
        self.assertEqual(result.total_units, result.total_cartons * 50)

    def test_oversized_carton_returns_none(self):
        # Carton bigger than any container
        carton = CartonSpec(length_mm=10000, width_mm=5000, height_mm=5000,
                            gross_weight_kg=1.0)
        result = calculate_loading(carton, "40HQ")
        self.assertIsNone(result)

    def test_recommend_container_returns_valid_type(self):
        carton = self._make_carton()
        rec = recommend_container(carton, target_quantity=500)
        self.assertIn(rec["recommended"], list(CONTAINER_SPECS.keys()))
        self.assertGreater(rec["containers_needed"], 0)

    def test_recommend_container_sufficient_for_target(self):
        carton = self._make_carton()
        target = 500
        rec = recommend_container(carton, target_quantity=target)
        best_option = next(
            o for o in rec["all_options"]
            if o["container_type"] == rec["recommended"]
        )
        self.assertGreaterEqual(
            best_option["total_capacity"],
            target,
        )

    def test_non_stackable_carton_single_layer(self):
        carton = CartonSpec(length_mm=600, width_mm=400, height_mm=350,
                            gross_weight_kg=10.0, stackable=False)
        result = calculate_loading(carton, "40HQ")
        self.assertIsNotNone(result)
        self.assertEqual(result.layers, 1)

    def test_all_containers_sorted_descending(self):
        carton = self._make_carton()
        results = calculate_all_containers(carton)
        counts = [r.total_cartons for r in results]
        self.assertEqual(counts, sorted(counts, reverse=True))


# ---------------------------------------------------------------------------
# analytics tests
# ---------------------------------------------------------------------------
from utils.analytics import (
    compute_activity_metrics,
    compute_funnel,
    compute_monthly_activity,
    compute_segmentation,
    generate_full_report,
)


class TestAnalytics(unittest.TestCase):

    def _sample_customers(self):
        return [
            {"company": "A", "stage": "新客户",  "country": "USA",    "industry": "Electronics", "last_contact": "2026-05-10"},
            {"company": "B", "stage": "已报价",  "country": "UK",     "industry": "Furniture",   "last_contact": "2026-05-01"},
            {"company": "C", "stage": "已下单",  "country": "USA",    "industry": "Electronics", "last_contact": "2026-04-15"},
            {"company": "D", "stage": "长期合作", "country": "Germany","industry": "Automotive",  "last_contact": "2026-03-01"},
            {"company": "E", "stage": "新客户",  "country": "France", "industry": "Fashion",     "last_contact": ""},
        ]

    def test_total_customers_count(self):
        report = generate_full_report(self._sample_customers())
        self.assertEqual(report.total_customers, 5)

    def test_conversion_rate_correct(self):
        # 已下单 + 长期合作 = 2 out of 5 = 40%
        report = generate_full_report(self._sample_customers())
        self.assertAlmostEqual(report.conversion_rate, 40.0, places=1)

    def test_empty_customers_report(self):
        report = generate_full_report([])
        self.assertEqual(report.total_customers, 0)
        self.assertEqual(report.conversion_rate, 0.0)
        self.assertEqual(report.funnel, [])

    def test_funnel_includes_all_present_stages(self):
        funnel = compute_funnel(self._sample_customers())
        stages_in_funnel = [f.stage for f in funnel]
        self.assertIn("新客户", stages_in_funnel)
        self.assertIn("已报价", stages_in_funnel)
        self.assertIn("已下单", stages_in_funnel)

    def test_funnel_percentages_sum_to_100(self):
        funnel = compute_funnel(self._sample_customers())
        total_pct = sum(f.percentage for f in funnel)
        self.assertAlmostEqual(total_pct, 100.0, delta=1.0)

    def test_segmentation_top_countries(self):
        seg = compute_segmentation(self._sample_customers())
        # USA appears twice, should be first
        top_countries = seg["top_countries"]
        self.assertGreater(len(top_countries), 0)
        self.assertEqual(top_countries[0][0], "USA")
        self.assertEqual(top_countries[0][1], 2)

    def test_activity_metrics_active_count(self):
        activity = compute_activity_metrics(self._sample_customers())
        # last_contact in 2026-05 should be within 30 days of today (2026-05-14)
        self.assertGreaterEqual(activity["active_count"], 2)
        self.assertGreaterEqual(activity["never_contacted"], 1)

    def test_monthly_activity_returns_6_entries(self):
        monthly = compute_monthly_activity(self._sample_customers())
        self.assertEqual(len(monthly), 6)

    def test_stage_distribution_counts(self):
        report = generate_full_report(self._sample_customers())
        self.assertEqual(report.stage_distribution.get("新客户", 0), 2)
        self.assertEqual(report.stage_distribution.get("已下单", 0), 1)


# ---------------------------------------------------------------------------
# ab_testing tests (non-streamlit logic only)
# ---------------------------------------------------------------------------
from utils.ab_testing import (
    ABTest,
    ABVariant,
    compute_confidence,
    simulate_results,
)


class TestABTesting(unittest.TestCase):

    def _make_variant(self, sends=100, opens=30, clicks=10, replies=5, label="A"):
        return ABVariant(
            variant_id=label.lower(),
            label=label,
            content="Test email content with a question?",
            subject_line="Test Subject",
            sends=sends, opens=opens, clicks=clicks, replies=replies,
        )

    def test_open_rate_calculation(self):
        v = self._make_variant(sends=100, opens=25)
        self.assertAlmostEqual(v.open_rate, 25.0)

    def test_click_rate_calculation(self):
        v = self._make_variant(sends=200, clicks=20)
        self.assertAlmostEqual(v.click_rate, 10.0)

    def test_reply_rate_calculation(self):
        v = self._make_variant(sends=100, replies=8)
        self.assertAlmostEqual(v.reply_rate, 8.0)

    def test_zero_sends_returns_zero_rate(self):
        v = self._make_variant(sends=0, opens=0, clicks=0, replies=0)
        self.assertEqual(v.open_rate, 0.0)
        self.assertEqual(v.click_rate, 0.0)
        self.assertEqual(v.reply_rate, 0.0)

    def test_variant_serialization_roundtrip(self):
        v = self._make_variant()
        d = v.to_dict()
        v2 = ABVariant.from_dict(d)
        self.assertEqual(v.sends, v2.sends)
        self.assertEqual(v.label, v2.label)
        self.assertEqual(v.content, v2.content)

    def test_ab_test_serialization_roundtrip(self):
        variants = [self._make_variant(label=lbl) for lbl in ["A", "B"]]
        test = ABTest(
            test_id="t1", name="Test 1", product="LED Light",
            created_at="2026-05-14 10:00", status="draft", variants=variants,
        )
        d = test.to_dict()
        test2 = ABTest.from_dict(d)
        self.assertEqual(test2.test_id, "t1")
        self.assertEqual(len(test2.variants), 2)

    def test_compute_confidence_high_difference(self):
        va = self._make_variant(sends=1000, opens=450)  # 45%
        vb = self._make_variant(sends=1000, opens=150)  # 15%
        conf = compute_confidence(va, vb)
        self.assertGreaterEqual(conf, 95.0)

    def test_compute_confidence_low_difference(self):
        va = self._make_variant(sends=100, opens=30)  # 30%
        vb = self._make_variant(sends=100, opens=29)  # 29%
        conf = compute_confidence(va, vb)
        self.assertLess(conf, 80.0)

    def test_compute_confidence_no_sends(self):
        va = self._make_variant(sends=0)
        vb = self._make_variant(sends=0)
        self.assertEqual(compute_confidence(va, vb), 0.0)

    def test_simulate_results_sets_sends(self):
        variants = [self._make_variant(sends=0, opens=0, label=lbl) for lbl in ["A", "B", "C"]]
        test = ABTest(
            test_id="sim1", name="Sim Test", product="Product",
            created_at="2026-05-14", status="draft", variants=variants,
        )
        # Call simulate without persistence (mock save)
        with unittest.mock.patch("utils.ab_testing.update_ab_test"):
            simulated = simulate_results(test, total_sends=100)
        for v in simulated.variants:
            self.assertEqual(v.sends, 100)
            self.assertGreater(v.opens, 0)
        self.assertEqual(simulated.status, "completed")
        self.assertIsNotNone(simulated.winner)

    def test_simulate_winner_is_highest_reply_rate(self):
        variants = [
            ABVariant("va", "A", "email?", sends=0, opens=0, replies=0),
            ABVariant("vb", "B", "email?", sends=0, opens=0, replies=0),
        ]
        test = ABTest("t2", "Test", "P", "2026", "draft", variants)
        with unittest.mock.patch("utils.ab_testing.update_ab_test"):
            simulated = simulate_results(test, total_sends=200)
        # Winner should be variant with max reply_rate
        best = max(simulated.variants, key=lambda v: v.reply_rate)
        self.assertEqual(simulated.winner, best.variant_id)


# ---------------------------------------------------------------------------
# prompt builder tests
# ---------------------------------------------------------------------------
from config.prompts import build_ab_variant_prompt, build_smart_quote_prompt


class TestTier2Prompts(unittest.TestCase):

    def test_smart_quote_prompt_contains_product(self):
        prompt, system = build_smart_quote_prompt(
            "LED Strip 5050", "Europe", 500, "$2/pc", "Competitor at $5", "FOB"
        )
        self.assertIn("LED Strip 5050", prompt)
        self.assertIn("Europe", prompt)
        self.assertIn("500", prompt)
        self.assertIn("FOB", prompt)
        self.assertIn("$2/pc", prompt)
        self.assertIsNotNone(system)

    def test_smart_quote_prompt_no_optional_fields(self):
        prompt, system = build_smart_quote_prompt("Widget", "USA", 1000)
        self.assertIn("Widget", prompt)
        self.assertIn("USA", prompt)
        self.assertNotIn("Production/Procurement Cost", prompt)
        self.assertNotIn("Competitor Reference", prompt)

    def test_ab_variant_prompt_subject_line_focus(self):
        prompt, system = build_ab_variant_prompt("LED Light", "Wholesalers", 3, "subject_line")
        self.assertIn("LED Light", prompt)
        self.assertIn("subject line", prompt.lower())
        self.assertIsNotNone(system)

    def test_ab_variant_prompt_full_email_focus(self):
        prompt, system = build_ab_variant_prompt("LED Light", "Wholesalers", 3, "full_email")
        self.assertIn("LED Light", prompt)
        # Full email focus mentions email body
        self.assertIn("email", prompt.lower())

    def test_ab_variant_prompt_num_variants(self):
        for n in [2, 3, 4, 5]:
            prompt, _ = build_ab_variant_prompt("P", "C", n, "subject_line")
            self.assertIn(str(n), prompt)

    def test_smart_quote_prompt_contains_price_range_section(self):
        prompt, _ = build_smart_quote_prompt("Chair", "UK", 2000)
        self.assertIn("Recommended Price Range", prompt)
        self.assertIn("Volume Discount Schedule", prompt)

    def test_smart_quote_sanitizes_oversized_input(self):
        # Very long product name should be truncated by sanitize_prompt_param
        long_product = "A" * 2000
        prompt, _ = build_smart_quote_prompt(long_product, "USA", 100)
        # Prompt must be generated (not empty)
        self.assertGreater(len(prompt), 100)
        # The raw 2000-char string should not appear verbatim (sanitized/truncated)
        self.assertNotIn("A" * 2000, prompt)


import unittest.mock

if __name__ == "__main__":
    unittest.main()
