"""Home page navigation configuration."""
from __future__ import annotations

NavItem = tuple[str, str, str, str]

QUICK_ACCESS: list[NavItem] = [
    ("🚀", "快速设置", "2分钟初始化资料", "pages/34_🚀_快速设置.py"),
    ("📥", "入站邮件", "导入客户邮件", "pages/35_📥_入站邮件.py"),
    ("📧", "开发信", "AI高转化冷邮件", "pages/1_📧_开发信.py"),
    ("📩", "询盘回复", "逐条回答+报价", "pages/2_📩_询盘回复.py"),
    ("📄", "报价单", "多SKU专业PDF