"""Home page navigation configuration."""
from __future__ import annotations

NavItem = tuple[str, str, str, str]

QUICK_ACCESS: list[NavItem] = [
    ("\U0001f680", "快速设置", "2分钟初始化资料", "pages/34_\U0001f680_快速设置.py"),
    ("\U0001f4e5", "入站邮件", "导入客户邮件", "pages/35_\U0001f4e5_入站邮件.py"),
    ("\U0001f4e7", "开发信", "AI高转化冷邮件", "pages/