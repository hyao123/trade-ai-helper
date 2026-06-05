"""Tests for sanitized AI provider error handling."""
from __future__ import annotations

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
_mock_st.secrets = {}
sys.modules["streamlit"] = _mock_st

_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv


def test_generic_ai_error_does_not_expose_exception_text():
    from utils.ai_client import _handle_api_error

    secret_detail = "sk-live-secret-token internal.example.local"
    message = _handle_api_error(RuntimeError(secret_detail))

    assert "AI 服务暂时不可用" in message
    assert "错误码" in message
    assert secret_detail not in message
    assert "RuntimeError" not in message
    assert "internal.example.local" not in message


def test_ai_error_code_is_stable_for_same_error():
    from utils.ai_client import _handle_api_error

    msg1 = _handle_api_error(RuntimeError("same provider failure"))
    msg2 = _handle_api_error(RuntimeError("same provider failure"))

    assert msg1 == msg2
    assert "same provider failure" not in msg1


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS: {name}")
