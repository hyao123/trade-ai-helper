"""Tests for product-grade AI config and persisted API counters."""
from __future__ import annotations

import importlib
import json
import time
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_ai_model_config_loads_external_overrides(ws_tmp):
    from config.ai_models import load_ai_model_config

    config_path = ws_tmp / "ai_models.json"
    config_path.write_text(
        json.dumps({
            "providers": {
                "customfast": {
                    "base_url": "https://example.test/v1",
                    "key_env": "CUSTOMFAST_API_KEY",
                    "models": {"fast-model": "fast-model"},
                    "default_model": "fast-model",
                    "cost_per_1k_tokens": 0.0,
                }
            },
            "tier_strategy": {"fast": {"provider": "customfast", "model": "fast-model"}},
            "plan_defaults": {"free": "fast"},
        }),
        encoding="utf-8",
    )

    config = load_ai_model_config(config_path)

    assert config["providers"]["customfast"]["default_model"] == "fast-model"
    assert config["tier_strategy"]["fast"]["provider"] == "customfast"
    assert config["plan_defaults"]["free"] == "fast"


def test_api_key_rate_counters_persist_to_storage(ws_tmp):
    import utils.api_keys as api_keys

    api_keys = importlib.reload(api_keys)
    metadata = {"key_id": "persisted-key", "tier": "team"}

    with patch("utils.storage.get_data_dir", return_value=ws_tmp):
        api_keys.record_api_usage(metadata)
        counters_file = ws_tmp / "api_rate_counters.json"
        assert counters_file.exists()
        persisted = json.loads(counters_file.read_text(encoding="utf-8"))
        assert persisted["persisted-key"]

        api_keys = importlib.reload(api_keys)
        ok, msg = api_keys.check_api_rate_limit(metadata)
        assert ok is True
        assert msg == "OK"
        persisted_after_check = json.loads(counters_file.read_text(encoding="utf-8"))
        assert "persisted-key" in persisted_after_check


def test_ai_client_rate_limit_slots_persist_and_reload(ws_tmp):
    import utils.ai_client as ai_client

    ai_client = importlib.reload(ai_client)
    user_id = "persisted-user"
    with patch("utils.storage.get_data_dir", return_value=ws_tmp):
        ai_client._call_times.clear()
        allowed, remaining = ai_client._rate_limit_check(user_id)
        assert allowed is True
        assert remaining == ai_client.RATE_LIMIT_MAX_CALLS - 1
        assert (ws_tmp / "ai_rate_limits.json").exists()

        ai_client._call_times.clear()
        assert ai_client.get_rate_limit_remaining(user_id) == ai_client.RATE_LIMIT_MAX_CALLS - 1

        old_slot = time.time() - ai_client.RATE_LIMIT_WINDOW - 10
        (ws_tmp / "ai_rate_limits.json").write_text(json.dumps({user_id: [old_slot]}), encoding="utf-8")
        ai_client._call_times.clear()
        assert ai_client.get_rate_limit_remaining(user_id) == ai_client.RATE_LIMIT_MAX_CALLS
