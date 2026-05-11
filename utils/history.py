"""
utils/history.py
----------------
生成历史记录管理。
所有 AI 生成结果自动保存到 session_state，供用户回看、复用、对比。
"""

from __future__ import annotations

from datetime import datetime
import streamlit as st


def _get_history() -> list[dict]:
    """获取历史记录列表。"""
    if "generation_history" not in st.session_state:
        st.session_state["generation_history"] = []
    return st.session_state["generation_history"]


def add_to_history(
    feature: str,
    title: str,
    content: str,
    params: dict | None = None,
) -> None:
    """
    将一次生成结果添加到历史记录。

    feature: 功能名称（如 "开发信", "询盘回复", "产品上架"）
    title: 显示标题（如产品名或客户名）
    content: 生成的完整文本
    params: 生成时的参数（可选，用于"重生成"）
    """
    history = _get_history()
    history.insert(0, {
        "feature": feature,
        "title": title,
        "content": content,
        "params": params or {},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    # 最多保留 50 条
    if len(history) > 50:
        st.session_state["generation_history"] = history[:50]


def get_history(feature: str | None = None, limit: int = 20) -> list[dict]:
    """
    获取历史记录。
    feature: 可选筛选（如 "开发信"），None 表示全部
    limit: 最多返回条数
    """
    history = _get_history()
    if feature:
        history = [h for h in history if h["feature"] == feature]
    return history[:limit]


def clear_history() -> None:
    """清空所有历史记录。"""
    st.session_state["generation_history"] = []


def get_history_count() -> int:
    """返回总历史记录数。"""
    return len(_get_history())
