"""
tests/test_workbench_navigation.py
----------------------------------
Unit tests for ROI-driven navigation sections and page paths.
"""
from __future__ import annotations

import pathlib
import unittest

from app import NAV_SECTIONS, QUICK_ACCESS


class TestWorkbenchNavigation(unittest.TestCase):
    """Verify workbench navigation integrity and target page existence."""

    def test_quick_access_paths_exist(self):
        for icon, title, desc, page_path in QUICK_ACCESS:
            p = pathlib.Path(page_path)
            self.assertTrue(p.exists(), f"Quick access page missing: {page_path}")

    def test_nav_sections_categories_cover_4_phases(self):
        section_titles = list(NAV_SECTIONS.keys())
        self.assertTrue(any("获客" in t or "寻源" in t for t in section_titles))
        self.assertTrue(any("转化" in t or "谈判" in t for t in section_titles))
        self.assertTrue(any("履约" in t or "单证" in t for t in section_titles))
        self.assertTrue(any("复购" in t or "客户" in t for t in section_titles))

    def test_all_nav_section_pages_exist(self):
        for section, items in NAV_SECTIONS.items():
            for icon, title, desc, page_path in items:
                p = pathlib.Path(page_path)
                self.assertTrue(p.exists(), f"Nav page missing in {section}: {page_path}")


if __name__ == "__main__":
    unittest.main()
