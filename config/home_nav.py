"""Small home navigation extensions.

Keep newly added homepage entries here so app.py does not need frequent edits.
"""
from __future__ import annotations

NavItem = tuple[str, str, str, str]

INBOUND_PAGE = "pages/35_\U0001f4e5_入站邮件.py"

EXTRA_QUICK_ACCESS: list[NavItem] = [
    ("\U0001f4e5", "入站邮件", "导入客户邮件", INBOUND_PAGE),
]

EXTRA_MAIL_NAV: list[NavItem