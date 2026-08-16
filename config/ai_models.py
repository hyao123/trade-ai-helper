"""External AI provider/model configuration loader.

``ai_models.json`` (shipped in this directory) is the **single source of truth**
for provider routing. This module only:
  - loads that file,
  - normalizes missing optional fields so partial configs stay usable, and
  - falls back to a minimal built-in NVIDIA config if the file is missing.

There is intentionally no second copy of the full provider data in Python;
edit ``ai_models.json`` instead of this module to change providers/models.
``tests/test_ai_models_config.py`` validates the shipped file so it cannot
silently drift into an unusable state.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger("ai_models")

_CONFIG_PATH = Path(__file__).with_name("ai_models.json")

# Minimal boot fallback used ONLY when ai_models.json is missing or corrupt.
# Keep this small — it is not the maintenance source of truth.
_FALLBACK_CONFIG: dict[str, Any] = {
    "providers": {
        "nvidia": {
            "base_url": "https://integrate.api.nvidia.com/v1",
            "key_env": "NVIDIA_API_KEY",
            "models": {"llama-3.3-70b": "meta/llama-3.3-70b-instruct"},
            "default_model": "llama-3.3-70b",
            "cost_per_1k_tokens": 0.003,
        }
    },
    "tier_strategy": {
        "fast": {"provider": "nvidia", "model": "llama-3.3-70b"},
        "balanced": {"provider": "nvidia", "model": "llama-3.3-70b"},
        "premium": {"provider": "nvidia", "model": "llama-3.3-70b"},
    },
    "plan_defaults": {
        "free": "fast",
        "pro": "balanced",
        "team": "premium",
        "enterprise": "premium",
    },
}

# Optional per-provider fields filled in when a provider entry omits them.
# Required fields (base_url, key_env, models, default_model) must come from the
# config file; downstream code expects them to be present.
_PROVIDER_FIELD_DEFAULTS: dict[str, Any] = {
    "cost_per_1k_tokens": 0.0,
}

_REQUIRED_PROVIDER_FIELDS = ("base_url", "key_env", "models", "default_model")


def _normalize_provider(name: str, raw: Any) -> dict[str, Any]:
    """Return a provider dict with optional fields filled in; skip invalid ones."""
    if not isinstance(raw, dict):
        logger.warning("Ignoring non-object provider entry: %s", name)
        return {}
    provider = dict(_PROVIDER_FIELD_DEFAULTS)
    provider.update(raw)
    return provider


def _normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Fill optional fields so downstream code never KeyErrors on missing keys.

    Provider entries that are not objects or that miss required fields are
    skipped with a warning instead of being kept as broken dicts.
    """
    providers = config.get("providers")
    if not isinstance(providers, dict):
        providers = {}

    normalized: dict[str, Any] = {}
    for name, raw in providers.items():
        provider = _normalize_provider(name, raw)
        if provider and all(
            provider.get(field) not in (None, "", {}) for field in _REQUIRED_PROVIDER_FIELDS
        ):
            normalized[name] = provider
        else:
            logger.warning("Skipping invalid AI provider entry: %s", name)
    config["providers"] = normalized

    if not isinstance(config.get("tier_strategy"), dict):
        config["tier_strategy"] = {}
    if not isinstance(config.get("plan_defaults"), dict):
        config["plan_defaults"] = {}
    return config


def load_ai_model_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load provider/model routing config from ``ai_models.json``.

    Returns the JSON content with optional fields normalized. If the file is
    missing or unreadable, returns a minimal built-in fallback so the app can
    still boot (a warning is logged).
    """
    path = config_path or _CONFIG_PATH
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Unable to load AI model config %s: %s", path, exc)
        return copy.deepcopy(_normalize_config(_FALLBACK_CONFIG))

    if not isinstance(raw, dict):
        logger.warning("AI model config %s is not an object; using fallback", path)
        return copy.deepcopy(_normalize_config(_FALLBACK_CONFIG))

    return _normalize_config(raw)


def validate_config(config: dict[str, Any]) -> list[str]:
    """Return a list of problems in a config dict (empty when valid).

    Used by tests to guard the shipped ``ai_models.json`` from accidental
    drift into an unusable state.
    """
    problems: list[str] = []
    providers = config.get("providers") or {}
    if not isinstance(providers, dict) or not providers:
        problems.append("providers must be a non-empty object")

    for name, provider in (providers or {}).items():
        if not isinstance(provider, dict):
            problems.append(f"provider {name!r} must be an object")
            continue
        for field in _REQUIRED_PROVIDER_FIELDS:
            if field not in provider or provider[field] in (None, "", {}):
                problems.append(f"provider {name!r} is missing required field {field!r}")

    tier_strategy = config.get("tier_strategy") or {}
    for tier in ("fast", "balanced", "premium"):
        entry = tier_strategy.get(tier) or {}
        if entry.get("provider") not in (providers or {}):
            problems.append(f"tier_strategy[{tier!r}] references unknown provider")

    plan_defaults = config.get("plan_defaults") or {}
    for plan in ("free", "pro", "team", "enterprise"):
        if plan not in plan_defaults:
            problems.append(f"plan_defaults is missing plan {plan!r}")

    return problems
