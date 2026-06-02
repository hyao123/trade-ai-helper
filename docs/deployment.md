# Deployment Guide

TradeAI Pro is a Streamlit application. The real application runtime must be a platform that supports long-lived HTTP/WebSocket connections.

## Production topology

Recommended setup:

```text
User browser
  ├─ https://trade-ai-helper.streamlit.app   # Streamlit Cloud runtime
  └─ Vercel custom/project URL               # optional redirect only
```

Vercel is **not** used to run Streamlit. It only redirects traffic to the Streamlit Cloud app. This repository's `vercel.json` is intentionally configured as a redirect layer because Streamlit requires WebSocket support and should not be deployed as a Vercel/Netlify serverless function.

## Supported runtime platforms

| Platform | Status | Notes |
|---|---|---|
| Streamlit Cloud | Recommended | Set main file to `app.py`; configure secrets in Streamlit Cloud. |
| Railway | Supported | Uses `Procfile`; supports `$PORT` and long-lived connections. |
| Render | Supported | Uses `Procfile`; configure as a Web Service. |
| Vercel | Redirect only | Do not run Streamlit here; use it only as a redirect/front-door if needed. |
| Netlify | Not supported | Serverless runtime is not suitable for Streamlit WebSocket sessions. |

## Streamlit Cloud settings

Create a new Streamlit Cloud app with:

- Repository: `hyao123/trade-ai-helper`
- Branch: `master`
- Main file path: `app.py`
- Python dependencies: `requirements.txt`

Required secret:

```toml
NVIDIA_API_KEY = "nvapi-xxx"
```

Authentication is required by default in public deployments. Users will see login and registration tabs and can create their own Free accounts without an admin-created account.

Common optional secrets:

```toml
# Optional admin fallback password. Users can still self-register without this.
APP_PASSWORD = "your-admin-password"

# Set only for local/demo deployments that should bypass login and registration.
# AUTH_REQUIRED = "false"

OPENAI_API_KEY = "sk-xxx"
DEEPSEEK_API_KEY = "sk-xxx"
STRIPE_SECRET_KEY = "sk_live_xxx"
STRIPE_PRICE_ID_PRO = "price_xxx"
STRIPE_PRICE_ID_ENTERPRISE = "price_xxx"
APP_BASE_URL = "https://trade-ai-helper.streamlit.app"
SMTP_HOST = "smtp.example.com"
SMTP_PORT = "587"
SMTP_USER = "user@example.com"
SMTP_PASSWORD = "smtp-password"
SMTP_FROM_EMAIL = "noreply@example.com"
```

## Self-service registration

By default, deployed users can self-register from the authentication screen:

1. Open the app URL.
2. Choose the registration tab.
3. Enter username, optional email, password, and optional referral code.
4. Submit the form to create a Free account.
5. Log in with the new username and password.

`APP_PASSWORD` is not required for user registration. When set, it only acts as an admin fallback password for the `admin` login. To intentionally run the app without any login gate, set `AUTH_REQUIRED = "false"` in Streamlit secrets or environment variables.

## Railway / Render

The app ships with this `Procfile`:

```procfile
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

That command is intended for hosts that inject a `$PORT` environment variable. Configure secrets as platform environment variables.

## Vercel redirect behavior

`vercel.json` permanently redirects all routes to Streamlit Cloud:

```json
{
  "destination": "https://trade-ai-helper.streamlit.app",
  "permanent": true
}
```

A successful Vercel deployment only confirms that the redirect layer is live. It does **not** validate the Streamlit runtime.

## Deployment verification checklist

After deploying to Streamlit Cloud, verify:

1. The app loads at `https://trade-ai-helper.streamlit.app`.
2. Login and self-service registration are visible before authentication.
3. A new user can register and then log in as a Free account.
4. Navigation between pages works without full-page errors.
5. AI generation works with `NVIDIA_API_KEY` or another configured provider.
6. File upload/download flows work for PDF and CSV features.
7. Stripe upgrade flows use the correct `APP_BASE_URL`.

## Security notes

The `.streamlit/config.toml` file should keep CSRF/XSRF protection enabled for public deployments. Avoid disabling CORS/XSRF just to make a serverless proxy work; that is usually a sign the app is deployed on the wrong platform.
