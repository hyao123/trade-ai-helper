"""
webhook_receiver.py
-------------------
Minimal WSGI receiver for Stripe subscription webhooks.

Why this exists
---------------
The app upgrades tiers via one-time Stripe Checkout completed on the return URL
(``utils.payment.complete_upgrade_from_query``), but subscription lifecycle events
(cancel → downgrade to free, payment_failed) are handled by
``utils.stripe_webhook.verify_and_process`` — which previously had no HTTP entry
point, so those lifecycle hooks never fired.

This module exposes ``verify_and_process`` behind a standard WSGI app with proper
HTTP status codes, so Stripe's webhook delivery retries on failure. It depends only
on the Python stdlib (``wsgiref``), so it can run:

  - Standalone:      python webhook_receiver.py            # served on PORT (default 8787)
  - Under gunicorn:  gunicorn webhook_receiver:application --bind 0.0.0.0:8787
  - Under waitress:  waitress-serve --port=8787 webhook_receiver:application

Deploy it as a separate small process/function. Point your Stripe webhook URL at
``{APP_BASE_URL}/api/stripe/webhook`` and set the ``STRIPE_WEBHOOK_SECRET`` webook
signing secret. Do NOT run it on the same worker as the Streamlit app.
"""
from __future__ import annotations

import os
from typing import Callable

# Reuse the tested webhook verification/processing logic.
from utils.stripe_webhook import verify_and_process

_STATUS_OK = "200 OK"
_STATUS_BAD_REQUEST = "400 Bad Request"
_STATUS_FAIL = "500 Internal Server Error"
_STATUS_NOT_FOUND = "404 Not Found"
_STATUS_METHOD = "405 Method Not Allowed"

WEBHOOK_PATH = "/api/stripe/webhook"
HEALTH_PATH = "/healthz"
_CT_JSON = ("Content-Type", "application/json; charset=utf-8")
_CT_TEXT = ("Content-Type", "text/plain; charset=utf-8")


def _read_body(environ: dict) -> bytes:
    """Read the full request body from ``environ`` (respecting Content-Length)."""
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        content_length = 0
    if content_length <= 0:
        return b""
    return environ.get("wsgi.input", "").read(content_length)


def application(environ: dict, start_response: Callable) -> list[bytes]:
    """
    WSGI application handling Stripe webhook POSTs.

    Routes:
      POST /api/stripe/webhook  -> verify + process; 200 ok / 4xx-5xx retry
      GET  /healthz             -> liveness probe
    """
    path = environ.get("PATH_INFO", "") or "/"
    method = (environ.get("REQUEST_METHOD") or "GET").upper()

    if method == "GET" and path == HEALTH_PATH:
        start_response(_STATUS_OK, [_CT_TEXT])
        return [b"ok"]

    if path != WEBHOOK_PATH:
        start_response(_STATUS_NOT_FOUND, [_CT_TEXT])
        return [b"Not found"]

    if method != "POST":
        start_response(
            _STATUS_METHOD,
            [("Content-Type", "text/plain; charset=utf-8"), ("Allow", "POST")],
        )
        return [b"Method not allowed"]

    payload = _read_body(environ)
    signature = environ.get("HTTP_STRIPE_SIGNATURE", "")

    if not signature:
        start_response(_STATUS_BAD_REQUEST, [_CT_TEXT])
        return [b"Missing Stripe-Signature header"]

    try:
        success, message = verify_and_process(payload, signature)
    except Exception as exc:
        start_response(_STATUS_FAIL, [_CT_TEXT])
        return [f"Webhook processing failed: {exc}".encode("utf-8")]

    if success:
        start_response(_STATUS_OK, [_CT_JSON])
        return [("{\"ok\": true, \"message\": \"%s\"}" % _json_escape(message)).encode("utf-8")]

    # Failure: signature/parse errors (permanent) return 400; handler errors return 500
    # Check if message indicates signature or parse failure
    if "signature" in message.lower() or "parse" in message.lower():
        start_response(_STATUS_BAD_REQUEST, [_CT_JSON])
    else:
        start_response(_STATUS_FAIL, [_CT_JSON])
    return [("{\"ok\": false, \"message\": \"%s\"}" % _json_escape(message)).encode("utf-8")]


def _json_escape(value: object) -> str:
    """Minimal JSON-safety for the response message (escape quotes/backslashes)."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def main() -> None:
    """Serve the receiver as a standalone process (default port 8787)."""
    from wsgiref.simple_server import make_server

    port = int(os.environ.get("PORT", "8787"))
    host = os.environ.get("HOST", "0.0.0.0")
    httpd = make_server(host, port, application)
    print(f"Stripe webhook receiver listening on http://{host}:{port}{WEBHOOK_PATH}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping webhook receiver.")
        httpd.server_close()


if __name__ == "__main__":
    main()
