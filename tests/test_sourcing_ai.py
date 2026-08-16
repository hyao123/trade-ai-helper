"""
tests/test_sourcing_ai.py
-------------------------
Unit tests for utils/sourcing_ai.py:
- Industrial cluster & chemical hub matching
- Export margin & tax rebate calculation
- Multi-channel search query generation (1688, Google, LinkedIn, CAS)
- Sourcing RFQ & chemical customization agreement generation
- Dangerous goods class lookup
"""
from __future__ import annotations

import unittest

from utils.sourcing_ai import (
    DANGEROUS_GOODS_CLASSES,
    INDUSTRIAL_CLUSTERS,
    build_customization_agreement_text,
    build_sourcing_rfq_prompt,
    calculate_export_profit,
    generate_sourcing_search_queries,
    match_industrial_clusters,
)


class TestSourcingAI(unittest.TestCase):
    """Test suite for sourcing and chemical customization module."""

    def test_cluster_database_not_empty(self):
        self.assertGreater(len(INDUSTRIAL_CLUSTERS), 5)
        chemical_clusters = [c for c in INDUSTRIAL_CLUSTERS if c.get("is_chemical")]
        self.assertGreater(len(chemical_clusters), 2)

    def test_match_industrial_clusters_chemical(self):
        results = match_industrial_clusters("医药中间体", is_chemical_only=True)
        self.assertGreater(len(results), 0)
        self.assertTrue(any("江苏" in r["region"] or "山东" in r["region"] for r in results))

    def test_match_industrial_clusters_general(self):
        results = match_industrial_clusters("LED")
        self.assertGreater(len(results), 0)
        # Should match Shenzhen or Ningbo/Zhongshan
        matched_regions = [r["region"] for r in results]
        self.assertTrue(any("深圳" in reg or "宁波" in reg or "中山" in reg for reg in matched_regions))

    def test_match_industrial_clusters_fallback(self):
        # Empty query should return full list
        all_clusters = match_industrial_clusters("")
        self.assertEqual(len(all_clusters), len(INDUSTRIAL_CLUSTERS))

    def test_calculate_export_profit_basic(self):
        # 100 CNY purchase price, 13% VAT, 13% rebate
        res = calculate_export_profit(
            purchase_price_cny=113.0,
            vat_rate=0.13,
            rebate_rate=0.13,
            domestic_freight_cny=2.0,
            packaging_cny=1.0,
            fob_price_usd=20.0,
            exchange_rate=7.2,
            qty=100.0,
        )
        # Tax free base = 113 / 1.13 = 100
        self.assertEqual(res["tax_free_base"], 100.0)
        # Rebate amount = 100 * 0.13 = 13
        self.assertEqual(res["tax_rebate_amount"], 13.0)
        # Net purchase cost = 113 - 13 = 100
        self.assertEqual(res["net_purchase_cost"], 100.0)
        # Domestic cost = 100 + 2 + 1 = 103
        self.assertEqual(res["unit_domestic_cost"], 103.0)
        # Total domestic cost for 100 units = 10300
        self.assertEqual(res["total_domestic_cost"], 10300.0)
        # Breakeven FOB = 103 / 7.2 = 14.31
        self.assertAlmostEqual(res["breakeven_fob_usd"], 14.31, places=2)
        # Total profit should be positive
        self.assertGreater(res["total_profit_cny"], 0.0)
        self.assertGreater(res["margin_pct"], 0.0)

    def test_calculate_export_profit_zero_or_negative_inputs(self):
        # Robustness against 0 qty or negative values
        res = calculate_export_profit(
            purchase_price_cny=0.0,
            qty=0.0,
            exchange_rate=0.0,
        )
        self.assertEqual(res["qty"], 1.0)
        self.assertEqual(res["exchange_rate"], 7.20)
        self.assertEqual(res["net_purchase_cost"], 0.0)

    def test_generate_sourcing_search_queries_with_cas(self):
        queries = generate_sourcing_search_queries(
            product_name="Cyclohexanone",
            cas_number="108-94-1",
            target_country="DE",
            application_industry="Solvent / Coating",
        )
        self.assertIn("domestic_sourcing", queries)
        self.assertIn("google_xray", queries)
        self.assertIn("linkedin_buyers", queries)

        # Check CAS presence in generated queries
        google_qs = [item["query"] for item in queries["google_xray"]]
        self.assertTrue(any("108-94-1" in q for q in google_qs))

    def test_build_sourcing_rfq_prompt(self):
        prompt = build_sourcing_rfq_prompt(
            product_name="Polyquaternium-10",
            cas_number="68610-92-4",
            purity_spec="Viscosity 300-500 cps",
            quantity_target="5 Metric Tons",
            packaging_requirement="25kg Paper Drum with PE liner",
            target_price_cny="45000 CNY/Ton",
            is_chemical=True,
        )
        self.assertIn("68610-92-4", prompt)
        self.assertIn("COA", prompt)
        self.assertIn("SDS/MSDS", prompt)
        self.assertIn("45000", prompt)

    def test_build_customization_agreement_text(self):
        agreement = build_customization_agreement_text(
            buyer_company="ABC International Trade Ltd",
            supplier_company="XYZ Chemical Material Co., Ltd",
            product_name="Industrial Grade Solvent",
            specs="Purity >= 99.5%, Moisture <= 0.05%",
            tolerance_terms="Moisture strictly below 0.05%",
            is_chemical=True,
        )
        self.assertIn("ABC International Trade Ltd", agreement)
        self.assertIn("XYZ Chemical Material Co., Ltd", agreement)
        self.assertIn("COA 分析报告", agreement)
        self.assertIn("UN 认证危险货物包装", agreement)

    def test_dangerous_goods_classes(self):
        self.assertIn("Class 3", DANGEROUS_GOODS_CLASSES)
        self.assertIn("Class 8", DANGEROUS_GOODS_CLASSES)
        self.assertIn("Non-DG", DANGEROUS_GOODS_CLASSES)


if __name__ == "__main__":
    unittest.main()
