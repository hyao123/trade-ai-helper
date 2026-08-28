# Phase A Data Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task.

**Goal:** Prevent silent user-data deletion, duplicate outreach sends, XSS in user HTML, Stripe webhook non-retries, and pytest writes into the real `data/` directory.

**Architecture:** Keep Streamlit and `utils.db.DatabaseBackend`. Add atomic single-user upsert; make bulk user saves upsert-only. Route CRM, campaigns, and tracking through repository collections. Persist each outreach result immediately. Return 400 only for permanent webhook failures and 500 for retryable handler failures. Escape user-controlled HTML. Isolate tests with a temporary data directory.

**Tech Stack:** Python 3.11, pytest, existing JSON/SQLite/Postgres backends, stdlib `html`.

**Spec:** Session review “阶段 A（先做，防丢数据和重复发信）”.

## Global Constraints

- Do not add pages, Drip UI, teams UI, or tracking HTTP endpoints.
- Do not switch Stripe Checkout from `mode: "payment"`; subscription rewrite is out of scope.
- Do not commit unrelated dirty files from the original checkout.
- TDD: write and run a failing test before production code.
- Preserve probe-safe `app.py` with no top-level Streamlit import.
- Reuse `html_escape` in pages and stdlib `html.escape` in `app.py`.
- Stage only files belonging to the current task.

---

### Task 1: User upsert without implicit delete

**Files:** `utils/db.py`, `utils/storage.py`, `utils/repositories.py`, `tests/test_db_backend.py`, `tests/test_repositories.py`.

Add `DatabaseBackend.upsert_user(username: str, user_data: dict) -> None`. Implement it for JSON, SQLite, and PostgreSQL. Change `save_all_users` in all backends to upsert provided rows and never delete rows or user directories omitted from a snapshot; an empty snapshot is a no-op. Change `repositories.save_user` to call `upsert_user` only. JSON upsert must hold the file lock across read/modify/write; add a `mutate_json` helper without recursively acquiring the same lock. Rewrite existing destructive snapshot tests to assert omitted users and their per-user data remain.

TDD tests must cover JSON and SQLite omitted-user preservation, JSON and SQLite single-row updates, PostgreSQL SQL containing no `DELETE ... NOT IN`, and repository `save_user` calling only `upsert_user`.

Run focused DB/repository tests, then `tests/test_user_auth.py` and `tests/test_pricing.py`. Commit `fix: upsert users without deleting omitted accounts`.

---

### Task 2: Route customers, campaigns, and tracking through repositories

**Files:** `utils/repositories.py`, `utils/customers.py`, `utils/auto_outreach.py`, `utils/email_tracking.py`, `tests/test_repositories.py`, optionally `tests/test_phase_a_collections.py`.

Add collection constants and helpers: `CUSTOMERS_COLLECTION`, `CAMPAIGNS_COLLECTION`, `TRACKING_COLLECTION`, `campaign_results_collection(campaign_id)`, `load/save_customers(username: str | None)`, `load/save_campaigns(username)`, `load/save_campaign_results(username, campaign_id)`, and `load/save_email_tracking`. User collections use `load_user_data/save_user_data`; anonymous customers and tracking use global data. Replace direct storage calls in customers, campaign CRUD/results, and every tracking mutation. Preserve existing session-state cache behavior and campaign result naming.

TDD tests must verify per-user vs global repository calls and campaign result collections. Run repository, utility, auto-outreach parse, and email webhook tests. Commit `fix: persist CRM, campaigns, and tracking through db backend`.

---

### Task 3: Persist each outreach send immediately

**Files:** `utils/auto_outreach.py`, optionally `utils/auto_outreach_config.py`, new `tests/test_auto_outreach_persist.py`.

In `run_campaign_step`, after each success or failure append, call `_save_campaign_results` and update campaign stats immediately. Remove the batch persistence window and `unsaved_count`; keep final completion update. Resume must skip only stored records with `status == "sent"`; failed records may retry. Add tests for two sends being persisted and already-sent email being skipped. Run focused persistence and parse tests. Commit `fix: persist outreach results after every send`.

---

### Task 4: Webhook retry status and AUTO_LOGIN readiness

**Files:** `webhook_receiver.py`, `utils/production_readiness.py`, `tests/test_webhook_receiver.py`, `tests/test_production_readiness.py`.

Keep payment as one-time `mode: "payment"`. In the receiver, missing signature, invalid signature, parse/configuration errors return 400. A handler failure such as upgrade failure or missing metadata returns 500 so Stripe retries. Add production readiness check `id="auto_login"` with critical fail when `AUTO_LOGIN` is `1/true/yes/on`; pass otherwise. Do not remove local AUTO_LOGIN behavior from `check_auth`. Add tests for both HTTP statuses and readiness. Commit `fix: retry Stripe handler failures and flag AUTO_LOGIN`.

---

### Task 5: Escape user HTML in home banner and CRM

**Files:** `app.py`, `pages/7_📇_客户管理.py`, `tests/test_xss_escape.py`.

Escape `username` and `email` before interpolation into the home verification banner using stdlib `html.escape` while keeping `app.py` probe-safe. Import existing `html_escape` in CRM and escape product and any other user-controlled values used in unsafe HTML. Add behavioral/source tests proving markup is neutralized. Run XSS and app-entrypoint tests. Commit `fix: escape user HTML in home banner and CRM`.

---

### Task 6: Isolate pytest from real data

**Files:** new `tests/conftest.py`, new `tests/test_storage_isolation.py`, `pyproject.toml`, and `tests/test_utils.py` only if a real-storage test needs a marker.

Add autouse fixture `isolate_app_storage` redirecting `utils.storage.get_data_dir` to `tmp_path / "data"`, clearing `DATABASE_URL` and `SQLITE_DB_PATH`, and resetting `utils.db._db_instance/_db_signature` before and after each test. Register `no_storage_isolation` marker only for the test that explicitly validates real directory creation. Add a test that storage does not resolve to repository `data/`. Run focused storage/auth/db/history tests and then `pytest -q`. Commit `test: isolate pytest storage from the real data directory`.

## Out of scope

- Stripe subscriptions and subscription UI
- Tracking HTTP routes
- Identity-helper unification
- Page scaffolding or i18n
- Secret rotation (operator action)
