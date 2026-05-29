"""Tests for deployment-probe entrypoints exported by app.py."""
from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def _load_app_module(module_name: str = "app_entrypoint_probe"):
    spec = importlib.util.spec_from_file_location(module_name, APP_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_app_exports_probe_entrypoints_without_importing_streamlit(monkeypatch):
    """Generic app probes should import app.py without starting Streamlit."""
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "streamlit" or name.startswith("streamlit."):
            raise AssertionError("app.py should not import Streamlit during probe import")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module = _load_app_module()

    assert module.app is module.application
    assert callable(module.application)
    assert callable(module.handler)


def test_wsgi_and_serverless_probe_responses():
    module = _load_app_module("app_entrypoint_probe_response")
    start_calls = []

    body = module.application({}, lambda status, headers: start_calls.append((status, headers)))

    assert start_calls == [("200 OK", [("Content-Type", "text/plain; charset=utf-8")])]
    assert b"streamlit run app.py" in b"".join(body)

    response = module.handler()
    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "text/plain; charset=utf-8"
    assert "streamlit run app.py" in response["body"]
