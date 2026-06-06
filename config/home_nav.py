"""Small home navigation extensions."""
from __future__ import annotations

NavItem = tuple[str, str, str, str]

INBOUND_PAGE = "pages/35_\U0001f4e5_\u5165\u7ad9\u90ae\u4ef6.py"

EXTRA_QUICK_ACCESS: list[NavItem] = [
    ("\U0001f4e5", "Inbound Email", "Import customer email", INBOUND_PAGE),
]

EXTRA_MAIL_NAV: list[NavItem] = [
    ("\U0001f4e5", "Inbound Email", "Import email and draft reply", INBOUND_PAGE),