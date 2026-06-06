"""Small home navigation extensions.

Keep newly added homepage entries here so app.py does not need frequent edits.
"""
from __future__ import annotations

NavItem = tuple[str, str, str, str]

EXTRA_QUICK_ACCESS: list[NavItem] = [
    ("📥", "入站邮件", "导入客户邮件", "pages/35_📥_入站邮件.py"),
]

EXTRA_MAIL_NAV: list[NavItem] = [
    ("📥", "入站邮件", "导入客户邮件生成回复草稿", "pages/35_📥_入站邮件.py