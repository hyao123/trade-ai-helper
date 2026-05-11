"""
utils/templates.py
------------------
模板保存/加载/删除系统。
数据持久化到 st.session_state（单 session 有效）。
未来可扩展到 JSON 文件或数据库。
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime


def _get_store() -> dict[str, list[dict]]:
    """获取模板存储（按功能分类）。"""
    if "templates" not in st.session_state:
        st.session_state["templates"] = {}
    return st.session_state["templates"]


def save_template(category: str, name: str, data: dict) -> None:
    """
    保存一个模板。
    category: 功能类别，如 "email", "inquiry", "listing"
    name: 模板名称
    data: 表单数据字典
    """
    store = _get_store()
    if category not in store:
        store[category] = []

    # 检查是否已存在同名模板，存在则覆盖
    store[category] = [t for t in store[category] if t["name"] != name]
    store[category].append({
        "name": name,
        "data": data,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })


def load_templates(category: str) -> list[dict]:
    """获取某分类下的所有模板列表。"""
    store = _get_store()
    return store.get(category, [])


def delete_template(category: str, name: str) -> None:
    """删除指定模板。"""
    store = _get_store()
    if category in store:
        store[category] = [t for t in store[category] if t["name"] != name]


def get_template_names(category: str) -> list[str]:
    """获取某分类下的模板名称列表。"""
    return [t["name"] for t in load_templates(category)]


def get_template_data(category: str, name: str) -> dict | None:
    """根据名称获取模板数据。"""
    for t in load_templates(category):
        if t["name"] == name:
            return t["data"]
    return None
