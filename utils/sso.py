"""
utils/sso.py
------------
Enterprise Single Sign-On (SSO) support.

Supports:
  - SAML 2.0 (for enterprise IdPs: Okta, Azure AD, OneLogin)
  - OAuth2/OIDC (for Google Workspace, Microsoft Entra)

Flow (SAML):
  1. User clicks "Login with SSO" on login page
  2. App redirects to IdP's SSO URL with SAML AuthnRequest
  3. User authenticates at IdP
  4. IdP posts SAML Response back to our ACS URL
  5. We validate signature, extract user attributes
  6. Create/update local user account, establish session

Flow (OIDC):
  1. User clicks "Login with SSO"
  2. App redirects to IdP authorization endpoint
  3. User authenticates, IdP redirects back with code
  4. App exchanges code for tokens, fetches user info
  5. Create/update local user, establish session

Configuration (per-tenant):
  SSO_PROVIDER: 'saml' or 'oidc'
  SSO_ENTITY_ID: IdP entity ID (SAML)
  SSO_SSO_URL: IdP SSO endpoint
  SSO_CERTIFICATE: IdP signing certificate (X.509 PEM)
  SSO_OIDC_ISSUER: OIDC issuer URL
  SSO_OIDC_CLIENT_ID: OIDC client ID
  SSO_OIDC_CLIENT_SECRET: OIDC client secret

Usage:
    from utils.sso import (
        is_sso_configured, get_sso_login_url,
        process_saml_response, process_oidc_callback,
        get_sso_config,
    )
"""
from __future__ import annotations

import base64
import json
import secrets
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from utils.logger import get_logger
from utils.secrets import get_secret
from utils.storage import load_json, save_json

logger = get_logger("sso")

_SSO_CONFIG_FILE = "sso_config.json"
_SSO_SESSIONS_FILE = "sso_sessions.json"

# SSO authentication is FAIL-CLOSED until a proper, signature-validating SAML/OIDC
# implementation ships (e.g. python3-saml / signxml). The prior code path accepted
# SAML/OIDC responses with zero cryptographic validation, allowing anyone who could
# POST a crafted response — or point the server at a chosen issuer — to authenticate
# as any email via provision_sso_user. Never enable this until full signature +
# condition validation is in place.
_SSO_AUTH_ENABLED = False
_SSO_DISABLED_MESSAGE = (
    "SSO 登录尚未启用：prevent signature validation (SAML) / ID-token validation (OIDC) "
    "未实现，为避免认证绕过，该功能已强制关闭。请联系管理员。"
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def is_sso_configured(team_id: str = "") -> bool:
    """Check if SSO is configured (globally or for a specific team)."""
    config = get_sso_config(team_id)
    provider = config.get("provider")
    if provider == "saml":
        return bool(config.get("sso_url")) and bool(config.get("entity_id"))
    elif provider == "oidc":
        return bool(config.get("issuer")) and bool(config.get("client_id"))
    return False


def get_sso_config(team_id: str = "") -> dict:
    """
    Get SSO configuration.

    Checks team-specific config first, then falls back to global env vars.

    Returns:
        Dict with provider, sso_url, entity_id, certificate (SAML)
        or provider, issuer, client_id, client_secret (OIDC)
    """
    # Check team-specific config
    if team_id:
        configs = load_json(_SSO_CONFIG_FILE, default={})
        if team_id in configs:
            return configs[team_id]

    # Fall back to environment variables
    provider = get_secret("SSO_PROVIDER")

    if provider == "saml":
        return {
            "provider": "saml",
            "entity_id": get_secret("SSO_ENTITY_ID"),
            "sso_url": get_secret("SSO_SSO_URL"),
            "certificate": get_secret("SSO_CERTIFICATE"),
            "acs_url": _get_acs_url(),
            "sp_entity_id": _get_sp_entity_id(),
        }
    elif provider == "oidc":
        return {
            "provider": "oidc",
            "issuer": get_secret("SSO_OIDC_ISSUER"),
            "client_id": get_secret("SSO_OIDC_CLIENT_ID"),
            "client_secret": get_secret("SSO_OIDC_CLIENT_SECRET"),
            "redirect_uri": _get_oidc_redirect_uri(),
            "scopes": ["openid", "profile", "email"],
        }

    return {"provider": None}


def save_sso_config(team_id: str, config: dict) -> tuple[bool, str]:
    """
    Save SSO configuration for a team.

    Args:
        team_id: Team to configure SSO for
        config: SSO configuration dict

    Returns:
        (success, message) tuple
    """
    provider = config.get("provider")
    if provider not in ("saml", "oidc"):
        return False, "Provider must be 'saml' or 'oidc'"

    if provider == "saml":
        required = ["entity_id", "sso_url"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
    elif provider == "oidc":
        required = ["issuer", "client_id", "client_secret"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"

    configs = load_json(_SSO_CONFIG_FILE, default={})
    if not isinstance(configs, dict):
        configs = {}
    configs[team_id] = config
    save_json(_SSO_CONFIG_FILE, configs)

    logger.info("SSO config saved for team %s (provider=%s)", team_id, provider)
    return True, "SSO configuration saved"


# ---------------------------------------------------------------------------
# SAML 2.0 flow
# ---------------------------------------------------------------------------

def get_saml_login_url(team_id: str = "", relay_state: str = "") -> str:
    """
    Generate the SAML AuthnRequest redirect URL.

    Args:
        team_id: Team context for multi-tenant SSO
        relay_state: Where to redirect after SSO success

    Returns:
        Full URL to redirect the user to the IdP
    """
    config = get_sso_config(team_id)
    sso_url = config.get("sso_url", "")
    sp_entity_id = config.get("sp_entity_id", _get_sp_entity_id())
    acs_url = config.get("acs_url", _get_acs_url())

    # Build a minimal SAML AuthnRequest
    request_id = f"_req_{secrets.token_hex(8)}"
    issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    authn_request = f"""<samlp:AuthnRequest
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        ID="{request_id}"
        Version="2.0"
        IssueInstant="{issue_instant}"
        Destination="{sso_url}"
        AssertionConsumerServiceURL="{acs_url}"
        ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
        <saml:Issuer>{sp_entity_id}</saml:Issuer>
    </samlp:AuthnRequest>"""

    import zlib
    # Deflate + Base64 encode for HTTP-Redirect binding
    deflated = zlib.compress(authn_request.encode())[2:-4]  # Strip zlib header/checksum
    encoded = base64.b64encode(deflated).decode()

    params = {
        "SAMLRequest": encoded,
    }
    if relay_state:
        params["RelayState"] = relay_state

    return f"{sso_url}?{urllib.parse.urlencode(params)}"


def process_saml_response(
    saml_response_b64: str,
    team_id: str = "",
) -> tuple[bool, dict | str]:
    """
    Process and validate a SAML Response from the IdP.

    **SECURITY — FAIL-CLOSED.** SAML responses are only accepted after full XML
    signature + assertion-condition validation. That validation is not implemented,
    so this function never authenticates a user and always returns ``False``. This
    prevents a forged SAML Response (base64 blob) from being accepted and mapped to
    any email via ``provision_sso_user``.

    Args:
        saml_response_b64: Base64-encoded SAML Response from POST
        team_id: Team context

    Returns:
        ``(False, error_message)`` always (auth disabled).
    """
    if not _SSO_AUTH_ENABLED:
        logger.warning("SAML response rejected: SSO authentication is fail-closed")
        return False, _SSO_DISABLED_MESSAGE

    # ---------------------------------------------------------------------------
    # NOT REACHABLE while `_SSO_AUTH_ENABLED` is False. Kept below only so the
    # intended processing flow is documented; it MUST add signature + Conditions
    # (NotBefore/NotOnOrAfter, Audience, Recipient, Issuer) and nonce validation
    # before this function may ever return True.
    # ---------------------------------------------------------------------------
    try:
        # Decode the SAML response
        response_xml = base64.b64decode(saml_response_b64).decode("utf-8")

        # Extract user attributes (simplified XML parsing)
        # In production, use proper SAML library with signature validation
        import re

        # Extract NameID (email)
        name_id_match = re.search(
            r'<(?:saml[2]?:)?NameID[^>]*>([^<]+)</(?:saml[2]?:)?NameID>',
            response_xml,
        )
        email = name_id_match.group(1).strip() if name_id_match else ""

        # Extract common attributes
        attrs = _extract_saml_attributes(response_xml)

        if not email and not attrs.get("email"):
            return False, "No email found in SAML response"

        user_info = {
            "email": email or attrs.get("email", ""),
            "first_name": attrs.get("firstName", attrs.get("givenName", "")),
            "last_name": attrs.get("lastName", attrs.get("surname", "")),
            "display_name": attrs.get("displayName", ""),
            "groups": attrs.get("groups", []),
            "provider": "saml",
            "team_id": team_id,
            "authenticated_at": datetime.now().isoformat(),
        }

        logger.info("SAML login successful: %s", user_info["email"])
        return True, user_info

    except Exception as e:
        logger.error("SAML response processing failed: %s", e)
        return False, f"SAML validation failed: {e}"


# ---------------------------------------------------------------------------
# OIDC flow
# ---------------------------------------------------------------------------

def get_oidc_login_url(team_id: str = "", state: str = "") -> str:
    """
    Generate the OIDC authorization URL.

    Args:
        team_id: Team context
        state: CSRF protection state parameter

    Returns:
        Authorization URL to redirect user to
    """
    config = get_sso_config(team_id)
    issuer = config.get("issuer", "")
    client_id = config.get("client_id", "")
    redirect_uri = config.get("redirect_uri", _get_oidc_redirect_uri())
    scopes = config.get("scopes", ["openid", "profile", "email"])

    if not state:
        state = secrets.token_urlsafe(16)

    # Discover authorization endpoint
    auth_endpoint = f"{issuer.rstrip('/')}/authorize"

    # Check well-known config for proper endpoint
    try:
        well_known_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        req = urllib.request.Request(well_known_url)
        resp = urllib.request.urlopen(req, timeout=10)
        oidc_config = json.loads(resp.read().decode())
        auth_endpoint = oidc_config.get("authorization_endpoint", auth_endpoint)
    except Exception:
        pass  # Fall back to default endpoint pattern

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "nonce": secrets.token_urlsafe(16),
    }

    return f"{auth_endpoint}?{urllib.parse.urlencode(params)}"


def process_oidc_callback(
    code: str,
    state: str = "",
    team_id: str = "",
) -> tuple[bool, dict | str]:
    """
    Process the OIDC authorization code callback.

    **SECURITY — FAIL-CLOSED.** This flow never validates the ``state``/``nonce``
    it generated, nor the returned ID token (signature/issuer/audience/nonce), so
    it is disabled: it always returns ``False`` rather than trusting a bare
    ``userinfo`` response that an attacker may have arranged. Re-enable only with
    full ID-token validation + state/nonce verification.

    Args:
        code: Authorization code from callback
        state: State parameter for CSRF validation
        team_id: Team context

    Returns:
        ``(False, error_message)`` always (auth disabled).
    """
    if not _SSO_AUTH_ENABLED:
        logger.warning("OIDC callback rejected: SSO authentication is fail-closed")
        return False, _SSO_DISABLED_MESSAGE

    # ---------------------------------------------------------------------------
    # NOT REACHABLE while `_SSO_AUTH_ENABLED` is False. Must validate the ID token
    # (signature, issuer, audience, nonce) and the `state` parameter before use.
    # ---------------------------------------------------------------------------
    config = get_sso_config(team_id)
    issuer = config.get("issuer", "")
    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")
    redirect_uri = config.get("redirect_uri", _get_oidc_redirect_uri())

    # Discover token endpoint
    token_endpoint = f"{issuer.rstrip('/')}/token"
    userinfo_endpoint = f"{issuer.rstrip('/')}/userinfo"

    try:
        well_known_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        req = urllib.request.Request(well_known_url)
        resp = urllib.request.urlopen(req, timeout=10)
        oidc_config = json.loads(resp.read().decode())
        token_endpoint = oidc_config.get("token_endpoint", token_endpoint)
        userinfo_endpoint = oidc_config.get("userinfo_endpoint", userinfo_endpoint)
    except Exception:
        pass

    # Exchange code for tokens
    try:
        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }).encode()

        req = urllib.request.Request(
            token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        token_data = json.loads(resp.read().decode())
    except Exception as e:
        logger.error("OIDC token exchange failed: %s", e)
        return False, f"Token exchange failed: {e}"

    access_token = token_data.get("access_token")
    if not access_token:
        return False, "No access token in response"

    # Fetch user info
    try:
        req = urllib.request.Request(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp = urllib.request.urlopen(req, timeout=15)
        userinfo = json.loads(resp.read().decode())
    except Exception as e:
        logger.error("OIDC userinfo fetch failed: %s", e)
        return False, f"User info fetch failed: {e}"

    user_info = {
        "email": userinfo.get("email", ""),
        "first_name": userinfo.get("given_name", ""),
        "last_name": userinfo.get("family_name", ""),
        "display_name": userinfo.get("name", ""),
        "picture": userinfo.get("picture", ""),
        "sub": userinfo.get("sub", ""),
        "provider": "oidc",
        "team_id": team_id,
        "authenticated_at": datetime.now().isoformat(),
    }

    if not user_info["email"]:
        return False, "No email in user info"

    logger.info("OIDC login successful: %s", user_info["email"])
    return True, user_info


# ---------------------------------------------------------------------------
# Unified SSO entry point
# ---------------------------------------------------------------------------

def get_sso_login_url(team_id: str = "", relay_state: str = "") -> tuple[bool, str]:
    """
    Get the appropriate SSO login URL based on configuration.

    Returns:
        (True, url) if SSO is configured
        (False, error_message) if not configured
    """
    config = get_sso_config(team_id)
    provider = config.get("provider")

    if provider == "saml":
        url = get_saml_login_url(team_id, relay_state)
        return True, url
    elif provider == "oidc":
        url = get_oidc_login_url(team_id, relay_state)
        return True, url
    else:
        return False, "SSO is not configured"


def provision_sso_user(
    user_info: dict,
    team_id: str = "",
) -> tuple[bool, str, dict]:
    """
    Create or update a local user account from SSO attributes.

    This is called after successful SAML/OIDC authentication.
    Implements Just-In-Time (JIT) provisioning.

    Args:
        user_info: User attributes from IdP
        team_id: Team to add the user to

    Returns:
        (success, message, local_user_info) tuple
    """
    email = user_info.get("email", "").strip().lower()
    if not email:
        return False, "No email provided", {}

    # Generate username from email (before @)
    username = email.split("@")[0].replace(".", "").replace("-", "")[:20].lower()
    # Ensure alphanumeric
    username = "".join(c for c in username if c.isalnum())
    if len(username) < 3:
        username = f"sso{secrets.token_hex(4)}"

    # Check if user already exists
    from utils.user_auth import _hash_password, _load_users_db, _save_users_db

    users = _load_users_db()

    # Find by email
    existing_username = None
    for uname, udata in users.items():
        if udata.get("email", "").lower() == email:
            existing_username = uname
            break

    if existing_username:
        # Update existing user
        users[existing_username]["last_sso_login"] = datetime.now().isoformat()
        users[existing_username]["sso_provider"] = user_info.get("provider", "")
        _save_users_db(users)

        local_info = {
            "username": existing_username,
            "email": email,
            "tier": users[existing_username].get("tier", "free"),
        }
        return True, "Existing user logged in via SSO", local_info
    else:
        # Create new user (JIT provisioning)
        # Generate a random password (user won't need it with SSO)
        random_pw = secrets.token_urlsafe(16)
        password_hash = _hash_password(random_pw)

        # Ensure username is unique
        base_username = username
        counter = 1
        while username in users:
            username = f"{base_username}{counter}"
            counter += 1

        display_name = user_info.get("display_name", "")
        if not display_name:
            display_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()

        users[username] = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "tier": "free",  # Will be upgraded if team has a plan
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "email_verified": True,  # SSO = verified
            "sso_provider": user_info.get("provider", ""),
            "sso_sub": user_info.get("sub", ""),
            "display_name": display_name,
            "last_sso_login": datetime.now().isoformat(),
        }
        _save_users_db(users)

        # Add to team if specified
        if team_id:
            try:
                from utils.teams import add_member
                add_member(team_id, username, "member")
            except Exception as e:
                logger.warning("Failed to add SSO user to team: %s", e)

        # Create user data directory
        from utils.user_auth import get_user_data_dir
        get_user_data_dir(username)

        local_info = {
            "username": username,
            "email": email,
            "tier": "free",
            "is_new": True,
        }
        logger.info("SSO user provisioned: %s (%s)", username, email)
        return True, "New user created via SSO", local_info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_acs_url() -> str:
    """Get the Assertion Consumer Service URL (SAML callback)."""
    base_url = get_secret("APP_BASE_URL") or "https://localhost:8501"
    return f"{base_url.rstrip('/')}/api/sso/saml/acs"


def _get_sp_entity_id() -> str:
    """Get Service Provider entity ID."""
    base_url = get_secret("APP_BASE_URL") or "https://localhost:8501"
    return f"{base_url.rstrip('/')}/saml/metadata"


def _get_oidc_redirect_uri() -> str:
    """Get OIDC redirect URI."""
    base_url = get_secret("APP_BASE_URL") or "https://localhost:8501"
    return f"{base_url.rstrip('/')}/api/sso/oidc/callback"


def _extract_saml_attributes(xml: str) -> dict:
    """
    Extract attribute values from a SAML Response XML.

    This is a simplified parser. In production, use python3-saml.
    """
    import re

    attrs: dict[str, Any] = {}

    # Find all Attribute elements and their values
    attr_pattern = r'<(?:saml[2]?:)?Attribute\s+Name="([^"]+)"[^>]*>.*?<(?:saml[2]?:)?AttributeValue[^>]*>([^<]*)</(?:saml[2]?:)?AttributeValue>'
    matches = re.findall(attr_pattern, xml, re.DOTALL)

    for name, value in matches:
        # Normalize common attribute names
        short_name = name.split("/")[-1] if "/" in name else name
        attrs[short_name] = value.strip()

    return attrs
