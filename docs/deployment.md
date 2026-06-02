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

Common optional secrets:

```toml
APP_PASSWORD = "your-password"
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
2. Navigation between pages works without full-page errors.
3. AI generation works with `NVIDIA_API_KEY` or another configured provider.
4. Login/session behavior works if `APP_PASSWORD` or multi-user auth is enabled.
5. File upload/download flows work for PDF and CSV features.
6. Stripe upgrade flows use the correct `APP_BASE_URL`.

## Security notes

The `.streamlit/config.toml` file should keep CSRF/XSRF protection enabled for public deployments. Avoid disabling CORS/XSRF just to make a serverless proxy work; that is usually a sign the app is deployed on the wrong platform.
