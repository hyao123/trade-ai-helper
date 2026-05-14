"""
utils/ai_client.py
------------------
NVIDIA NIM API 调用层（OpenAI 兼容接口）。

- 使用 openai SDK（NVIDIA NIM 完全兼容 OpenAI 接口）
- call_llm()       非流式，返回 str
- stream_llm()     流式，返回 Generator[str]，供 st.write_stream() 消费
- Rate Limiting 基于内存 sliding-window（注：多进程/重启后计数重置）
- 所有 Prompt 模板从 config.prompts 导入
- Rate-limit slot 仅在 API 成功时消耗（失败自动回滚）

NVIDIA NIM API 文档：https://docs.api.nvidia.com/nim/docs/api-quickstart
"""

from __future__ import annotations

import os
import time
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
from utils.logger import get_logger

logger = get_logger("ai_client")

# ---------------------------------------------------------------------------
# 客户端单例
# ---------------------------------------------------------------------------
_API_KEY  = get_secret("NVIDIA_API_KEY")
_API_BASE = "https://integrate.api.nvidia.com/v1"
_MODEL    = get_secret("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """返回全局单例 OpenAI 客户端，避免每次调用新建连接池。"""
    global _client, _API_KEY
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


def _rate_limit_consume(user_id: str) -> None:
    """消耗一个 rate-limit slot。"""
    _call_times[user_id].append(time.time())


def _rate_limit_rollback(user_id: str) -> None:
    """回滚最近一个 slot（API 调用失败时调用）。"""
    if _call_times[user_id]:
        _call_times[user_id].pop()


def get_rate_limit_remaining(user_id: str = "default") -> int:
    """返回当前窗口内剩余调用次数（不消耗配额）。"""
    now = time.time()
    used = len([t for t in _call_times[user_id] if now - t < RATE_LIMIT_WINDOW])
    return max(0, RATE_LIMIT_MAX_CALLS - used)


def get_rate_limit_reset_seconds(user_id: str = "default") -> int:
    """返回最早 slot 释放的剩余秒数（供 UI 显示倒计时）。"""
    now = time.time()
    active = [t for t in _call_times[user_id] if now - t < RATE_LIMIT_WINDOW]
    if not active:
        return 0
    earliest = min(active)
    return max(0, int(RATE_LIMIT_WINDOW - (now - earliest)))


def _check_preconditions(user_id: str = "default") -> str | None:
    """返回错误信息字符串；None 表示可以继续调用。不消耗 rate limit slot。"""
    if not get_secret("NVIDIA_API_KEY"):
        return "⚠️ 请先设置 NVIDIA_API_KEY（.env 文件或 Streamlit Cloud Secrets）"

    # Tier-based daily limit check (only for logged-in non-admin users)
    from utils.user_auth import get_current_user
    current_user = get_current_user()
    if current_user and current_user.get("username") not in (None, "admin"):
        from utils.pricing import increment_usage
        username = current_user["username"]
        ok, err_msg = increment_usage(username)
        if not ok:
            logger.warning("Daily tier limit hit for user=%s", username)
            return err_msg

    # Sliding-window burst guard (secondary)
    now = time.time()
    _call_times[user_id] = [t for t in _call_times[user_id] if now - t < RATE_LIMIT_WINDOW]
    if len(_call_times[user_id]) >= RATE_LIMIT_MAX_CALLS:
        wait_min = RATE_LIMIT_WINDOW // 60
        logger.warning("Rate limit hit for user=%s", user_id)
        return f"⚠️ 调用频率超限，每 {wait_min} 分钟最多 {RATE_LIMIT_MAX_CALLS} 次，请稍后再试。"
    return None


def _handle_api_error(e: Exception) -> str:
    logger.error("API error: %s: %s", type(e).__name__, e)
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
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """非流式调用，返回完整文本字符串。失败时自动回滚 rate-limit slot。"""
    err = _check_preconditions(user_id)
    if err:
        return err

    logger.info("API call: model=%s, user=%s", _MODEL, user_id)
    # 先消耗 slot，失败则回滚
    _rate_limit_consume(user_id)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {
        "model": _MODEL,
        "messages": messages,
        "temperature": temperature,
        "timeout": 60,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    try:
        resp = _get_client().chat.completions.create(**kwargs)
        logger.info("API call success: model=%s, user=%s", _MODEL, user_id)
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("API call failed: model=%s, user=%s", _MODEL, user_id)
        _rate_limit_rollback(user_id)  # 失败回滚
        # Rollback tier-based daily usage if applicable
        from utils.user_auth import get_current_user
        current_user = get_current_user()
        if current_user and current_user.get("username") not in (None, "admin"):
            from utils.pricing import decrement_usage
            decrement_usage(current_user["username"])
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
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> Generator[str, None, None]:
    """
    流式调用，返回文本 token 的生成器。
    仅在收到第一个 token 后才消耗 rate-limit slot。
    """
    err = _check_preconditions(user_id)
    if err:
        yield err
        return

    logger.info("Stream API call: model=%s, user=%s", _MODEL, user_id)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {
        "model": _MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
        "timeout": 90,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    try:
        stream = _get_client().chat.completions.create(**kwargs)
        slot_consumed = False
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                if not slot_consumed:
                    _rate_limit_consume(user_id)  # 第一个 token 到达才消耗
                    slot_consumed = True
                yield delta
        # 如果流完全没产出 token（空响应），不消耗 slot
    except Exception as e:
        # 流式失败不消耗 slot（slot_consumed 为 False 时已不消耗）
        logger.error("Stream API call failed: model=%s, user=%s", _MODEL, user_id)
        # Rollback tier-based daily usage if no token was produced
        if not slot_consumed:
            from utils.user_auth import get_current_user
            current_user = get_current_user()
            if current_user and current_user.get("username") not in (None, "admin"):
                from utils.pricing import decrement_usage
                decrement_usage(current_user["username"])
        yield _handle_api_error(e)


# 向后兼容别名
stream_kimi = stream_llm


# ---------------------------------------------------------------------------
# 业务函数
# ---------------------------------------------------------------------------

def generate_email(
    product: str,
    customer: str,
    features: str,
    tone: str = "简洁专业",
    language: str = "英语",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_email_prompt(product, customer, features, tone, language)
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


def generate_listing(
    product: str,
    keywords: str,
    features: str,
    platform: str = "Amazon",
    category: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    from config.prompts import build_listing_prompt
    prompt, system = build_listing_prompt(product, keywords, features, platform, category)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_social_post(
    product: str,
    features: str,
    platform: str = "All Platforms",
    audience: str = "",
    promo: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    from config.prompts import build_social_post_prompt
    prompt, system = build_social_post_prompt(product, features, platform, audience, promo)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_bulk_email(
    company: str,
    contact_name: str,
    product: str,
    industry: str = "",
    country: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    from config.prompts import build_bulk_email_prompt
    prompt, system = build_bulk_email_prompt(company, contact_name, product, industry, country)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_negotiation(
    scenario: str,
    product: str,
    current_offer: str,
    bottom_line: str,
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    from config.prompts import build_negotiation_prompt
    prompt, system = build_negotiation_prompt(scenario, product, current_offer, bottom_line)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_holiday_greeting(
    holiday: str,
    customer_name: str,
    company: str,
    relationship_level: str,
    product_mention: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    from config.prompts import build_holiday_greeting_prompt
    prompt, system = build_holiday_greeting_prompt(holiday, customer_name, company, relationship_level, product_mention)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_email_polish(
    content: str,
    source_lang: str,
    target_lang: str,
    mode: str,
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    from config.prompts import build_email_polish_prompt
    prompt, system = build_email_polish_prompt(content, source_lang, target_lang, mode)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


def generate_complaint_response(
    complaint_type: str,
    severity: str,
    relationship: str,
    proposed_solution: str,
    customer_complaint: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    from config.prompts import build_complaint_response_prompt
    prompt, system = build_complaint_response_prompt(complaint_type, severity, relationship, proposed_solution, customer_complaint)
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)
