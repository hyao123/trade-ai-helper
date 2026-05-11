"""
utils/ai_client.py
------------------
NVIDIA NIM API 调用层（OpenAI 兼容接口）。

- 使用 openai SDK（NVIDIA NIM 完全兼容 OpenAI 接口）
- call_llm()       非流式，返回 str
- stream_llm()     流式，返回 Generator[str]，供 st.write_stream() 消费
- Rate Limiting 基于内存 sliding-window（注：多进程/重启后计数重置）
- 所有 Prompt 模板从 config.prompts 导入

NVIDIA NIM API 文档：https://docs.api.nvidia.com/nim/docs/api-quickstart
"""

from __future__ import annotations

import os
import time
import types
from collections import defaultdict
from typing import Generator

from openai import OpenAI, AuthenticationError, RateLimitError, APIStatusError, APITimeoutError

from config.prompts import (
    build_email_prompt,
    build_inquiry_prompt,
    build_product_intro_prompt,
    build_followup_prompt,
)
from utils.secrets import get_secret

# ---------------------------------------------------------------------------
# 客户端单例
# ---------------------------------------------------------------------------
_API_KEY  = get_secret("NVIDIA_API_KEY")
_API_BASE = "https://integrate.api.nvidia.com/v1"
# 默认使用 meta/llama-3.3-70b-instruct，可通过环境变量覆盖
_MODEL    = get_secret("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """返回全局单例 OpenAI 客户端，避免每次调用新建连接池。"""
    global _client, _API_KEY
    # 若 API Key 在运行时变更（如从 Streamlit Secrets 延迟加载），重建客户端
    current_key = get_secret("NVIDIA_API_KEY")
    if _client is None or current_key != _API_KEY:
        _API_KEY = current_key
        _client = OpenAI(api_key=_API_KEY, base_url=_API_BASE)
    return _client


# ---------------------------------------------------------------------------
# Rate Limiting（内存 sliding-window）
# ---------------------------------------------------------------------------
_call_times: dict[str, list[float]] = defaultdict(list)

RATE_LIMIT_MAX_CALLS = int(get_secret("RATE_LIMIT_MAX_CALLS", "20"))
RATE_LIMIT_WINDOW    = int(get_secret("RATE_LIMIT_WINDOW", "3600"))


def _rate_limit_check(user_id: str = "default") -> tuple[bool, int]:
    """Sliding-window rate limit. 返回 (allowed, remaining)."""
    now = time.time()
    _call_times[user_id] = [t for t in _call_times[user_id] if now - t < RATE_LIMIT_WINDOW]
    remaining = RATE_LIMIT_MAX_CALLS - len(_call_times[user_id])
    if remaining <= 0:
        return False, 0
    _call_times[user_id].append(now)
    return True, remaining - 1


def get_rate_limit_remaining(user_id: str = "default") -> int:
    """返回当前窗口内剩余调用次数（不消耗配额）。"""
    now = time.time()
    used = len([t for t in _call_times[user_id] if now - t < RATE_LIMIT_WINDOW])
    return max(0, RATE_LIMIT_MAX_CALLS - used)


def _check_preconditions(user_id: str = "default") -> str | None:
    """返回错误信息字符串；None 表示可以继续调用。"""
    if not get_secret("NVIDIA_API_KEY"):
        return "⚠️ 请先设置 NVIDIA_API_KEY（.env 文件或 Streamlit Cloud Secrets）"
    allowed, _ = _rate_limit_check(user_id)
    if not allowed:
        wait_min = RATE_LIMIT_WINDOW // 60
        return f"⚠️ 调用频率超限，每 {wait_min} 分钟最多 {RATE_LIMIT_MAX_CALLS} 次，请稍后再试。"
    return None


def _handle_api_error(e: Exception) -> str:
    if isinstance(e, AuthenticationError):
        return "⚠️ NVIDIA API Key 无效，请检查 NVIDIA_API_KEY 是否正确。"
    if isinstance(e, RateLimitError):
        return "⚠️ API 调用超出 NVIDIA NIM 平台限额，请稍后重试或升级套餐。"
    if isinstance(e, APITimeoutError):
        return "⚠️ 请求超时，请检查网络连接后重试。"
    if isinstance(e, APIStatusError):
        return f"⚠️ NVIDIA NIM 服务器错误 ({e.status_code})，请稍后重试。"
    return f"⚠️ 调用失败: {e}"


# ---------------------------------------------------------------------------
# 核心调用 — 非流式
# ---------------------------------------------------------------------------
def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    user_id: str = "default",
) -> str:
    """非流式调用，返回完整文本字符串。"""
    err = _check_preconditions(user_id)
    if err:
        return err

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = _get_client().chat.completions.create(
            model=_MODEL,
            messages=messages,
            temperature=0.7,
            timeout=60,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return _handle_api_error(e)


# 向后兼容别名
call_kimi = call_llm


# ---------------------------------------------------------------------------
# 核心调用 — 流式
# ---------------------------------------------------------------------------
def stream_llm(
    prompt: str,
    system_prompt: str | None = None,
    user_id: str = "default",
) -> Generator[str, None, None]:
    """
    流式调用，返回文本 token 的生成器。
    供 Streamlit st.write_stream() 消费。
    若发生错误，yield 错误消息字符串后结束。
    """
    err = _check_preconditions(user_id)
    if err:
        yield err
        return

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        stream = _get_client().chat.completions.create(
            model=_MODEL,
            messages=messages,
            temperature=0.7,
            stream=True,
            timeout=90,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        yield _handle_api_error(e)


# 向后兼容别名
stream_kimi = stream_llm


def _is_generator(obj: object) -> bool:
    """精确判断是否为生成器对象。"""
    return isinstance(obj, types.GeneratorType)


# ---------------------------------------------------------------------------
# 业务函数
# ---------------------------------------------------------------------------

def generate_email(
    product: str,
    customer: str,
    features: str,
    tone: str = "简洁专业",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_email_prompt(product, customer, features, tone)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def reply_inquiry(
    inquiry: str,
    customer_name: str = "",
    your_name: str = "",
    company_name: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_inquiry_prompt(inquiry, customer_name, your_name, company_name)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_product_intro(
    product: str,
    features: str,
    target: str,
    languages: list[str],
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_product_intro_prompt(product, features, target, languages)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_followup(
    customer: str,
    stage: str,
    product: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_followup_prompt(customer, stage, product)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)
