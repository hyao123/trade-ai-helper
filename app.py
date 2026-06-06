"""Probe-safe Streamlit entrypoint for AI-Trade Pro."""
from __future__ import annotations

PROBE_BODY = "AI-Trade Pro Streamlit app. Start with: streamlit run app.py"


def application(environ, start_response):
    """Minimal WSGI fallback for deployment probes."""
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [PROBE_BODY.encode("utf-