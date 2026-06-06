"""Small home navigation extensions."""
from __future__ import annotations

NavItem = tuple[str, str, str, str]

_INBOX = chr(0x1F4E5)
_INBOUND_ZH = "\u5165\u7ad9\u90ae\u4ef6"
INBOUND_PAGE = f"pages/35_{_INBOX}_{_INBOUND_ZH}.py"

EXTRA_QUICK_ACCESS: list[NavItem] = [
    (_INBOX, "Inbound Email", "Import customer email", INBOUND_PAGE),
]
