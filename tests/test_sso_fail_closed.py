"""SSO security tests.

SSO authentication is intentionally FAIL-CLOSED until signature-validating SAML/OIDC
support ships. These guards assert that neither auth path can ever succeed, so a
future re-enable cannot silently reintroduce the auth bypass.
"""
from __future__ import annotations


def test_saml_response_never_authenticates():
    """A SAML response — even a well-formed one — must never yield (True, user)."""
    from utils.sso import process_saml_response

    # A plausible-looking (but unsigned) SAML assertion blob.
    fake_b64 = "PHNhbWxwOlJlc3BvbnNlPjxBbGllbnQ+PDA1Ok5hbWVJRD5hZ2luYm9zdEBleGFtcGxlLmNvbTwvbmFtZUlEPS8+PC9BbGllbnQ+PC9zYW1scDpSZXNwb25zZT4="
    ok, result = process_saml_response(fake_b64, team_id="t1")
    assert ok is False
    assert isinstance(result, str)  # an error message, not user info


def test_oidc_callback_never_authenticates():
    """An OIDC callback must never yield (True, user), fail-closed."""
    from utils.sso import process_oidc_callback

    ok, result = process_oidc_callback("some-code", state="s", team_id="t1")
    assert ok is False
    assert isinstance(result, str)


def test_empty_saml_response_is_rejected_not_raising():
    """An empty/garbage SAML blob must fail closed with an error message."""
    from utils.sso import process_saml_response

    ok, result = process_saml_response("not-base64-!!!", team_id="t1")
    assert ok is False
    assert isinstance(result, str)
