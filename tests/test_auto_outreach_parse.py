"""Tests for auto_outreach CSV/Excel prospect parsing.

Covers the header-case normalization fix: a CSV exported with capitalized
headers ("Email", "Company") must not silently drop every row.
"""
from __future__ import annotations

import io
import sys
import types

# Mock streamlit/dotenv so auto_outreach imports cleanly.
_stub = types.ModuleType("streamlit")
_stub.session_state = {}
sys.modules.setdefault("streamlit", _stub)
_dotenv = types.ModuleType("dotenv")
_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules.setdefault("dotenv", _dotenv)

from utils.auto_outreach import _parse_csv  # noqa: E402


def test_parse_csv_lowercases_capitalized_headers():
    content = (
        "Email,Company,Contact Name,Industry,Country\n"
        "john@acme.com,ACME,John,Electronics,US\n"
    ).encode("utf-8")
    rows, err = _parse_csv(content)
    assert err == ""
    assert len(rows) == 1
    row = rows[0]
    assert row.get("email") == "john@acme.com"
    assert row.get("company") == "ACME"
    assert row.get("contact_name") == "John"
    assert row.get("industry") == "Electronics"
    assert row.get("country") == "US"


def test_parse_csv_lowercase_headers_still_work():
    content = (
        "email,company,country\n"
        "jane@beta.com,Beta Corp,DE\n"
    ).encode("utf-8")
    rows, err = _parse_csv(content)
    assert err == ""
    assert rows[0]["email"] == "jane@beta.com"
    assert rows[0]["company"] == "Beta Corp"
    assert rows[0]["country"] == "DE"
