"""
utils/ai_client.py
------------------
AI 调用层 — 支持多模型路由（NVIDIA NIM / OpenAI / DeepSeek）。

当 ai_gateway 检测到多个 API Key 时，自动使用智能路由和降级机制。
仅配置 NVIDIA_API_KEY 时保持原有行为不变。

- call_llm()       非流式，返回 str
- stream_llm()     流式，返回 Generator[str]，供 st.write_stream() 消费
- Rate Limiting 基于持久化 sliding-window（重启后保留窗口内计数）
- 所有 Prompt 模板从 config.prompts 导入
- Rate-limit slot 仅在 API 成功时消耗（失败自动回滚）

Multi-model routing:
  - 配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 后自动启用 AI Gateway
  - 用户可通过 AI 偏好页选择模型
  - 按用户套餐自动选择模型层级 (free=fast, pro=balanced, team=premium)
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from typing import Generator
from uuid import uuid4

from openai import (
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from config.prompts import (
    build_customer_profile_prompt,
    build_email_prompt,
    build_followup_prompt,
    build_hs_code_prompt,
    build_inquiry_prompt,
    build_intent_recognition_prompt,
    build_product_intro_prompt,
    build_smart_quote_prompt,
)
from utils.logger import get_logger
from utils.secrets import get_secret
from utils.storage import load_json, save_json

logger = get_logger("ai_client")


def _new_request_id() -> str:
    """Return a short random id for correlating one AI call across logs."""
    return uuid4().hex[:12]


def _build_messages(prompt: str, system_prompt: str | None) -> list[dict]:
    """Build the chat messages array (system first, then user)."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages

# ---------------------------------------------------------------------------
# 客户端单例
# ---------------------------------------------------------------------------
_API_BASE = "https://integrate.api.nvidia.com/v1"

_client: OpenAI | None = None
_client_api_key: str | None = None


def _get_model() -> str:
    """Return the configured NVIDIA model name, always reading the latest secret."""
    return get_secret("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")


def _get_client() -> OpenAI:
    """返回全局单例 OpenAI 客户端，避免每次调用新建连接池。"""
    global _client, _client_api_key
    current_key = get_secret("NVIDIA_API_KEY")
    if _client is None or current_key != _client_api_key:
        _client_api_key = current_key
        _client = OpenAI(api_key=_client_api_key, base_url=_API_BASE)
    return _client


# ---------------------------------------------------------------------------
# Rate Limiting（持久化 sliding-window）
# ---------------------------------------------------------------------------
_call_times: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_FILE = "ai_rate_limits.json"

# Backward-compatible module-level aliases for external callers that import
# RATE_LIMIT_MAX_CALLS or RATE_LIMIT_WINDOW directly.  These are evaluated
# once on first import; prefer the lazy _get_rate_limit_*() functions for
# values that may be updated at runtime.
RATE_LIMIT_MAX_CALLS = int(get_secret("RATE_LIMIT_MAX_CALLS", "20"))
RATE_LIMIT_WINDOW = int(get_secret("RATE_LIMIT_WINDOW", "3600"))

_RATE_LIMIT_MAX_CALLS_CACHED: int | None = None
_RATE_LIMIT_WINDOW_CACHED: int | None = None


def _get_rate_limit_max_calls() -> int:
    """Lazy-read rate limit max calls from secrets, cached after first read."""
    global _RATE_LIMIT_MAX_CALLS_CACHED
    if _RATE_LIMIT_MAX_CALLS_CACHED is None:
        _RATE_LIMIT_MAX_CALLS_CACHED = int(get_secret("RATE_LIMIT_MAX_CALLS", "20"))
    return _RATE_LIMIT_MAX_CALLS_CACHED


def _get_rate_limit_window() -> int:
    """Lazy-read rate limit window from secrets, cached after first read."""
    global _RATE_LIMIT_WINDOW_CACHED
    if _RATE_LIMIT_WINDOW_CACHED is None:
        _RATE_LIMIT_WINDOW_CACHED = int(get_secret("RATE_LIMIT_WINDOW", "3600"))
    return _RATE_LIMIT_WINDOW_CACHED


def _load_rate_limit_slots(user_id: str | None = None) -> None:
    """Hydrate missing in-memory rate-limit slots from persistent storage."""
    if user_id is not None and user_id in _call_times:
        return
    raw = load_json(_RATE_LIMIT_FILE, default={})
    if not isinstance(raw, dict):
        return
    for stored_user_id, slots in raw.items():
        if isinstance(slots, list) and stored_user_id not in _call_times:
            _call_times[stored_user_id] = [float(slot) for slot in slots]


def _save_rate_limit_slots() -> None:
    """Persist sliding-window rate-limit slots for restart-safe counters."""
    save_json(_RATE_LIMIT_FILE, {user_id: slots for user_id, slots in _call_times.items() if slots})


def _prune_rate_limit_slots(user_id: str, now: float | None = None, *, persist: bool = False) -> list[float]:
    """Drop expired sliding-window slots and return the active slots.

    When *persist* is False (default), only the in-memory state is updated.
    Callers that mutate the slot list (consume / rollback) are responsible
    for calling ``_save_rate_limit_slots()`` once after all mutations,
    avoiding redundant file I/O.
    """
    _load_rate_limit_slots(user_id)
    window = _get_rate_limit_window()
    current_time = time.time() if now is None else now
    active = [t for t in _call_times[user_id] if current_time - t < window]
    _call_times[user_id] = active
    if persist:
        _save_rate_limit_slots()
    return active


def _rate_limit_check(user_id: str = "default") -> tuple[bool, int]:
    """Check and consume one sliding-window rate-limit slot.

    Returns ``(allowed, remaining)``. Expired slots are pruned before the
    decision, and a successful check consumes exactly one slot.
    """
    max_calls = _get_rate_limit_max_calls()
    now = time.time()
    active = _prune_rate_limit_slots(user_id, now)
    if len(active) >= max_calls:
        return False, 0

    active.append(now)
    _save_rate_limit_slots()
    return True, max(0, max_calls - len(active))


def _rate_limit_consume(user_id: str) -> None:
    """消耗一个 rate-limit slot（prune + append + 单次持久化）。"""
    now = time.time()
    _prune_rate_limit_slots(user_id, now).append(now)
    _save_rate_limit_slots()  # single write for prune + consume


def _rate_limit_rollback(user_id: str) -> None:
    """回滚最近一个 slot（API 调用失败时调用）。"""
    _load_rate_limit_slots(user_id)
    if _call_times[user_id]:
        _call_times[user_id].pop()
        _save_rate_limit_slots()


def get_rate_limit_remaining(user_id: str = "default") -> int:
    """返回当前窗口内剩余调用次数（不消耗配额）。"""
    used = len(_prune_rate_limit_slots(user_id))
    return max(0, _get_rate_limit_max_calls() - used)


def get_rate_limit_reset_seconds(user_id: str = "default") -> int:
    """返回最早 slot 释放的剩余秒数（供 UI 显示倒计时）。"""
    now = time.time()
    active = _prune_rate_limit_slots(user_id, now)
    if not active:
        return 0
    earliest = min(active)
    return max(0, int(_get_rate_limit_window() - (now - earliest)))


def _any_provider_configured() -> bool:
    """Return True when any provider key (built-in via config, or custom) is present.

    Provider existence is derived from the loaded ``PROVIDERS`` config rather than
    a hard-coded key tuple, so configuring only qwen/zhipu/moonshot etc. is honored.
    """
    has_any_key = any(
        get_secret(cfg["key_env"]) for cfg in _get_builtin_providers().values()
    )
    if not has_any_key:
        try:
            from utils.ai_gateway import _get_custom_provider_config
            has_any_key = bool(_get_custom_provider_config())
        except Exception:
            pass
    return has_any_key


def _get_builtin_providers() -> dict:
    """Return the provider config map, tolerating import/load failures."""
    try:
        from utils.ai_gateway import PROVIDERS
        return PROVIDERS if isinstance(PROVIDERS, dict) else {}
    except Exception:
        return {}


def _check_preconditions(user_id: str = "default") -> str | None:
    """返回错误信息字符串；None 表示可以继续调用。不消耗 rate limit slot。"""
    if not _any_provider_configured():
        return "⚠️ 请先设置 AI API Key（NVIDIA / OpenAI / DeepSeek 或自定义 Provider）"

    # Sliding-window burst guard runs BEFORE the tier daily-limit increment so a
    # rate-limited request does not burn a daily AI generation.
    max_calls = _get_rate_limit_max_calls()
    window = _get_rate_limit_window()
    if len(_prune_rate_limit_slots(user_id)) >= max_calls:
        wait_min = window // 60
        logger.warning("Rate limit hit for user=%s", user_id)
        return f"⚠️ 调用频率超限，每 {wait_min} 分钟最多 {max_calls} 次，请稍后再试。"

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

    return None


def _error_code(e: Exception) -> str:
    """Build a short deterministic error code without exposing provider details."""
    raw = f"{type(e).__name__}:{str(e)[:200]}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:8].upper()


def _handle_api_error(e: Exception) -> str:
    """Return a sanitized user-facing AI error while logging full details."""
    code = _error_code(e)
    logger.exception("AI provider error code=%s type=%s", code, type(e).__name__)
    if isinstance(e, AuthenticationError):
        return f"⚠️ AI 服务认证失败，请联系管理员检查 API Key 配置。错误码：{code}"
    if isinstance(e, RateLimitError):
        return f"⚠️ AI 服务当前限流，请稍后重试。错误码：{code}"
    if isinstance(e, APITimeoutError):
        return f"⚠️ AI 请求超时，请稍后重试。错误码：{code}"
    if isinstance(e, APIStatusError):
        return f"⚠️ AI 服务暂时不可用，请稍后重试。错误码：{code}"
    return f"⚠️ AI 服务暂时不可用，请稍后重试。错误码：{code}"


def _log_gateway_fallback(e: Exception, *, stream: bool = False) -> None:
    """Log gateway fallback without showing provider exception text to users."""
    code = _error_code(e)
    logger.warning(
        "%s failed, falling back to direct provider. error_code=%s type=%s",
        "Gateway stream" if stream else "Gateway call",
        code,
        type(e).__name__,
        exc_info=True,
    )


def _should_use_gateway() -> bool:
    """Determine whether the multi-model gateway should handle the call.

    Returns True when any built-in provider or the custom provider is configured.
    The gateway routes and falls back correctly for a single provider too, so it
    always engages when at least one provider is available. When nothing is
    configured, callers are gated earlier by ``_check_preconditions``.
    """
    # Custom provider → always go through gateway
    try:
        from utils.ai_gateway import _get_custom_provider_config
        if _get_custom_provider_config():
            return True
    except Exception:
        pass

    return any(
        get_secret(cfg["key_env"]) for cfg in _get_builtin_providers().values()
    )


def _get_user_model_tier(user_id: str) -> str:
    """Get the AI model tier for a user based on their plan.

    Returns: 'fast', 'balanced', or 'premium'
    """
    try:
        from utils.user_auth import get_current_user
        current_user = get_current_user()
        if current_user:
            tier = current_user.get("tier", "free")
            from utils.ai_gateway import PLAN_DEFAULTS
            return PLAN_DEFAULTS.get(tier, "balanced")
    except Exception:
        pass
    return "balanced"


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
    """非流式调用，返回完整文本字符串。支持多模型路由，失败时自动回滚 rate-limit slot。"""
    err = _check_preconditions(user_id)
    if err:
        return err

    request_id = _new_request_id()

    # ── Multi-model gateway路由 ──
    if _should_use_gateway():
        try:
            from utils.ai_gateway import get_gateway
            gw = get_gateway()
            tier = _get_user_model_tier(user_id)
            logger.info("API call via gateway: tier=%s, user=%s, request_id=%s", tier, user_id, request_id)
            _rate_limit_consume(user_id)
            result = gw.generate(
                prompt,
                system_prompt,
                tier=tier,
                temperature=temperature,
                max_tokens=max_tokens,
                request_id=request_id,
            )
            if result.startswith("⚠️"):
                _rate_limit_rollback(user_id)
                _rollback_tier_usage()
            return result
        except Exception as e:
            _log_gateway_fallback(e)
            _rate_limit_rollback(user_id)
            # Fall through to direct NVIDIA call below

    # ── Direct NVIDIA NIM call (original path) ──
    model = _get_model()
    logger.info("API call: model=%s, user=%s, request_id=%s", model, user_id, request_id)
    _rate_limit_consume(user_id)

    messages = _build_messages(prompt, system_prompt)

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "timeout": 60,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    try:
        resp = _get_client().chat.completions.create(**kwargs)
        logger.info("API call success: model=%s, user=%s, request_id=%s", model, user_id, request_id)
        _record_usage("nvidia", model, resp, request_id)
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("API call failed: model=%s, user=%s, request_id=%s", model, user_id, request_id)
        _rate_limit_rollback(user_id)
        _rollback_tier_usage()
        return _handle_api_error(e)


def _record_usage(provider: str, model: str, response, request_id: str | None = None) -> None:
    """Record token usage for cost tracking (direct-path mirror of gateway tracking)."""
    try:
        usage = getattr(response, "usage", None)
        if usage:
            from utils.analytics import track_event
            track_event("ai_usage", {
                "provider": provider,
                "model": model,
                "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
                "total_tokens": getattr(usage, "total_tokens", 0) or 0,
                "request_id": request_id or "",
            })
    except Exception as exc:  # tracking must never break the LLM call
        logger.debug("Usage tracking failed (non-critical): %s", exc)


def _rollback_tier_usage() -> None:
    """Rollback tier-based daily usage if applicable."""
    from utils.user_auth import get_current_user
    current_user = get_current_user()
    if current_user and current_user.get("username") not in (None, "admin"):
        from utils.pricing import decrement_usage
        decrement_usage(current_user["username"])


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
    流式调用，返回文本 token 的生成器。支持多模型路由。
    仅在收到第一个 token 后才消耗 rate-limit slot。
    """
    err = _check_preconditions(user_id)
    if err:
        yield err
        return

    request_id = _new_request_id()

    # ── Multi-model gateway路由 ──
    if _should_use_gateway():
        slot_consumed = False
        try:
            from utils.ai_gateway import get_gateway
            gw = get_gateway()
            tier = _get_user_model_tier(user_id)
            logger.info("Stream API call via gateway: tier=%s, user=%s, request_id=%s", tier, user_id, request_id)
            for token in gw.stream(
                prompt,
                system_prompt,
                tier=tier,
                temperature=temperature,
                max_tokens=max_tokens,
                request_id=request_id,
            ):
                if not slot_consumed and not token.startswith("⚠️"):
                    _rate_limit_consume(user_id)
                    slot_consumed = True
                yield token
            if not slot_consumed:
                _rollback_tier_usage()
            return
        except Exception as e:
            _log_gateway_fallback(e, stream=True)
            if slot_consumed:
                # We already emitted tokens and consumed a slot; falling through
                # to the direct path would double-consume and stream a second
                # response. Surface the failure instead.
                _rollback_tier_usage()
                yield _handle_api_error(e)
                return
            # Nothing was streamed yet -> safe to fall through to direct path.

    # ── Direct NVIDIA NIM call (original path) ──
    model = _get_model()
    logger.info("Stream API call: model=%s, user=%s, request_id=%s", model, user_id, request_id)
    messages = _build_messages(prompt, system_prompt)

    kwargs: dict = {
        "model": model,
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
        last_chunk = None
        for chunk in stream:
            last_chunk = chunk
            delta = chunk.choices[0].delta.content
            if delta:
                if not slot_consumed:
                    _rate_limit_consume(user_id)
                    slot_consumed = True
                yield delta
        if not slot_consumed:
            _rollback_tier_usage()
        if last_chunk is not None:
            _record_usage("nvidia", model, last_chunk, request_id)
    except Exception as e:
        logger.error("Stream API call failed: model=%s, user=%s, request_id=%s", model, user_id, request_id)
        if not slot_consumed:
            _rollback_tier_usage()
        yield _handle_api_error(e)


# 向后兼容别名
stream_kimi = stream_llm


# ---------------------------------------------------------------------------
# 业务函数
# ---------------------------------------------------------------------------

def _call_with_style(
    prompt: str,
    system: str | None = None,
    user_id: str = "default",
    stream: bool = False,
) -> str | Generator[str, None, None]:
    """Helper to append user AI style instructions/context and invoke LLM."""
    try:
        from utils.user_prefs import get_ai_style_suffix
        suffix = get_ai_style_suffix()
        if suffix:
            prompt = prompt + suffix
    except Exception:
        pass
    return stream_llm(prompt, system, user_id) if stream else call_llm(prompt, system, user_id)


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
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def reply_inquiry(
    inquiry: str,
    customer_name: str = "",
    your_name: str = "",
    company_name: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_inquiry_prompt(inquiry, customer_name, your_name, company_name)
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def product_intro(
    product_name: str,
    features: str,
    target_customer: str,
    language: str = "英语",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_product_intro_prompt(product_name, features, target_customer, language)
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def followup_email(
    customer_name: str,
    last_contact: str,
    purpose: str,
    tone: str = "简洁专业",
    language: str = "英语",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    prompt, system = build_followup_prompt(customer_name, last_contact, purpose, tone, language)
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def generate_followup(
    customer: str,
    stage: str,
    product: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    """生成外贸跟进邮件（基于跟进阶段）。"""
    prompt, system = build_followup_prompt(customer, stage, product)
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def generate_smart_quote(
    product: str,
    target_market: str,
    order_quantity: int,
    production_cost: str = "",
    competitor_info: str = "",
    trade_term: str = "FOB",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    """生成智能报价 / 定价策略建议。"""
    prompt, system = build_smart_quote_prompt(
        product, target_market, order_quantity, production_cost, competitor_info, trade_term
    )
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def lookup_hs_code(
    product: str,
    description: str = "",
    target_country: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    """基于产品生成 HS 编码建议。"""
    prompt, system = build_hs_code_prompt(product, description, target_country)
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def recognize_email_intent(
    email_content: str,
    context: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    """识别客户回复邮件的真实意图。"""
    prompt, system = build_intent_recognition_prompt(email_content, context)
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)


def analyze_customer_profile(
    company_name: str,
    website: str = "",
    industry: str = "",
    additional_info: str = "",
    stream: bool = False,
    user_id: str = "default",
) -> str | Generator[str, None, None]:
    """生成 B2B 客户画像深度分析。"""
    prompt, system = build_customer_profile_prompt(company_name, website, industry, additional_info)
    return _call_with_style(prompt, system, user_id=user_id, stream=stream)
