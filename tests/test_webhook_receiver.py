"""Tests for the minimal WSGI Stripe webhook receiver (webhook_receiver.py)."""
from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import webhook_receiver as wr


def _env(method="POST", path="/api/stripe/webhook", body=b"", sig="sig_abc"):
    headers = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_STRIPE_SIGNATURE": sig,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    return headers


def _run(environ):
    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    chunks = wr.application(environ, _start_response)
    captured["body"] = b"".join(chunks).decode("utf-8")
    return captured


def test_health_get_returns_ok():
    out = _run(_env(method="GET", path="/healthz"))
    assert out["status"] == wr._STATUS_OK
    assert out["body"] == "ok"


def test_unknown_path_returns_404():
    out = _run(_env(method="GET", path="/nope"))
    assert out["status"] == wr._STATUS_NOT_FOUND


def test_non_post_webhook_returns_405():
    out = _run(_env(method="GET", path=wr.WEBHOOK_PATH))
    assert out["status"] == wr._STATUS_METHOD


def test_missing_signature_returns_400():
    env = _env(body=b"{}")
    env["HTTP_STRIPE_SIGNATURE"] = ""
    out = _run(env)
    assert out["status"] == wr._STATUS_BAD_REQUEST


def test_successful_verification_returns_200():
    with patch("webhook_receiver.verify_and_process", return_value=(True, "processed")):
        out = _run(_env(body=b'{"type":"checkout.session.completed"}', sig="sig_valid"))
    assert out["status"] == wr._STATUS_OK
    assert "processed" in out["body"]


def test_failed_verification_returns_400_and_no_200():
    with patch("webhook_receiver.verify_and_process", return_value=(False, "Invalid signature")):
        out = _run(_env(body=b"{}", sig="sig_bad"))
    assert out["status"] == wr._STATUS_BAD_REQUEST
    assert "Invalid signature" in out["body"]


def test_verify_and_process_called_with_payload_and_signature():
    with patch("webhook_receiver.verify_and_process", return_value=(True, "ok")) as mocked:
        _run(_env(body=b'{"a":1}', sig="my_sig"))
    mocked.assert_called_once_with(b'{"a":1}', "my_sig")
