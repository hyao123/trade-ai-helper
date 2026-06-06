"""Home page navigation configuration.

Keep large Streamlit rendering code separate from frequently edited navigation
items. New product pages should usually be added here instead of editing
``app.py`` directly.
"""
from __future__ import annotations

NavItem = tuple[str, str, str, str]

QUICK_ACCESS: list[NavItem] = [
    ("🚀", "快速设置", "2分钟初始化资料", "pages/34_🚀