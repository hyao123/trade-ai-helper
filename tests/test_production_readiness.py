"""Tests for commercial deployment readiness checks."""
from __future__ import annotations

from utils.production_readiness import run_readiness_checks, summarize_readiness


def _secret_getter(values: dict[str, str]):
    def getter(key: str, default: str = "") -> str:
        return values.get(key, default)

    return getter


def test_readiness_fails_for_public_auth_bypass_and_ephemeral_storage():
    checks = run_readiness_checks(
        secret_getter=_secret_getter({
            "AUTH_REQUIRED": "false",
            "NVIDIA_API_KEY": "nvapi-test",
        })
    )
    by_id = {check.id: check for check in checks}

    assert by_id["auth_required"].status == "fail"
    assert by_id["persistence_backend"].status == "fail"
    assert summarize_readiness(checks)["ready"] is False


def test_readiness_passes_core_postgres_stripe_and_email_configuration():
    checks = run_readiness_checks(
        secret_getter=_secret_getter({
            "AUTH_REQUIRED": "true",
            "DATABASE_URL": "postgres://user:pass@example.com/db",
            "OPENAI_API_KEY": "sk-test",
            "STRIPE_SECRET_KEY": "sk_live_test",
            "STRIPE_PRICE_ID_PRO": "price_pro",
            "STRIPE_WEBHOOK_SECRET": "whsec_test",
            "APP_BASE_URL": "https://trade.example.com",
            "SENDGRID_API_KEY": "SG.test",
        })
    )
    summary = summarize_readiness(checks)
    by_id = {check.id: check for check in checks}

    assert by_id["account_security_controls"].status == "pass"
    assert summary["failed"] == 0
    assert summary["ready"] is True


def test_readiness_flags_partially_configured_stripe_as_critical():
    checks = run_readiness_checks(
        secret_getter=_secret_getter({
            "DATABASE_URL": "postgres://user:pass@example.com/db",
            "NVIDIA_API_KEY": "nvapi-test",
            "STRIPE_SECRET_KEY": "sk_live_test",
            "STRIPE_PRICE_ID_PRO": "price_pro",
        })
    )
    by_id = {check.id: check for check in checks}

    assert by_id["stripe_billing"].status == "fail"
    assert "STRIPE_WEBHOOK_SECRET" in by_id["stripe_billing"].detail
    assert "APP_BASE_URL" in by_id["stripe_billing"].detail


def test_sqlite_and_missing_transactional_email_are_warnings_not_failures():
    checks = run_readiness_checks(
        secret_getter=_secret_getter({
            "SQLITE_DB_PATH": "trade_ai_helper.sqlite3",
            "DEEPSEEK_API_KEY": "sk-test",
        })
    )
    by_id = {check.id: check for check in checks}
    summary = summarize_readiness(checks)

    assert by_id["persistence_backend"].status == "warn"
    assert by_id["transactional_email"].status == "warn"
    assert by_id["account_security_controls"].status == "pass"
    assert summary["failed"] == 0
    assert summary["ready"] is True


def test_readiness_includes_account_security_controls():
    checks = run_readiness_checks(
        secret_getter=_secret_getter({
            "DATABASE_URL": "postgres://user:pass@example.com/db",
            "NVIDIA_API_KEY": "nvapi-test",
        })
    )
    by_id = {check.id: check for check in checks}

    assert "account_security_controls" in by_id
    assert by_id["account_security_controls"].status == "pass"
    assert "hashed tokens" in by_id["account_security_controls"].detail
