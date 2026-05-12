"""
utils/templates.py
------------------
模板保存/加载/删除系统。
数据持久化到 st.session_state + JSON 文件。
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.storage import load_json, save_json

_FILENAME = "templates.json"


def _get_store() -> dict[str, list[dict]]:
    """获取模板存储（按功能分类）。"""
    if "templates" not in st.session_state:
        st.session_state["templates"] = load_json(_FILENAME, default={})
        st.session_state["_templates_loaded_from_disk"] = True
    elif not st.session_state.get("_templates_loaded_from_disk"):
        disk_data = load_json(_FILENAME, default={})
        if disk_data and not st.session_state["templates"]:
            st.session_state["templates"] = disk_data
        st.session_state["_templates_loaded_from_disk"] = True
    return st.session_state["templates"]


def _persist_templates() -> None:
    """Save current templates to disk."""
    save_json(_FILENAME, st.session_state.get("templates", {}))


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
    _persist_templates()


def load_templates(category: str) -> list[dict]:
    """获取某分类下的所有模板列表。"""
    store = _get_store()
    return store.get(category, [])


def delete_template(category: str, name: str) -> None:
    """删除指定模板。"""
    store = _get_store()
    if category in store:
        store[category] = [t for t in store[category] if t["name"] != name]
    _persist_templates()


def get_template_names(category: str) -> list[str]:
    """获取某分类下的模板名称列表。"""
    return [t["name"] for t in load_templates(category)]


def get_template_data(category: str, name: str) -> dict | None:
    """根据名称获取模板数据。"""
    for t in load_templates(category):
        if t["name"] == name:
            return t["data"]
    return None
