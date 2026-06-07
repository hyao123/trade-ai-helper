"""Probe-safe Streamlit entrypoint for AI-Trade Pro."""
from __future__ import annotations

PROBE_BODY = "AI-Trade Pro Streamlit app. Start with: streamlit run app.py"


def application(environ, start_response):
    """Minimal WSGI fallback for deployment probes."""
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [PROBE_BODY.encode("utf-8")]


def handler(event=None, context=None):
    """Minimal serverless-style fallback for app export probes."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
        "body": PROBE_BODY,
    }


app = application