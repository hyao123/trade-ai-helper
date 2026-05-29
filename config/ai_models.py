"""External AI provider/model configuration loader."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger("ai_models")

_CONFIG_PATH = Path(__file__).with_name("ai_models.json")
_DEFAULT_CONFIG: dict[str, Any] = {
    "providers": {
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
            "models": {"gpt-4o": "gpt-4o", "gpt-4o-mini": "gpt-4o-mini"},
            "default_model": "gpt-4o-mini",
            "cost_per_1k_tokens": 0.015,
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "key_env": "DEEPSEEK_API_KEY",
            "models": {"deepseek-chat": "deepseek-chat", "deepseek-reasoner": "deepseek-reasoner"},
            "default_model": "deepseek-chat",
            "cost_per_1k_tokens": 0.001,
        },
    },
    "tier_strategy": {
        "fast": {"provider": "deepseek", "model": "deepseek-chat"},
        "balanced": {"provider": "nvidia", "model": "llama-3.3-70b"},
        "premium": {"provider": "openai", "model": "gpt-4o"},
    },
    "plan_defaults": {"free": "fast", "pro": "balanced", "team": "premium", "enterprise": "premium"},
}


def load_ai_model_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load provider/model routing config, falling back to built-in defaults."""
    path = config_path or _CONFIG_PATH
    config = copy.deepcopy(_DEFAULT_CONFIG)
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Unable to load AI model config %s: %s", path, exc)
        return config

    if isinstance(raw.get("providers"), dict):
        config["providers"].update(raw["providers"])
    if isinstance(raw.get("tier_strategy"), dict):
        config["tier_strategy"].update(raw["tier_strategy"])
    if isinstance(raw.get("plan_defaults"), dict):
        config["plan_defaults"].update(raw["plan_defaults"])
    return config
