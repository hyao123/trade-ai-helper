"""Production readiness checks for commercial deployments.

The checks are intentionally pure and dependency-light so they can be reused
from tests, deployment scripts, Streamlit admin pages, or CI jobs.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from utils.secrets import get_secret

_FALSE_VALUES = {"0", "false", "no", "off"}
_AI_PROVIDER_KEYS = ("NVIDIA_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY")


@dataclass(frozen=True)
class ReadinessCheck:
    """One production readiness finding."""

    id: str
    title: str
    status: str
    severity: str
    detail: str
    recommendation: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "detail": self.detail,
            "recommendation": self.recommendation,
        }


def _is_false(value: str) -> bool:
    return str(value or "").strip().lower() in _FALSE_VALUES


def _has_any(secret_getter: Callable[[str, str], str], keys: tuple[str, ...]) -> bool:
    return any(bool(secret_getter(key, "")) for key in keys)


def _check_auth(secret_getter: Callable[[str, str], str]) -> ReadinessCheck:
    auth_required = secret_getter("AUTH_REQUIRED", "true")
    if _is_false(auth_required):
        return ReadinessCheck(
            id="auth_required",
            title="Authentication gate",
            status="fail",
            severity="critical",
            detail="AUTH_REQUIRED is disabled, so public visitors can bypass login.",
            recommendation="Keep AUTH_REQUIRED unset or set it to true for public/commercial deployments.",
        )
    return ReadinessCheck(
        id="auth_required",
        title="Authentication gate",
        status="pass",
        severity="info",
        detail="Authentication is required by default.",
        recommendation="Keep self-service registration enabled and protect admin fallback credentials.",
    )


def _check_persistence(secret_getter: Callable[[str, str], str]) -> ReadinessCheck:
    database_url = secret_getter("DATABASE_URL", "")
    sqlite_path = secret_getter("SQLITE_DB_PATH", "")
    if database_url.startswith("postgres"):
        return ReadinessCheck(
            id="persistence_backend",
            title="Durable persistence",
            status="pass",
            severity="info",
            detail="PostgreSQL DATABASE_URL is configured.",
            recommendation="Monitor backups, migrations, and connection limits for multi-instance deployments.",
        )
    if database_url.startswith("sqlite:") or sqlite_path:
        return ReadinessCheck(
            id="persistence_backend",
            title="Durable persistence",
            status="warn",
            severity="medium",
            detail="SQLite persistence is configured; this is suitable for a single app instance.",
            recommendation="Use PostgreSQL before multi-instance commercial deployment or strict durability needs.",
        )
    return ReadinessCheck(
        id="persistence_backend",
        title="Durable persistence",
        status="fail",
        severity="critical",
        detail="No DATABASE_URL or SQLITE_DB_PATH is configured; hosted file storage may be ephemeral.",
        recommendation="Configure PostgreSQL for production or SQLite for a single-instance demo.",
    )


def _check_ai_provider(secret_getter: Callable[[str, str], str]) -> ReadinessCheck:
    if _has_any(secret_getter, _AI_PROVIDER_KEYS):
        return ReadinessCheck(
            id="ai_provider",
            title="AI provider",
            status="pass",
            severity="info",
            detail="At least one built-in AI provider API key is configured.",
            recommendation="Configure fallback providers and monitor token/cost usage for paid plans.",
        )
    return ReadinessCheck(
        id="ai_provider",
        title="AI provider",
        status="fail",
        severity="critical",
        detail="No NVIDIA, OpenAI, or DeepSeek API key is configured.",
        recommendation="Configure at least one AI provider key before public launch.",
    )


def _check_payment(secret_getter: Callable[[str, str], str]) -> ReadinessCheck:
    secret_key = secret_getter("STRIPE_SECRET_KEY", "")
    has_price = _has_any(secret_getter, ("STRIPE_PRICE_ID_PRO", "STRIPE_PRICE_ID_ENTERPRISE", "STRIPE_PRICE_ID_TEAM"))
    webhook_secret = secret_getter("STRIPE_WEBHOOK_SECRET", "")
    app_base_url = secret_getter("APP_BASE_URL", "")

    if not secret_key and not has_price:
        return ReadinessCheck(
            id="stripe_billing",
            title="Stripe billing",
            status="warn",
            severity="medium",
            detail="Stripe billing is not configured.",
            recommendation="Configure Stripe keys before enabling paid upgrades in the product UI.",
        )
    missing = []
    if not secret_key:
        missing.append("STRIPE_SECRET_KEY")
    if not has_price:
        missing.append("Stripe price ID")
    if not webhook_secret:
        missing.append("STRIPE_WEBHOOK_SECRET")
    if not app_base_url:
        missing.append("APP_BASE_URL")
    if missing:
        return ReadinessCheck(
            id="stripe_billing",
            title="Stripe billing",
            status="fail",
            severity="critical",
            detail=f"Stripe billing is partially configured but missing: {', '.join(missing)}.",
            recommendation="Complete Stripe checkout and webhook secrets before accepting paid upgrades.",
        )
    return ReadinessCheck(
        id="stripe_billing",
        title="Stripe billing",
        status="pass",
        severity="info",
        detail="Stripe checkout, price, webhook, and app base URL settings are present.",
        recommendation="Verify webhook delivery in Stripe Dashboard after deployment.",
    )


def _check_email(secret_getter: Callable[[str, str], str]) -> ReadinessCheck:
    has_sendgrid = bool(secret_getter("SENDGRID_API_KEY", ""))
    has_smtp = all(
        bool(secret_getter(key, ""))
        for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_EMAIL")
    )
    if has_sendgrid or has_smtp:
        return ReadinessCheck(
            id="transactional_email",
            title="Transactional email",
            status="pass",
            severity="info",
            detail="Transactional email credentials are configured.",
            recommendation="Send a real verification/reset email from the deployed environment.",
        )
    return ReadinessCheck(
        id="transactional_email",
        title="Transactional email",
        status="warn",
        severity="medium",
        detail="No SendGrid or SMTP credentials are configured.",
        recommendation="Configure transactional email for verification, password reset, and billing notifications.",
    )


def _check_account_security_controls() -> ReadinessCheck:
    try:
        from utils.security_audit import AUDIT_EVENT_NAME, detect_audit_risks
        from utils.user_auth import (
            _EMAIL_VERIFICATION_REQUEST_LIMIT,
            _LOGIN_FAILURE_LIMIT,
            _PASSWORD_RESET_REQUEST_LIMIT,
            _TOKEN_HASH_ALGORITHM,
        )
    except Exception as exc:
        return ReadinessCheck(
            id="account_security_controls",
            title="Account security controls",
            status="fail",
            severity="critical",
            detail=f"Account security controls could not be imported: {exc}",
            recommendation="Fix authentication/security modules before public launch.",
        )

    controls_enabled = (
        _LOGIN_FAILURE_LIMIT > 0
        and _PASSWORD_RESET_REQUEST_LIMIT > 0
        and _EMAIL_VERIFICATION_REQUEST_LIMIT > 0
        and _TOKEN_HASH_ALGORITHM == "sha256"
        and AUDIT_EVENT_NAME == "security_audit"
        and callable(detect_audit_risks)
    )
    if controls_enabled:
        return ReadinessCheck(
            id="account_security_controls",
            title="Account security controls",
            status="pass",
            severity="info",
            detail="Login lockout, recovery email throttling, hashed tokens, and security audit risk detection are enabled.",
            recommendation="Review security audit events after launch and tune thresholds if legitimate users are impacted.",
        )
    return ReadinessCheck(
        id="account_security_controls",
        title="Account security controls",
        status="fail",
        severity="critical",
        detail="One or more account security controls are disabled or misconfigured.",
        recommendation="Keep login lockout, recovery throttling, hashed account tokens, and audit risk detection enabled.",
    )


def _check_auto_login(secret_getter: Callable[[str, str], str]) -> ReadinessCheck:
    """Verify AUTO_LOGIN is not enabled in production."""
    auto_login = secret_getter("AUTO_LOGIN", "")
    # Check if AUTO_LOGIN is set to a truthy enabled value
    if auto_login:
        normalized = str(auto_login).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return ReadinessCheck(
                id="auto_login",
                title="Auto-login bypass",
                status="critical",
                severity="critical",
                detail="AUTO_LOGIN is enabled, bypassing authentication for all users.",
                recommendation="Remove or set AUTO_LOGIN=0 in production. Use only for local development.",
            )
    return ReadinessCheck(
        id="auto_login",
        title="Auto-login bypass",
        status="pass",
        severity="info",
        detail="AUTO_LOGIN is disabled or not set.",
        recommendation="Keep AUTO_LOGIN unset in production deployments.",
    )


def run_readiness_checks(
    *,
    secret_getter: Callable[[str, str], str] = get_secret,
) -> list[ReadinessCheck]:
    """Run commercial deployment readiness checks."""
    return [
        _check_auth(secret_getter),
        _check_persistence(secret_getter),
        _check_ai_provider(secret_getter),
        _check_payment(secret_getter),
        _check_email(secret_getter),
        _check_account_security_controls(),
        _check_auto_login(secret_getter),
    ]


def summarize_readiness(checks: list[ReadinessCheck]) -> dict[str, int | bool]:
    """Return a compact summary useful for dashboards and CI gates."""
    failed = sum(1 for check in checks if check.status == "fail")
    warnings = sum(1 for check in checks if check.status == "warn")
    passed = sum(1 for check in checks if check.status == "pass")
    return {
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "ready": failed == 0,
    }
