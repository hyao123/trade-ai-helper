"""Probe-safe Streamlit entrypoint for AI-Trade Pro.

The module intentionally avoids importing Streamlit at import time so generic
platform probes can import ``app.py`` and find lightweight WSGI/serverless
fallbacks. The actual Streamlit UI is rendered only from ``main()``.
"""

from __future__ import annotations

PROBE_BODY = "AI-Trade Pro Streamlit app. Start with: streamlit run app.py"


def application(environ, start_response):
    """Minimal W