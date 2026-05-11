"""
utils/secrets.py
----------------
统一读取配置的入口，兼容三种来源（优先级从高到低）：
  1. Streamlit Cloud Secrets（st.secrets）
  2. 本地 .env 文件（python-dotenv）
  3. 系统环境变量

用法：
    from utils.secrets import get_secret
    api_key = get_secret("KIMI_API_KEY")
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str, default: str = "") -> str:
    """
    按优先级读取配置：
    1. st.secrets（Streamlit Cloud 部署时）
    2. os.environ（.env 或系统环境变量）
    3. default
    """
    # 1. 尝试从 Streamlit Secrets 读取
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val is not None:
            return str(val)
    except Exception:
        pass

    # 2. 从环境变量读取
    val = os.getenv(key, "")
    if val:
        return val

    return default
