"""
utils/secrets.py
----------------
统一读取配置的入口，兼容三种来源（优先级从高到低）：
  1. Streamlit Cloud Secrets（st.secrets）
  2. 本地 .env 文件（python-dotenv）
  3. 系统环境变量

用法：
    from utils.secrets import get_secret
    api_key = get_secret("NVIDIA_API_KEY")
"""

from __future__ import annotations

import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger(__name__)
_EPHEMERAL_ADMIN_PASSWORD = secrets.token_urlsafe(32)
_FALSE_VALUES = {"0", "false", "no", "off"}


def _streamlit_secret(key: str) -> str | None:
    """Read one Streamlit secret without falling back to environment variables."""
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val is not None:
            return str(val)
    except (ImportError, AttributeError, FileNotFoundError):
        # ImportError: streamlit 未安装（测试环境）
        # AttributeError: st.secrets 不可用（非 Streamlit 运行时）
        # FileNotFoundError: secrets.toml 不存在
        pass
    except Exception as e:
        # 记录意外错误但不中断
        _logger.warning(f"Unexpected error reading st.secrets[{key!r}]: {e}")
    return None


def _auth_required_default() -> bool:
    """Return whether authentication should be required when APP_PASSWORD is unset."""
    raw = _streamlit_secret("AUTH_REQUIRED")
    if raw is None:
        raw = os.getenv("AUTH_REQUIRED", "true")
    return raw.strip().lower() not in _FALSE_VALUES


def get_secret(key: str, default: str = "") -> str:
    """
    按优先级读取配置：
    1. st.secrets（Streamlit Cloud 部署时）
    2. os.environ（.env 或系统环境变量）
    3. default

    APP_PASSWORD special case:
    - When explicitly configured, it acts as the admin fallback password.
    - When not configured and AUTH_REQUIRED is not false, return an ephemeral
      unguessable password so the login/register UI is still shown and public
      deployments support self-service registration by default.
    - Set AUTH_REQUIRED=false for local/demo deployments that should bypass auth.
    """
    val = _streamlit_secret(key)
    if val is not None:
        return val

    # 2. 从环境变量读取
    val = os.getenv(key, "")
    if val:
        return val

    if key == "APP_PASSWORD" and _auth_required_default():
        return _EPHEMERAL_ADMIN_PASSWORD

    return default
