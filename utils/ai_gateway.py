"""
utils/ai_gateway.py
-------------------
Multi-model AI gateway supporting provider switching, fallback, and cost tracking.

Supported providers:
  - nvidia: NVIDIA NIM (Llama-3.3-70b, Mistral-Large-2, etc.)
  - openai: OpenAI (GPT-4o, GPT-4o-mini)
  - deepseek: DeepSeek (DeepSeek-V3, DeepSeek-Chat)

Model selection:
  - User preference (from AI settings page)
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

from utils.analytics import track_event
from utils.logger import get_logger
from utils.secrets import get_secret

logger = get_logger("ai_gateway")


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, dict] = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_env": "NVIDIA_API_KEY",
        "models": {
            "llama-3.3-70b": "meta/llama-3.3-70b-instruct",
            "mistral-large-2": "mistralai/mistral-large-2-instruct",
        },
        "default_model": "llama-3.3-70b",
        "cost_per_1k_tokens": 0.003,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
        "models": {
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
        },
        "default_model": "gpt-4o-mini",
        "cost_per_1k_tokens": 0.015,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "key_env": "DEEPSEEK_API_KEY",
        "models": {
            "deepseek-chat": "deepseek-chat",
            "deepseek-reasoner": "deepseek-reasoner",
        },
        "default_model": "deepseek-chat",
        "cost_per_1k_tokens": 0.001,
    },
}

# Tier-to-strategy mapping
TIER_STRATEGY: dict[str, dict] = {
    "fast": {"provider": "deepseek", "model": "deepseek-chat"},
    "balanced": {"provider": "nvidia", "model": "llama-3.3-70b"},
    "premium": {"provider": "openai", "model": "gpt-4o"},
}

# Plan-to-default tier
PLAN_DEFAULTS: dict[str, str] = {
    "free": "fast",
    "pro": "balanced",
    "team": "premium",
    "enterprise": "premium",
}


class AIGateway:
    """
    Unified AI generation gateway with multi-provider support.
    """

    def __init__(self):
        self._clients: dict[str, OpenAI | None] = {}

    def _get_client(self, provider: str) -> OpenAI | None:
        """Get or create an OpenAI-compatible client for a provider."""
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

    def get_available_providers(self) -> list[str]:
        """Return list of providers that have API keys configured."""
        available = []
        for name, config in PROVIDERS.items():
            if get_secret(config["key_env"]):
                available.append(name)
        return available

    def get_available_models(self) -> list[dict]:
        """Return all available models across configured providers."""
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
        return models

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

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            tier: Strategy tier (fast/balanced/premium)
            provider: Override provider name
            model: Override model key
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            fallback: Whether to try other providers on failure

        Returns:
            Generated text string, or error message starting with "⚠️"
        """
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

        Falls back to non-streaming on provider failure.
        """
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
