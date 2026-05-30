"""
utils/ai_gateway.py
-------------------
Multi-model AI gateway supporting provider switching, fallback, and cost tracking.

Supported providers:
  - nvidia: NVIDIA NIM (Llama-3.3-70b, Mistral-Large-2, etc.)
  - openai: OpenAI (GPT-4o, GPT-4o-mini)
  - deepseek: DeepSeek (DeepSeek-V3, DeepSeek-Chat)
  - custom: Any OpenAI-compatible endpoint (user-configured base URL + API key)

Model selection:
  - User preference (from AI settings page) — custom provider takes highest priority
  - Tier-based defaults (free=fast, pro=balanced, team=premium)
  - Automatic fallback on failure

Usage:
    from utils.ai_gateway import get_gateway
    gw = get_gateway()
    result = gw.generate(prompt, system_prompt, tier="balanced")
    stream = gw.stream(prompt, system_prompt, tier="balanced")
"""
from __future__ import annotations

from typing import Generator

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment, misc]

from config.ai_models import load_ai_model_config
from utils.analytics import track_event
from utils.logger import get_logger
from utils.secrets import get_secret

logger = get_logger("ai_gateway")

# ---------------------------------------------------------------------------
# Custom provider helpers
# ---------------------------------------------------------------------------

def _get_custom_provider_config() -> dict | None:
    """
    Read user-configured custom provider from session prefs.

    Returns a provider-config-style dict if the custom provider is enabled
    and has a non-empty base_url + api_key, otherwise None.
    """
    try:
        from utils.user_prefs import get_prefs
        prefs = get_prefs()
    except Exception:
        return None

    if prefs.get("custom_provider_enabled", "false").lower() != "true":
        return None

    base_url = prefs.get("custom_provider_base_url", "").strip().rstrip("/")
    api_key  = prefs.get("custom_provider_api_key", "").strip()
    model_id = prefs.get("custom_provider_model", "").strip()
    name     = prefs.get("custom_provider_name", "custom").strip() or "custom"

    if not base_url or not api_key or not model_id:
        return None

    return {
        "base_url": base_url,
        "api_key":  api_key,
        "model_id": model_id,
        "name":     name,
    }


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------
_AI_MODEL_CONFIG = load_ai_model_config()
PROVIDERS: dict[str, dict] = _AI_MODEL_CONFIG["providers"]
TIER_STRATEGY: dict[str, dict] = _AI_MODEL_CONFIG["tier_strategy"]
PLAN_DEFAULTS: dict[str, str] = _AI_MODEL_CONFIG["plan_defaults"]


class AIGateway:
    """
    Unified AI generation gateway with multi-provider support.

    Priority order for model selection:
      1. User-configured custom provider (base_url + api_key + model from prefs)
      2. Explicit provider/model override arguments
      3. Tier-based strategy (fast/balanced/premium)
      4. Automatic fallback to any available provider
    """

    def __init__(self):
        self._clients: dict[str, OpenAI | None] = {}
        # Custom client is ephemeral — re-created when prefs change
        self._custom_client: OpenAI | None = None
        self._custom_client_key: str = ""  # tracks which api_key+url the client was built for

    # ── Client builders ───────────────────────────────

    def _get_client(self, provider: str) -> OpenAI | None:
        """Get or create an OpenAI-compatible client for a built-in provider."""
        if provider in self._clients:
            return self._clients[provider]

        config = PROVIDERS.get(provider)
        if not config:
            return None

        api_key = get_secret(config["key_env"])
        if not api_key:
            return None

        client = OpenAI(api_key=api_key, base_url=config["base_url"])
        self._clients[provider] = client
        return client

    def _get_custom_client(self) -> tuple[OpenAI | None, str]:
        """
        Return (client, model_id) for the user-configured custom provider.
        Returns (None, "") if the custom provider is not configured / disabled.
        """
        cfg = _get_custom_provider_config()
        if not cfg:
            return None, ""

        cache_key = f"{cfg['base_url']}|{cfg['api_key']}"
        if self._custom_client is None or self._custom_client_key != cache_key:
            self._custom_client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
            self._custom_client_key = cache_key

        return self._custom_client, cfg["model_id"]

    # ── Provider discovery ────────────────────────────

    def get_available_providers(self) -> list[str]:
        """Return list of built-in providers that have API keys configured."""
        available = []
        for name, config in PROVIDERS.items():
            if get_secret(config["key_env"]):
                available.append(name)
        return available

    def get_available_models(self) -> list[dict]:
        """Return all available models across configured providers (including custom)."""
        models = []
        for provider_name in self.get_available_providers():
            config = PROVIDERS[provider_name]
            for model_key, model_id in config["models"].items():
                models.append({
                    "provider": provider_name,
                    "key": model_key,
                    "model_id": model_id,
                    "cost": config["cost_per_1k_tokens"],
                })
        # Custom provider entry
        cfg = _get_custom_provider_config()
        if cfg:
            models.insert(0, {
                "provider": "custom",
                "key": cfg["model_id"],
                "model_id": cfg["model_id"],
                "cost": 0.0,
                "custom_name": cfg["name"],
            })
        return models

    # ── Generation ────────────────────────────────────

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tier: str = "balanced",
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        fallback: bool = True,
    ) -> str:
        """
        Non-streaming generation with automatic fallback.

        Custom provider (from user prefs) takes highest priority when enabled.

        Returns:
            Generated text string, or error message starting with "⚠️"
        """
        # ── Priority 1: custom provider ──
        custom_client, custom_model_id = self._get_custom_client()
        if custom_client:
            logger.info("Using custom provider model=%s", custom_model_id)
            messages = self._build_messages(prompt, system_prompt)
            kwargs: dict = {"model": custom_model_id, "messages": messages,
                            "temperature": temperature, "timeout": 60}
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            try:
                resp = custom_client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as e:
                logger.error("Custom provider call failed (%s): %s", custom_model_id, e)
                if not fallback:
                    return f"⚠️ 自定义模型调用失败: {e}"
                logger.info("Falling back to built-in providers after custom provider failure")
                # Fall through to built-in providers below

        # ── Priority 2 & 3: explicit override or tier strategy ──
        provider_name, model_id = self._resolve_model(tier, provider, model)
        client = self._get_client(provider_name)

        if not client:
            if fallback:
                return self._fallback_generate(prompt, system_prompt, temperature, max_tokens, exclude=provider_name)
            return "⚠️ AI 服务未配置，请检查 API Key 设置"

        messages = self._build_messages(prompt, system_prompt)
        kwargs = {"model": model_id, "messages": messages, "temperature": temperature, "timeout": 60}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        try:
            resp = client.chat.completions.create(**kwargs)
            result = resp.choices[0].message.content or ""
            self._track_usage(provider_name, model_id, resp)
            return result
        except Exception as e:
            logger.error("AI generation failed (%s/%s): %s", provider_name, model_id, e)
            if fallback:
                return self._fallback_generate(prompt, system_prompt, temperature, max_tokens, exclude=provider_name)
            return f"⚠️ AI 调用失败: {e}"

    def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tier: str = "balanced",
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """
        Streaming generation. Yields text tokens.

        Custom provider (from user prefs) takes highest priority when enabled.
        Falls back to non-streaming on provider failure.
        """
        # ── Priority 1: custom provider ──
        custom_client, custom_model_id = self._get_custom_client()
        if custom_client:
            logger.info("Streaming via custom provider model=%s", custom_model_id)
            messages = self._build_messages(prompt, system_prompt)
            kwargs: dict = {"model": custom_model_id, "messages": messages,
                            "temperature": temperature, "stream": True, "timeout": 90}
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            try:
                stream_resp = custom_client.chat.completions.create(**kwargs)
                for chunk in stream_resp:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return
            except Exception as e:
                logger.error("Custom provider stream failed (%s): %s", custom_model_id, e)
                yield f"⚠️ 自定义模型调用失败: {e}"
                return

        # ── Priority 2 & 3: explicit override or tier strategy ──
        provider_name, model_id = self._resolve_model(tier, provider, model)
        client = self._get_client(provider_name)

        if not client:
            yield "⚠️ AI 服务未配置，请检查 API Key 设置"
            return

        messages = self._build_messages(prompt, system_prompt)
        kwargs = {"model": model_id, "messages": messages, "temperature": temperature, "stream": True, "timeout": 90}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        try:
            stream_resp = client.chat.completions.create(**kwargs)
            for chunk in stream_resp:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error("AI stream failed (%s/%s): %s", provider_name, model_id, e)
            yield f"⚠️ AI 调用失败: {e}"

    # ── Internal helpers ──────────────────────────────

    def _resolve_model(
        self, tier: str, provider: str | None, model: str | None
    ) -> tuple[str, str]:
        """Resolve the actual provider and model ID to use."""
        if provider and model:
            config = PROVIDERS.get(provider, {})
            model_id = config.get("models", {}).get(model, model)
            return provider, model_id

        # Use tier strategy
        strategy = TIER_STRATEGY.get(tier, TIER_STRATEGY["balanced"])
        prov = strategy["provider"]
        mod_key = strategy["model"]

        # Check if preferred provider is available
        if not get_secret(PROVIDERS[prov]["key_env"]):
            # Fall back to any available provider
            for name in self.get_available_providers():
                prov = name
                mod_key = PROVIDERS[name]["default_model"]
                break

        config = PROVIDERS.get(prov, {})
        model_id = config.get("models", {}).get(mod_key, mod_key)
        return prov, model_id

    def _build_messages(self, prompt: str, system_prompt: str | None) -> list[dict]:
        """Build the messages array for the API call."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _fallback_generate(
        self, prompt: str, system_prompt: str | None,
        temperature: float, max_tokens: int | None, exclude: str
    ) -> str:
        """Try other available providers as fallback."""
        for provider_name in self.get_available_providers():
            if provider_name == exclude:
                continue
            logger.info("Falling back to provider: %s", provider_name)
            config = PROVIDERS[provider_name]
            default_model = config["default_model"]
            model_id = config["models"][default_model]
            client = self._get_client(provider_name)
            if not client:
                continue
            try:
                messages = self._build_messages(prompt, system_prompt)
                kwargs = {"model": model_id, "messages": messages, "temperature": temperature, "timeout": 60}
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                resp = client.chat.completions.create(**kwargs)
                self._track_usage(provider_name, model_id, resp)
                return resp.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Fallback %s also failed: %s", provider_name, e)
                continue
        return "⚠️ 所有 AI 服务暂时不可用，请稍后重试"

    def _track_usage(self, provider: str, model: str, response) -> None:
        """Track token usage for cost analysis."""
        try:
            usage = response.usage
            if usage:
                track_event("ai_usage", {
                    "provider": provider,
                    "model": model,
                    "input_tokens": usage.prompt_tokens,
                    "output_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                })
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_gateway: AIGateway | None = None


def get_gateway() -> AIGateway:
    """Get the singleton AI gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
    return _gateway
