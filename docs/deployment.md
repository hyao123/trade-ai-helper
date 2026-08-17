# Deployment Guide

TradeAI Pro is a Streamlit application. The real application runtime must be a platform that supports long-lived HTTP/WebSocket connections.

## Production topology

Recommended setup:

```text
User browser
  └─ https://trade-ai-helper.streamlit.app   # Streamlit Cloud runtime
```

The repository is deployed **only** on Streamlit Cloud. Because Streamlit requires long-lived HTTP/WebSocket connections, it must not be deployed as a Vercel / Netlify serverless function. Serverless-style config files (`vercel.json`, `Procfile`, `runtime.txt`) have been removed from the repository.

## Supported runtime platforms

| Platform | Status | Notes |
|---|---|---|
| Streamlit Cloud | Recommended | Set main file to `app.py`; configure secrets in Streamlit Cloud. |
| Self-hosted Streamlit | Supported | Run `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0` on any long-lived server. |
| Vercel / Netlify | Not supported | Serverless runtime is not suitable for Streamlit WebSocket sessions. |

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

# Simple single-instance demo persistence. Uses Python's built-in sqlite3 module.
SQLITE_DB_PATH = "trade_ai_helper.sqlite3"

# Production/commercial persistence option.
# DATABASE_URL = "your-postgres-database-url"

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
5. The app signs the user in and lands on the home page.

`APP_PASSWORD` is not required for user registration. When set, it only acts as an admin fallback password for the `admin` login. To intentionally run the app without any login gate, set `AUTH_REQUIRED = "false"` in Streamlit secrets or environment variables.

## User data persistence

Logged-in user history is saved per account. AI generation history is stored in the configured `DatabaseBackend`:

- With `SQLITE_DB_PATH` or a SQLite `DATABASE_URL`: users, usage, payment state, and per-user history are saved in a single SQLite file. This is the recommended first step for a lightweight demo or single-instance deployment.
- With a PostgreSQL `DATABASE_URL`: per-user data is saved in PostgreSQL and is better suited for commercial or multi-instance deployment.
- Without either setting: per-user data falls back to JSON files under the app's local `data/` directory. This is fine for local development, but hosted ephemeral file systems may lose data on restart or redeploy.

For a public demo, start with SQLite. For production with multiple app instances or strict durability requirements, move to PostgreSQL.

## Self-hosting

For self-hosted long-lived servers (Docker, a VPS, Railway, Render, etc.), start Streamlit with a `$PORT`-style command:

```bash
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

Configure platform environment variables for secrets. The repository intentionally does not ship a `Procfile` or `runtime.txt`; add platform-specific config in the target host if needed.

## Stripe webhook receiver

Tier upgrades complete from the one-time Stripe Checkout return URL, so the main
app never needs to receive webhooks. **Subscription lifecycle events** — cancelling
a paid tier (downgrade to free) and failed payments — are handled by the
`utils/stripe_webhook` handler, which is surfaced by a small **standalone WSGI
receiver** in `webhook_receiver.py` (stdlib only, no extra dependencies).

Point your Stripe webhook at `{APP_BASE_URL}/api/stripe/webhook` and configure the
`STRIPE_WEBHOOK_SECRET` signing secret. Run it as a separate small process/function —
**not** on the same worker as the Streamlit app:

```bash
# standalone
PORT=8787 python webhook_receiver.py

# or behind gunicorn / waitress
gunicorn webhook_receiver:application --bind 0.0.0.0:8787
waitress-serve --port=8787 webhook_receiver:application
```

`GET /healthz` returns `200 ok` for liveness probes. The receiver returns a non-2xx
status on any failure so Stripe retries delivery.

## Deployment verification checklist

After deploying to Streamlit Cloud, verify:

1. The app loads at `https://trade-ai-helper.streamlit.app`.
2. Login and self-service registration are visible before authentication.
3. A new user can register and land on the app home page.
4. The user can generate AI content and see it in history.
5. The same user can log out, log back in, and still see account history.
6. Navigation between pages works without full-page errors.
7. AI generation works with `NVIDIA_API_KEY` or another configured provider.
8. File upload/download flows work for PDF and CSV features.
9. Stripe upgrade flows use the correct `APP_BASE_URL`.

## Security notes

The `.streamlit/config.toml` file should keep CSRF/XSRF protection enabled for public deployments. Avoid disabling CORS/XSRF just to make a serverless proxy work; that is usually a sign the app is deployed on the wrong platform.
