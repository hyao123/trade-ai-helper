"""
utils/history.py
----------------
生成历史记录管理。
所有 AI 生成结果自动保存到 session_state，供用户回看、复用、对比。
Data persists to disk via JSON storage layer.
Supports per-user isolation when a user is logged in.
"""

from __future__ import annotations

from datetime import datetime
import streamlit as st

from utils.storage import load_json, save_json, load_user_json, save_user_json
from utils.logger import get_logger

logger = get_logger("history")

_FILENAME = "history.json"


def _get_current_username() -> str | None:
    """Get current logged-in username, or None for shared/admin mode."""
    user = st.session_state.get("current_user")
    if user and user.get("username") and user["username"] != "admin":
        return user["username"]
    return None


def _get_history() -> list[dict]:
    """获取历史记录列表。"""
    username = _get_current_username()
    if username:
        flag_key = f"_history_loaded_from_disk_{username}"
        state_key = f"generation_history_{username}"
        if state_key not in st.session_state or not st.session_state.get(flag_key):
            st.session_state[state_key] = load_user_json(username, _FILENAME, default=[])
            st.session_state[flag_key] = True
        return st.session_state[state_key]
    else:
        if "generation_history" not in st.session_state or not st.session_state.get("_history_loaded_from_disk"):
            st.session_state["generation_history"] = load_json(_FILENAME, default=[])
            st.session_state["_history_loaded_from_disk"] = True
        return st.session_state["generation_history"]


def _persist_history() -> None:
    """Save current history to disk."""
    username = _get_current_username()
    if username:
        state_key = f"generation_history_{username}"
        save_user_json(username, _FILENAME, st.session_state.get(state_key, []))
    else:
        save_json(_FILENAME, st.session_state.get("generation_history", []))


def import_history(data: list) -> None:
    """Bulk-import history data, replacing current state and persisting to disk."""
    username = _get_current_username()
    if username:
        state_key = f"generation_history_{username}"
        flag_key = f"_history_loaded_from_disk_{username}"
        st.session_state[state_key] = data
        st.session_state[flag_key] = True
        save_user_json(username, _FILENAME, data)
    else:
        st.session_state["generation_history"] = data
        st.session_state["_history_loaded_from_disk"] = True
        save_json(_FILENAME, data)
    logger.info("History imported: %d records", len(data))


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
    logger.debug("Added history: feature=%s, title=%s", feature, title)
    # 最多保留 50 条
    if len(history) > 50:
        logger.warning("History cap reached, truncating to 50")
        username = _get_current_username()
        if username:
            state_key = f"generation_history_{username}"
            st.session_state[state_key] = history[:50]
        else:
            st.session_state["generation_history"] = history[:50]
    _persist_history()


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
    username = _get_current_username()
    if username:
        state_key = f"generation_history_{username}"
        st.session_state[state_key] = []
        save_user_json(username, _FILENAME, [])
    else:
        st.session_state["generation_history"] = []
        save_json(_FILENAME, [])
    logger.info("History cleared")


def get_history_count() -> int:
    """返回总历史记录数。"""
    return len(_get_history())
