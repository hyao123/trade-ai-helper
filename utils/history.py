"""
utils/history.py
----------------
生成历史记录管理。

History is kept in Streamlit session_state for responsive rendering, and is
persisted through the configured DatabaseBackend:
- logged-in users: per-user history collection
- admin/anonymous bypass mode: shared history collection
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.logger import get_logger
from utils.repositories import (
    load_shared_history,
    load_user_history,
    save_shared_history,
    save_user_history,
)
from utils.storage import get_storage_scope

logger = get_logger("history")

_HISTORY_LIMIT = 50
_STATE_KEY = "generation_history"
_LOADED_KEY = "_history_loaded_from_backend"
_SCOPE_KEY = "_history_backend_scope"


def _get_current_username() -> str | None:
    """Get current logged-in username, or None for shared/admin mode."""
    user = st.session_state.get("current_user")
    if user and user.get("username") and user["username"] != "admin":
        return user["username"]
    return None


def _history_state_key(username: str | None = None) -> str:
    return f"{_STATE_KEY}_{username}" if username else _STATE_KEY


def _history_loaded_key(username: str | None = None) -> str:
    return f"{_LOADED_KEY}_{username}" if username else _LOADED_KEY


def _history_scope_key(username: str | None = None) -> str:
    return f"{_SCOPE_KEY}_{username}" if username else _SCOPE_KEY


def _scope(username: str | None = None) -> str:
    owner_scope = f"user:{username}" if username else "shared"
    return f"{owner_scope}|storage:{get_storage_scope()}"


def _load_persisted_history(username: str | None) -> list[dict]:
    return load_user_history(username) if username else load_shared_history()


def _save_persisted_history(username: str | None, history: list[dict]) -> None:
    if username:
        save_user_history(username, history)
    else:
        save_shared_history(history)


def _get_history(username: str | None = None) -> list[dict]:
    """Get the active history list for a specific user or shared mode."""
    if username is None:
        username = _get_current_username()

    state_key = _history_state_key(username)
    loaded_key = _history_loaded_key(username)
    scope_key = _history_scope_key(username)
    scope = _scope(username)

    if (
        state_key not in st.session_state
        or not st.session_state.get(loaded_key)
        or st.session_state.get(scope_key) != scope
    ):
        st.session_state[state_key] = _load_persisted_history(username)
        st.session_state[loaded_key] = True
        st.session_state[scope_key] = scope

    return st.session_state[state_key]


def _persist_history(username: str | None = None) -> None:
    """Save current history to the configured backend."""
    if username is None:
        username = _get_current_username()
    state_key = _history_state_key(username)
    history = st.session_state.get(state_key, [])
    _save_persisted_history(username, history)


def import_history(data: list) -> None:
    """Bulk-import history data, replacing current state and persisting to backend."""
    username = _get_current_username()
    st.session_state[_history_state_key(username)] = data
    st.session_state[_history_loaded_key(username)] = True
    st.session_state[_history_scope_key(username)] = _scope(username)
    _persist_history(username)
    logger.info("History imported: %d records", len(data))


def _dedupe_history(entries: list[dict]) -> list[dict]:
    """Dedupe history entries while preserving order."""
    seen: set[tuple] = set()
    result: list[dict] = []
    for item in entries:
        key = (
            item.get("timestamp", ""),
            item.get("feature", ""),
            item.get("title", ""),
            item.get("content", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def migrate_session_history_to_user(username: str) -> None:
    """
    Merge shared in-session history into the user's persisted history.

    This is useful immediately after login/registration when a visitor may have
    generated content before authenticating. It keeps existing user history,
    prepends the most recent shared session entries, and caps the result.
    """
    if not username or username == "admin":
        return

    shared_key = _history_state_key(None)
    transient_history = st.session_state.get(shared_key, [])
    if not transient_history:
        return

    user_history = _get_history(username)
    merged = _dedupe_history(list(transient_history) + list(user_history))[:_HISTORY_LIMIT]
    st.session_state[_history_state_key(username)] = merged
    st.session_state[_history_loaded_key(username)] = True
    st.session_state[_history_scope_key(username)] = _scope(username)
    _persist_history(username)
    logger.info("Migrated %d transient history records to user=%s", len(transient_history), username)


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
    username = _get_current_username()
    history = _get_history(username)
    history.insert(0, {
        "feature": feature,
        "title": title,
        "content": content,
        "params": params or {},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    logger.debug("Added history: feature=%s, title=%s, user=%s", feature, title, username or "shared")
    # 最多保留 50 条
    if len(history) > _HISTORY_LIMIT:
        logger.warning("History cap reached, truncating to %d", _HISTORY_LIMIT)
        history[:] = history[:_HISTORY_LIMIT]
    _persist_history(username)


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
    st.session_state[_history_state_key(username)] = []
    st.session_state[_history_loaded_key(username)] = True
    st.session_state[_history_scope_key(username)] = _scope(username)
    _persist_history(username)
    logger.info("History cleared for user=%s", username or "shared")


def get_history_count() -> int:
    """返回总历史记录数。"""
    return len(_get_history())
