"""Guards for the shipped AI model config (config/ai_models.json).

These tests intentionally avoid system temp dirs (tempfile/TemporaryDirectory)
so they run anywhere, including sandboxed environments where writing outside
the workspace is denied. The two tests that need to write a config file use a
unique file under the gitignored ``data/`` directory and clean up after
themselves.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from config.ai_models import (
    _CONFIG_PATH,
    _FALLBACK_CONFIG,
    load_ai_model_config,
    validate_config,
)

_WORKSPACE_TMP = Path(__file__).resolve().parent.parent / "data" / "_test_tmp"


def _unique_workspace_file(name: str) -> Path:
    """Return a unique writable path under the gitignored data/ directory."""
    _WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
    return _WORKSPACE_TMP / f"{uuid.uuid4().hex[:12]}_{name}"


def test_shipped_ai_models_json_is_valid():
    """The shipped ai_models.json must be a complete, usable config."""
    config = load_ai_model_config()
    problems = validate_config(config)
    assert problems == [], f"shipped ai_models.json is invalid: {problems}"


def test_shipped_config_keeps_required_tiers_and_plans():
    """fast/balanced/premium tiers and all plan defaults must exist."""
    config = load_ai_model_config()
    for tier in ("fast", "balanced", "premium"):
        assert tier in config["tier_strategy"], f"missing tier {tier}"
    for plan in ("free", "pro", "team", "enterprise"):
        assert plan in config["plan_defaults"], f"missing plan default {plan}"


def test_external_partial_config_overrides_not_required_fields():
    """A partial external config replaces providers but stays normalized."""
    path = _unique_workspace_file("ai_models.json")
    path.write_text(json.dumps({
        "providers": {
            "customfast": {
                "base_url": "https://example.test/v1",
                "key_env": "CUSTOMFAST_API_KEY",
                "models": {"fast-model": "fast-model"},
                "default_model": "fast-model",
            }
        },
        "tier_strategy": {"fast": {"provider": "customfast", "model": "fast-model"}},
        "plan_defaults": {"free": "fast"},
    }), encoding="utf-8")

    try:
        config = load_ai_model_config(path)
        assert config["providers"]["customfast"]["default_model"] == "fast-model"
        # Optional field defaulted in, so downstream cost lookups never KeyError.
        assert config["providers"]["customfast"]["cost_per_1k_tokens"] == 0.0
        assert config["tier_strategy"]["fast"]["provider"] == "customfast"
        assert config["plan_defaults"]["free"] == "fast"
    finally:
        path.unlink(missing_ok=True)


def test_missing_config_falls_back_to_minimal_nvidia():
    """A missing config file must not crash; fallback keeps NVIDIA usable."""
    missing = _unique_workspace_file("does_not_exist.json")
    config = load_ai_model_config(missing)
    assert config["providers"]["nvidia"]["key_env"] == "NVIDIA_API_KEY"
    assert "fast" in config["tier_strategy"]
    assert config["plan_defaults"]["free"] == "fast"
    assert validate_config(config) == []


def test_invalid_provider_entries_are_skipped():
    """Broken provider entries must be dropped, not kept as KeyError bombs."""
    path = _unique_workspace_file("ai_models_broken.json")
    path.write_text(json.dumps({
        "providers": {
            "good": {
                "base_url": "https://example.test/v1",
                "key_env": "GOOD_API_KEY",
                "models": {"m": "m"},
                "default_model": "m",
            },
            "not_an_object": "oops",
            "missing_fields": {"base_url": "https://example.test/v1"},
        },
        "tier_strategy": {"fast": {"provider": "good", "model": "m"}},
        "plan_defaults": {"free": "fast"},
    }), encoding="utf-8")

    try:
        config = load_ai_model_config(path)
        assert set(config["providers"].keys()) == {"good"}
    finally:
        path.unlink(missing_ok=True)


def test_fallback_config_is_self_consistent():
    """The built-in fallback must itself pass validation."""
    assert validate_config(_FALLBACK_CONFIG) == []


def test_validate_config_detects_unknown_tier_model_key():
    """tier_strategy[tier].model must be a key of that provider's models."""
    path = _unique_workspace_file("ai_models_badtier.json")
    path.write_text(json.dumps({
        "providers": {
            "nvidia": {
                "base_url": "https://example.test/v1",
                "key_env": "NVIDIA_API_KEY",
                "models": {"llama-3.3-70b": "meta/llama-3.3-70b-instruct"},
                "default_model": "llama-3.3-70b",
            }
        },
        "tier_strategy": {
            "fast": {"provider": "nvidia", "model": "no-such-model"},  # not in models
            "balanced": {"provider": "nvidia", "model": "llama-3.3-70b"},
            "premium": {"provider": "nvidia", "model": "llama-3.3-70b"},
        },
        "plan_defaults": {"free": "fast", "pro": "balanced", "team": "premium", "enterprise": "premium"},
    }), encoding="utf-8")

    try:
        config = load_ai_model_config(path)
        problems = validate_config(config)
        assert any("tier_strategy['fast'].model" in p for p in problems), problems
    finally:
        path.unlink(missing_ok=True)


def test_config_path_points_to_shipped_file():
    """Regression guard: the loader must default to the repo's own JSON."""
    assert _CONFIG_PATH.exists(), "config/ai_models.json is missing"


def test_tier_config_and_plan_defaults_keys_align():
    """Every plan in pricing.TIER_CONFIG must have a route in ai_models plan_defaults."""
    from utils.pricing import TIER_CONFIG
    config = load_ai_model_config()
    plan_defaults = config.get("plan_defaults") or {}
    missing = [p for p in TIER_CONFIG.keys() if p not in plan_defaults]
    assert missing == [], (
        f"TIER_CONFIG keys without an ai_models plan_default route: {missing}; "
        "these users would fall back to free-tier limits while being routed to a higher model tier"
    )
