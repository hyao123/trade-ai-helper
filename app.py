"""Probe-safe Streamlit entrypoint for AI-Trade Pro."""
from __future__ import annotations

PROBE_BODY = "AI-Trade Pro Streamlit app. Start with: streamlit run app.py"


def application(environ, start_response):
    """Minimal WSGI fallback for deployment probes."""
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [PROBE_BODY.encode("utf-8")]


def handler(event=None, context=None):
    """Minimal serverless-style fallback for app export probes."""
    return {"statusCode": 200, "headers": {"Content-Type": "text/plain; charset=utf-8"}, "body": PROBE_BODY}


app = application

HOME_CSS = """
<style>
.home-hero{background:linear-gradient(135deg,#1e1b4b 0%,#312e81 35%,#6366f1 100%);padding:2.2rem;border-radius:20px;margin-bottom:1.2rem;color:white}.home-hero h1{font-size:2.1rem;margin:0 0 .5rem;font-weight:900}.home-hero p{color:#c7d2fe;margin:0}.section-label{font