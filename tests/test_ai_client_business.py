"""Smoke guards for the AI-client business functions and the agent tool registry.

These tests verify that every function imported by pages from utils.ai_client,
and every ``module.function`` referenced in ``AGENT_TOOLS``, actually exists and
is importable. A missing wrapper previously crashed pages 5/17/20/26/27/28 and
the agent tool dispatch (test_tier2 only grepped page source text and missed it).
"""
from __future__ import annotations

import importlib
from unittest.mock import patch


# Functions that pages import from utils.ai_client (each must exist).
PAGE_IMPORTED = [
    "generate_email",
    "reply_inquiry",
    "product_intro",
    "followup_email",
    "generate_followup",
    "generate_smart_quote",
    "lookup_hs_code",
    "recognize_email_intent",
    "analyze_customer_profile",
]


def _resolve(module_name: str, func_name: str) -> bool:
    module = importlib.import_module(module_name)
    return hasattr(module, func_name) and callable(getattr(module, func_name))


def test_business_functions_exist_in_ai_client():
    module = importlib.import_module("utils.ai_client")
    missing = [name for name in PAGE_IMPORTED if not callable(getattr(module, name, None))]
    assert missing == [], f"utils.ai_client is missing: {missing}"


def test_agent_tool_registry_references_exist():
    from utils.ai_agent import AGENT_TOOLS

    bad = []
    for tool_id, cfg in AGENT_TOOLS.items():
        module = cfg.get("module")
        func = cfg.get("function")
        if not module or not func:
            bad.append(f"{tool_id}: missing module/function")
            continue
        try:
            if not _resolve(module, func):
                bad.append(f"{tool_id}: {module}.{func} not found")
        except Exception as exc:  # pragma: no cover - defensive
            bad.append(f"{tool_id}: {module}.{func} import error: {exc}")
    assert bad == [], f"AGENT_TOOLS references broken:\n" + "\n".join(bad)


def test_smart_quote_wrapper_signature_matches_pages():
    """pages/17 calls generate_smart_quote with keyword args matching the prompt builder."""
    from utils.ai_client import generate_smart_quote
    import inspect

    params = inspect.signature(generate_smart_quote).parameters
    for expected in ("product", "target_market", "order_quantity", "production_cost", "trade_term"):
        assert expected in params, f"generate_smart_quote missing param {expected}"


def test_agent_tools_function_params_are_all_callable_kwargs():
    """Guard that every AGENT_TOOLS param name is accepted by its function."""
    from utils.ai_client import (
        analyze_customer_profile,
        generate_email,
        generate_followup,
        generate_smart_quote,
        lookup_hs_code,
        recognize_email_intent,
        reply_inquiry,
    )

    func_map = {
        "generate_email": generate_email,
        "generate_followup": generate_followup,
        "reply_inquiry": reply_inquiry,
        "generate_smart_quote": generate_smart_quote,
        "lookup_hs_code": lookup_hs_code,
        "analyze_customer_profile": analyze_customer_profile,
        "recognize_email_intent": recognize_email_intent,
    }
    from utils.ai_agent import AGENT_TOOLS

    import inspect

    for tool_id, cfg in AGENT_TOOLS.items():
        func = func_map.get(cfg["function"])
        if func is None:
            continue
        sig = inspect.signature(func).parameters
        for param in cfg.get("params", []):
            assert param in sig, f"AGENT_TOOLS[{tool_id}] param {param!r} not accepted by {cfg['function']}"


def test_agent_plan_rejects_llm_error_string():
    """._parse_plan must not turn a ⚠️ error string into a cold-email plan."""
    from utils.ai_agent import Agent

    agent = Agent(user_id="test_user")
    plan = agent._parse_plan(
        "send follow-ups to all overdue customers",
        "⚠️ 调用频率超限，每 60 分钟最多 20 次，请稍后再试。",
    )
    assert len(plan.tasks) == 0, "error response must yield a plan with no tasks"


def test_agent_plan_rejects_unparseable_json():
    """._parse_plan must not fabricate a tool call for unparseable AI output."""
    from utils.ai_agent import Agent

    agent = Agent(user_id="test_user")
    plan = agent._parse_plan("do something", "This is not JSON at all {{{")
    assert len(plan.tasks) == 0


def test_stream_llm_does_not_double_consume_on_midstream_gateway_failure():
    """If the gateway stream emits tokens then raises, stream_llm must not
    fall through to the direct path and consume a second rate-limit slot."""
    import utils.ai_client as ac

    def _raising_stream(*args, **kwargs):
        yield "partial"
        raise RuntimeError("boom")

    class _Gw:
        def stream(self, *a, **k):
            return _raising_stream()

    consumed = []

    def _fake_consume(uid):
        consumed.append(uid)

    def _fake_rollback():
        pass

    with patch.object(ac, "_should_use_gateway", return_value=True), \
         patch("utils.ai_gateway.get_gateway", return_value=_Gw()), \
         patch.object(ac, "_rate_limit_consume", side_effect=_fake_consume), \
         patch.object(ac, "_rate_limit_rollback", side_effect=_fake_rollback), \
         patch.object(ac, "_rollback_tier_usage", side_effect=_fake_rollback), \
         patch("utils.ai_client._check_preconditions", return_value=None), \
         patch("utils.ai_client._get_model", return_value="meta/test-model"), \
         patch.object(ac, "_get_client", return_value=object()):
        out = list(ac.stream_llm("hi", user_id="test_user"))

    # At most one slot consumed; the direct NVIDIA path must NOT run.
    assert len(consumed) <= 1, f"expected <=1 slot consumption, got {len(consumed)}"
    # Our fake raise outputs "partial" then fails cleanly rather than re-streaming.
    assert out and out[0] == "partial"
