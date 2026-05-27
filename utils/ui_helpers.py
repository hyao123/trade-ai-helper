"""
utils/ui_helpers.py
-------------------
所有页面共享的 UI 组件：
- inject_css()   注入全局样式（幂等，用 session_state 控制）
- check_auth()   访问密码鉴权
- copy_button()  真实可用的"复制到剪贴板"按钮
- show_result()  统一渲染生成结果区域（流式/非流式均正确处理）
"""

from __future__ import annotations

import hmac
import html
import json
import re
import types

import streamlit as st

from config.i18n import LANGUAGES, t
from utils.secrets import get_secret
from utils.user_auth import (
    authenticate_user,
    get_current_user,
    register_user,
    request_password_reset,
    reset_password,
)

# ---------------------------------------------------------------------------
# 全局 CSS
# ---------------------------------------------------------------------------
_CSS = """
<style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');

    /* ── Base ── */
    * { font-family: 'Inter', 'Noto Sans SC', 'Microsoft YaHei', sans-serif !important; }
    :root {
        --primary:   #2563eb;
        --primary-light: #eff6ff;
        --primary-dark:  #1e40af;
        --accent:    #7c3aed;
        --success:   #059669;
        --warning:   #d97706;
        --surface:   #ffffff;
        --surface-2: #f8fafc;
        --border:    #e2e8f0;
        --text-1:    #0f172a;
        --text-2:    #475569;
        --text-3:    #94a3b8;
        --radius-lg: 16px;
        --radius-md: 10px;
        --radius-sm: 6px;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
        --shadow-lg: 0 10px 40px rgba(0,0,0,0.10), 0 4px 12px rgba(0,0,0,0.06);
    }

    .block-container { padding: 1.5rem 2.5rem !important; max-width: 1320px !important; }
    h1, h2, h3 { font-weight: 700 !important; color: var(--text-1) !important; }
    h3 { font-size: 1.05rem !important; }

    /* ── Hero ── */
    .hero-section {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 40%, #4f46e5 75%, #7c3aed 100%);
        padding: 2.8rem 2.5rem 2.4rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: '';
        position: absolute; inset: 0;
        background: radial-gradient(ellipse at 80% 50%, rgba(124,58,237,0.35) 0%, transparent 60%),
                    radial-gradient(ellipse at 20% 80%, rgba(37,99,235,0.25) 0%, transparent 50%);
        pointer-events: none;
    }
    .hero-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,0.12); backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px; padding: 4px 14px; font-size: 0.78rem;
        font-weight: 600; letter-spacing: 0.04em; margin-bottom: 1rem;
        color: rgba(255,255,255,0.9);
    }
    .hero-title {
        font-size: 2.4rem !important; font-weight: 800 !important;
        line-height: 1.2 !important; margin-bottom: 0.6rem !important;
        letter-spacing: -0.02em;
    }
    .hero-title span { color: #93c5fd; }
    .hero-subtitle { font-size: 1rem; opacity: 0.82; line-height: 1.6; max-width: 560px; }
    .hero-tags {
        display: flex; flex-wrap: wrap; gap: 8px; margin-top: 1.4rem;
    }
    .hero-tag {
        background: rgba(255,255,255,0.12); backdrop-filter: blur(6px);
        border: 1px solid rgba(255,255,255,0.18); border-radius: 20px;
        padding: 4px 12px; font-size: 0.8rem; color: rgba(255,255,255,0.9);
        font-weight: 500;
    }
    .hero-stats {
        display: flex; gap: 2rem; margin-top: 1.6rem;
        padding-top: 1.4rem; border-top: 1px solid rgba(255,255,255,0.15);
    }
    .hero-stat-num { font-size: 1.55rem; font-weight: 800; color: #fff; }
    .hero-stat-lbl { font-size: 0.75rem; color: rgba(255,255,255,0.65); margin-top: 2px; }

    /* ── Stat cards (overview row) ── */
    .stat-card {
        background: var(--surface); border-radius: var(--radius-lg);
        padding: 1.2rem 1.4rem;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
        display: flex; align-items: center; gap: 1rem;
        transition: box-shadow .2s, transform .2s;
    }
    .stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
    .stat-icon {
        width: 44px; height: 44px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem; flex-shrink: 0;
    }
    .stat-value { font-size: 1.5rem; font-weight: 800; color: var(--text-1); line-height: 1; }
    .stat-label { font-size: 0.78rem; color: var(--text-2); margin-top: 3px; }

    /* ── Feature cards (quick access grid) ── */
    .feat-card {
        background: var(--surface); border-radius: var(--radius-lg);
        padding: 1.3rem 1.1rem 1.1rem;
        border: 1.5px solid var(--border);
        box-shadow: var(--shadow-sm);
        text-align: center; cursor: pointer;
        transition: all .2s ease;
        height: 100%;
    }
    .feat-card:hover {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(37,99,235,0.08), var(--shadow-md);
        transform: translateY(-3px);
    }
    .feat-icon {
        font-size: 2rem; margin-bottom: 0.55rem;
        display: block;
    }
    .feat-title {
        font-size: 0.88rem; font-weight: 700; color: var(--text-1);
        line-height: 1.3; margin-bottom: 0.3rem;
    }
    .feat-desc {
        font-size: 0.73rem; color: var(--text-3); line-height: 1.4;
    }

    /* ── Category row items ── */
    .cat-row {
        display: flex; align-items: center; padding: 0.7rem 0.9rem;
        border-radius: var(--radius-md); border: 1px solid var(--border);
        background: var(--surface); margin-bottom: 0.5rem;
        transition: background .15s, border-color .15s;
    }
    .cat-row:hover { background: var(--primary-light); border-color: #bfdbfe; }
    .cat-row-icon { font-size: 1.1rem; margin-right: 0.65rem; flex-shrink: 0; }
    .cat-row-title { font-size: 0.88rem; font-weight: 600; color: var(--text-1); }
    .cat-row-desc  { font-size: 0.77rem; color: var(--text-2); margin-left: 0.5rem; }

    /* ── Tips cards ── */
    .tip-card-pro {
        background: var(--surface);
        border-radius: var(--radius-md);
        padding: 1rem 1.1rem;
        border: 1px solid var(--border);
        border-left: 3px solid var(--primary);
        box-shadow: var(--shadow-sm);
        font-size: 0.84rem; color: var(--text-2); line-height: 1.6;
    }
    .tip-card-pro strong { color: var(--text-1); }

    /* ── Section divider label ── */
    .section-label {
        font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: var(--text-3);
        margin: 1.6rem 0 0.8rem; display: flex; align-items: center; gap: 8px;
    }
    .section-label::after {
        content: ''; flex: 1; height: 1px; background: var(--border);
    }

    /* ── main-form (existing pages) ── */
    .main-form {
        background: var(--surface); border-radius: var(--radius-lg); padding: 2rem;
        box-shadow: var(--shadow-sm); border: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }
    .form-title { color: var(--text-1); font-size: 1.1rem; font-weight: 700; margin-bottom: 1.25rem; }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea  > div > div > textarea {
        border-radius: 8px !important; border: 1.5px solid var(--border) !important;
        padding: 0.6rem 0.85rem !important; font-size: 0.9rem !important;
        background: var(--surface-2) !important;
        transition: border-color .15s, box-shadow .15s;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea  > div > div > textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
        background: var(--surface) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 8px !important; font-weight: 600 !important;
        padding: 0.55rem 1.25rem !important; font-size: 0.88rem !important;
        transition: all .2s !important; border: 1.5px solid transparent !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(37,99,235,0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 16px rgba(37,99,235,0.4) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        border-color: var(--border) !important; color: var(--text-1) !important;
        background: var(--surface) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--primary) !important; color: var(--primary) !important;
        background: var(--primary-light) !important;
    }

    /* ── Tip card (pages) ── */
    .tip-card {
        background: #fffbeb; border-radius: 8px; padding: 0.75rem 1rem;
        border-left: 3px solid #f59e0b; margin-bottom: 1rem; font-size: 0.85rem;
    }

    /* ── Success / result ── */
    .success-box {
        background: linear-gradient(135deg, #dcfce7 0%, #d1fae5 100%);
        border-radius: 12px; padding: 1.1rem; text-align: center;
        border: 1.5px solid #6ee7b7; margin: 1rem 0;
    }
    .success-title { font-size: 1rem; font-weight: 700; color: #065f46; }
    .result-area {
        background: var(--surface-2); border-radius: var(--radius-md); padding: 1.25rem;
        border: 1px solid var(--border); margin-top: 1rem;
    }
    .subject-box {
        background: var(--primary-light); border-radius: var(--radius-md);
        padding: 1rem 1.25rem; border: 1.5px solid #bfdbfe; margin-bottom: 0.75rem;
    }
    .subject-label {
        font-size: 0.72rem; font-weight: 700; color: var(--primary);
        text-transform: uppercase; letter-spacing: 0.06em;
    }
    .subject-text { font-size: 1rem; font-weight: 600; color: var(--text-1); margin-top: 0.25rem; }
    .stream-container {
        background: var(--surface-2); border-radius: var(--radius-md); padding: 1.25rem;
        border: 1.5px dashed #bfdbfe; margin: 0.75rem 0;
        min-height: 60px; line-height: 1.7; white-space: pre-wrap;
        font-size: 0.95rem; color: var(--text-1);
    }

    /* ── Login ── */
    .login-box {
        max-width: 420px; margin: 5rem auto; background: var(--surface);
        border-radius: 20px; padding: 2.5rem;
        box-shadow: var(--shadow-lg); border: 1px solid var(--border); text-align: center;
    }
    .login-title { font-size: 1.45rem; font-weight: 800; color: var(--text-1); margin-bottom: 0.4rem; }
    .login-sub   { color: var(--text-2); font-size: 0.9rem; margin-bottom: 1.5rem; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }
    [data-testid="stSidebarNavItems"] {
        padding-top: 0 !important;
    }

    /* ── Sidebar collapse/expand toggle button (更醒目) ── */
    [data-testid="collapsedControl"] {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        border-radius: 0 12px 12px 0 !important;
        padding: 12px 10px 12px 8px !important;
        box-shadow: 0 4px 16px rgba(99,102,241,0.35), 0 2px 6px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease !important;
        border: none !important;
        top: 1rem !important;
    }
    [data-testid="collapsedControl"]:hover {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        box-shadow: 0 6px 24px rgba(99,102,241,0.5), 0 3px 8px rgba(0,0,0,0.12) !important;
        transform: translateX(3px) !important;
    }
    [data-testid="collapsedControl"] svg {
        color: white !important;
        width: 20px !important;
        height: 20px !important;
    }
    /* Sidebar内的 collapse 按钮(收起按钮) */
    [data-testid="stSidebar"] button[kind="header"] {
        background: rgba(79, 70, 229, 0.08) !important;
        border-radius: 8px !important;
        border: 1.5px solid rgba(79, 70, 229, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] button[kind="header"]:hover {
        background: rgba(79, 70, 229, 0.15) !important;
        border-color: var(--primary) !important;
        transform: scale(1.05) !important;
    }
    [data-testid="stSidebar"] button[kind="header"] svg {
        color: var(--primary) !important;
    }
    [data-testid="stSidebar"] [aria-current="page"],
    [data-testid="stSidebar"] [aria-current="page"] span {
        color: var(--primary) !important; font-weight: 700 !important;
        background: rgba(37,99,235,0.08) !important; border-radius: 6px;
    }
    [data-testid="stSidebar"] .stProgress > div > div { background-color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stProgress > div > div > div { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] hr { border-color: var(--border) !important; }
    [data-testid="stSidebar"] .stMarkdown a { color: var(--primary) !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: var(--surface-2) !important;
        border-radius: 10px; padding: 4px !important;
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px !important; font-weight: 600 !important;
        font-size: 0.84rem !important; padding: 0.4rem 1rem !important;
        color: var(--text-2) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--surface) !important; color: var(--primary) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    /* ── Metrics ── */
    [data-testid="metric-container"] {
        background: var(--surface); border-radius: var(--radius-lg);
        border: 1px solid var(--border); padding: 1rem 1.2rem !important;
        box-shadow: var(--shadow-sm);
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 800 !important; color: var(--text-1) !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: var(--text-2) !important; }

    /* ── Footer ── */
    .footer { text-align: center; padding: 1.8rem; color: var(--text-3); font-size: 0.78rem; }
    .footer a { color: var(--primary) !important; text-decoration: none; }

    /* ── Hide Streamlit default chrome for cleaner look ── */
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }
    footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none !important; }

    /* ── Misc ── */
    .price-tag {
        background: rgba(255,255,255,0.18); padding: 0.4rem 1rem;
        border-radius: 20px; display: inline-flex; align-items: center;
        gap: 0.5rem; margin-top: 0.75rem; font-size: 0.88rem;
        border: 1px solid rgba(255,255,255,0.25);
    }

    /* ── Animations ── */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .hero-section { animation: fadeUp .5s ease both; }
    .feat-card    { animation: fadeUp .4s ease both; }

    @media (max-width: 768px) {
        .block-container { padding: 0.75rem !important; }
        .hero-title { font-size: 1.6rem !important; }
        .hero-stats { flex-wrap: wrap; gap: 1rem; }
    }
</style>
"""


def inject_css() -> None:
    """注入全局 CSS（幂等：用 session_state 控制，每次 session 只注入一次）。"""
    if not st.session_state.get("_css_injected"):
        st.markdown(_CSS, unsafe_allow_html=True)
        st.session_state["_css_injected"] = True
    # 每次页面渲染时刷新侧栏信息
    show_sidebar_info()


# ---------------------------------------------------------------------------
# 侧栏信息（Rate Limit 剩余次数）
# ---------------------------------------------------------------------------
def _get_session_user_id() -> str:
    """获取当前 session 唯一 ID 作为 rate-limit user_id（per-session 限速）。"""
    if "user_session_id" not in st.session_state:
        import uuid
        st.session_state["user_session_id"] = str(uuid.uuid4())[:8]
    return st.session_state["user_session_id"]


def show_sidebar_info() -> None:
    """在侧栏显示 Logo、用户信息、剩余 API 调用次数和重置倒计时。"""
    from utils.ai_client import (
        RATE_LIMIT_MAX_CALLS,
        get_rate_limit_remaining,
        get_rate_limit_reset_seconds,
    )

    uid = _get_session_user_id()

    with st.sidebar:
        # ── Logo / Brand ──
        st.markdown(
            '<div style="text-align:center;padding:0.2rem 0 0.5rem;">'
            '<img src="app/static/logo.svg" alt="AI-Trade Pro" '
            'style="width:52px;height:52px;margin-bottom:6px;'
            'filter:drop-shadow(0 2px 8px rgba(99,102,241,0.3));" />'
            '<div style="font-size:1.1rem;font-weight:800;color:#1e293b;letter-spacing:-0.02em;">AI-Trade Pro</div>'
            '<div style="font-size:0.66rem;color:#64748b;margin-top:2px;">外贸全流程 AI 助手</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Language selector at top
        lang_options = list(LANGUAGES.keys())
        current_lang = st.session_state.get("language", "zh")
        current_display = next(
            (k for k, v in LANGUAGES.items() if v == current_lang),
            lang_options[0],
        )
        current_idx = lang_options.index(current_display) if current_display in lang_options else 0
        selected_display = st.selectbox(
            t("language"),
            lang_options,
            index=current_idx,
            key="_lang_selector",
        )
        new_lang = LANGUAGES[selected_display]
        if new_lang != st.session_state.get("language", "zh"):
            st.session_state["language"] = new_lang
            # Persist to user profile if logged in
            current_user = get_current_user()
            if current_user and current_user.get("username") not in (None, "admin"):
                from utils.storage import load_json, save_json
                users_db = load_json("users_db.json", default={})
                if current_user["username"] in users_db:
                    users_db[current_user["username"]]["language"] = new_lang
                    save_json("users_db.json", users_db)
            st.rerun()

        # Show user info and logout button
        current_user = get_current_user()
        if current_user:
            username = current_user.get("username", "")
            tier = current_user.get("tier", "free")
            tier_badge = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}.get(tier, tier)
            st.markdown(f"### 👤 {username}")
            st.caption(f"{t('plan_label')}: **{tier_badge}**")
            if st.button(f"🚪 {t('logout')}", key="_logout_btn", use_container_width=True):
                st.session_state.pop("authenticated", None)
                st.session_state.pop("current_user", None)
                st.rerun()

        st.markdown("---")
        st.markdown(f"### {t('usage_status')}")

        # Tier-based usage display for logged-in non-admin users
        if current_user and current_user.get("username") not in (None, "admin"):
            from utils.pricing import TIER_CONFIG, get_daily_usage
            username = current_user["username"]
            tier = current_user.get("tier", "free")
            config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
            daily_limit = config["daily_limit"]
            count = get_daily_usage(username)

            if daily_limit is not None:
                progress_val = count / daily_limit if daily_limit > 0 else 0
                st.progress(min(progress_val, 1.0))
                st.caption(f"{t('used_today')} **{count}/{daily_limit}** {t('times')}")
            else:
                st.progress(0.0)
                st.caption(f"{t('used_today')} **{count}** {t('times')} ({t('unlimited')})")
        else:
            # Sliding-window display for admin or non-logged-in mode
            remaining = get_rate_limit_remaining(uid)
            used = RATE_LIMIT_MAX_CALLS - remaining
            st.progress(used / RATE_LIMIT_MAX_CALLS if RATE_LIMIT_MAX_CALLS > 0 else 0)
            st.caption(f"{t('used')} **{used}** / {RATE_LIMIT_MAX_CALLS} {t('times')}")

            reset_secs = get_rate_limit_reset_seconds(uid)
            if reset_secs > 0:
                minutes, seconds = divmod(reset_secs, 60)
                st.caption(t("earliest_release").format(minutes=minutes, seconds=seconds))
        st.markdown("---")


def get_user_id() -> str:
    """获取当前用户的 user ID（供 AI 业务函数传递给 rate limiter）。"""
    current_user = get_current_user()
    if current_user:
        return current_user.get("username", _get_session_user_id())
    return _get_session_user_id()


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------
def check_auth() -> None:
    """
    Multi-user authentication with login/register tabs.
    - APP_PASSWORD not set: pass through
    - Already authenticated: pass through
    - Not authenticated: show login/register UI and st.stop()
    - APP_PASSWORD as admin fallback: if login password matches APP_PASSWORD,
      authenticate as admin with enterprise tier.
    """
    app_password = get_secret("APP_PASSWORD")
    if not app_password:
        st.session_state.authenticated = True
        return
    if st.session_state.get("authenticated"):
        return

    # Determine which view to show: 'login', 'forgot', or 'reset'
    auth_view = st.session_state.get("_auth_view", "login")

    st.markdown(f"""
    <div class="login-box">
        <div style="font-size:2.5rem;">💼</div>
        <div class="login-title">{t('login_title')}</div>
        <div class="login-sub">{t('login_subtitle')}</div>
    </div>
    """, unsafe_allow_html=True)

    if auth_view == "forgot":
        _show_forgot_password_view()
        st.stop()
    elif auth_view == "reset":
        _show_reset_password_view()
        st.stop()

    login_tab, register_tab = st.tabs([t("login_tab"), t("register_tab")])

    with login_tab:
        with st.form("login_form"):
            login_username = st.text_input(t("username"), placeholder=t("username_placeholder"), key="login_username")
            login_password = st.text_input(t("password"), type="password", placeholder=t("password_placeholder"), key="login_password")
            if st.form_submit_button(t("login_button"), use_container_width=True, type="primary"):
                # Admin fallback: APP_PASSWORD grants admin access only for "admin" or empty username
                login_name_lower = login_username.strip().lower()
                if hmac.compare_digest(login_password, app_password) and login_name_lower in ("admin", ""):
                    st.session_state.authenticated = True
                    st.session_state["current_user"] = {"username": "admin", "tier": "enterprise"}
                    st.rerun()
                else:
                    success, user_info = authenticate_user(login_username, login_password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state["current_user"] = user_info
                        # Load language preference from user profile
                        saved_lang = user_info.get("language")
                        if saved_lang:
                            st.session_state["language"] = saved_lang
                        st.rerun()
                    else:
                        st.error(f"❌ {t('invalid_credentials')}")

        # Forgot password button (outside form since forms can't nest)
        if st.button(f"🔑 {t('forgot_password')}", key="_forgot_pw_btn"):
            st.session_state["_auth_view"] = "forgot"
            st.rerun()

    with register_tab:
        with st.form("register_form"):
            reg_username = st.text_input(t("username"), placeholder=t("choose_username_placeholder"), key="reg_username")
            reg_email = st.text_input(t("email_optional"), placeholder=t("email_placeholder"), key="reg_email")
            reg_password = st.text_input(t("password"), type="password", placeholder=t("choose_password_placeholder"), key="reg_password")
            reg_confirm = st.text_input(t("confirm"), type="password", placeholder=t("confirm_password_placeholder"), key="reg_confirm")
            # Referral code field (pre-filled from URL ?ref=xxx)
            _ref_default = st.query_params.get("ref", "") if hasattr(st, "query_params") else ""
            reg_referral = st.text_input(
                "🎁 邀请码（选填）",
                placeholder="朋友的邀请码，双方各得额度奖励",
                value=_ref_default,
                key="reg_referral",
            )
            if st.form_submit_button(t("register_button"), use_container_width=True, type="primary"):
                if reg_password != reg_confirm:
                    st.error(f"❌ {t('passwords_not_match')}")
                else:
                    success, msg = register_user(reg_username, reg_password, reg_email)
                    if success:
                        st.success(f"✅ {t('registration_successful')}")
                        # Apply referral code if provided
                        if reg_referral and reg_referral.strip():
                            try:
                                from utils.referral import apply_referral
                                ref_ok, ref_msg = apply_referral(
                                    reg_referral.strip(),
                                    reg_username.strip().lower(),
                                )
                                if ref_ok:
                                    st.success(f"🎁 {ref_msg}")
                                else:
                                    st.caption(f"邀请码未生效: {ref_msg}")
                            except Exception as e:
                                st.caption(f"邀请码处理失败: {e}")
                    else:
                        st.error(f"❌ {msg}")

    st.stop()


def _show_forgot_password_view() -> None:
    """Show the forgot password form for requesting a reset email."""
    from utils.email_service import is_email_configured

    with st.form("forgot_password_form"):
        st.subheader(f"🔑 {t('forgot_password')}")
        if not is_email_configured():
            st.warning(f"⚠️ {t('email_not_configured')}")
        email_or_user = st.text_input(
            t("enter_email_or_username"),
            placeholder=t("enter_email_or_username"),
            key="_forgot_input",
        )
        if st.form_submit_button(t("send_reset_email"), use_container_width=True, type="primary"):
            success, msg = request_password_reset(email_or_user)
            if success:
                st.success(f"✅ {t('reset_email_sent')}")
            else:
                st.error(f"❌ {msg}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"⬅️ {t('back_to_login')}", key="_back_login_from_forgot"):
            st.session_state["_auth_view"] = "login"
            st.rerun()
    with col2:
        if st.button(f"🔒 {t('reset_password')}", key="_go_to_reset"):
            st.session_state["_auth_view"] = "reset"
            st.rerun()


def _show_reset_password_view() -> None:
    """Show the reset password form for entering token and new password."""
    with st.form("reset_password_form"):
        st.subheader(f"🔒 {t('reset_password')}")
        reset_username = st.text_input(
            t("username"),
            placeholder=t("username_placeholder"),
            key="_reset_username",
        )
        reset_token = st.text_input(
            t("enter_reset_token"),
            placeholder=t("enter_reset_token"),
            key="_reset_token",
        )
        reset_new_pw = st.text_input(
            t("new_password"),
            type="password",
            placeholder=t("new_password"),
            key="_reset_new_pw",
        )
        reset_confirm_pw = st.text_input(
            t("confirm_new_password"),
            type="password",
            placeholder=t("confirm_new_password"),
            key="_reset_confirm_pw",
        )
        if st.form_submit_button(t("reset_password"), use_container_width=True, type="primary"):
            if reset_new_pw != reset_confirm_pw:
                st.error(f"❌ {t('passwords_not_match')}")
            else:
                success, msg = reset_password(reset_username, reset_token, reset_new_pw)
                if success:
                    st.success(f"✅ {t('password_reset_success')}")
                    st.session_state["_auth_view"] = "login"
                else:
                    if "expired" in msg.lower():
                        st.error(f"❌ {t('token_expired')}")
                    else:
                        st.error(f"❌ {t('token_invalid')}")

    if st.button(f"⬅️ {t('back_to_login')}", key="_back_login_from_reset"):
        st.session_state["_auth_view"] = "login"
        st.rerun()


# ---------------------------------------------------------------------------
# 复制按钮（用 json.dumps 安全转义，防止 JS 注入）
# ---------------------------------------------------------------------------
def copy_button(text: str, key: str) -> None:
    """使用 navigator.clipboard JS API 实现真实复制，2s 后恢复。"""
    safe_js = json.dumps(text)   # 自动处理所有转义：\n \\ " 等
    btn_id = f"copy_btn_{key}"
    st.components.v1.html(
        f"""
        <button id="{btn_id}"
            onclick="navigator.clipboard.writeText({safe_js}).then(()=>{{
                var b=document.getElementById('{btn_id}');
                b.innerText='✅ 已复制';
                b.style.background='#dcfce7';b.style.borderColor='#22c55e';b.style.color='#166534';
                setTimeout(()=>{{
                    b.innerText='📋 复制到剪贴板';
                    b.style.background='white';b.style.borderColor='#3b82f6';b.style.color='#3b82f6';
                }},2000);
            }})"
            style="width:100%;padding:0.55rem 1rem;border-radius:8px;
                   border:1.5px solid #3b82f6;background:white;color:#3b82f6;
                   font-weight:600;cursor:pointer;font-size:0.9rem;transition:all 0.2s;">
            📋 复制到剪贴板
        </button>
        """,
        height=48,
    )


# ---------------------------------------------------------------------------
# Subject Line 提取
# ---------------------------------------------------------------------------
def extract_subject(text: str) -> tuple[str, str]:
    """
    从 AI 输出中提取邮件主题行，支持多种变体格式：
    - Subject: xxx
    - **Subject:** xxx
    - Subject Line: xxx
    - 主题行：xxx
    返回 (subject, body)；提取失败则返回 ('', text)。
    """
    lines = text.strip().splitlines()
    if not lines:
        return "", text

    first = lines[0].strip()
    # 正则匹配多种 Subject 变体（含 markdown bold、中文冒号等）
    pattern = r'^\s*(?:\*\*)?(?:subject(?:\s*line)?|邮件主题行?)\s*[:：]\s*(?:\*\*)?\s*(.+?)(?:\*\*)?\s*$'
    match = re.match(pattern, first, re.IGNORECASE)
    if match:
        subject = match.group(1).strip()
        # 跳过 subject 行之后的空行
        rest_lines = lines[1:]
        while rest_lines and not rest_lines[0].strip():
            rest_lines = rest_lines[1:]
        body = "\n".join(rest_lines).strip()
        return subject, body
    return "", text


def show_subject(subject: str, key: str) -> None:
    """渲染主题行高亮卡片 + 复制按钮（XSS 安全）。"""
    if not subject:
        return
    safe_subject = html.escape(subject)
    st.markdown(
        f'<div class="subject-box">'
        f'<div class="subject-label">📌 邮件主题行（Subject Line）</div>'
        f'<div class="subject-text">{safe_subject}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    copy_button(subject, f"subject_{key}")


# ---------------------------------------------------------------------------
# 结果展示区（静态：非流式 or 流式完成后）
# ---------------------------------------------------------------------------
def _render_result_area(
    text: str,
    result_key: str,
    label: str,
    file_name: str,
    height: int,
    show_subject_line: bool,
) -> None:
    """渲染成功提示 + 可选 Subject Line + 文本区 + 下载/复制按钮。"""
    st.markdown(
        '<div class="success-box">'
        '<div style="font-size:1.5rem;">✅</div>'
        '<div class="success-title">生成完成！</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    display_text = text
    if show_subject_line:
        subject, display_text = extract_subject(text)
        if subject:
            show_subject(subject, result_key)

    st.markdown('<div class="result-area">', unsafe_allow_html=True)
    st.text_area(label, display_text, height=height, key=f"display_{result_key}")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 下载", display_text,
            file_name=file_name, mime="text/plain",
            use_container_width=True,
        )
    with col2:
        copy_button(display_text, result_key)
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 流式渲染（核心修复：让 st.write_stream 在干净容器里运行）
# ---------------------------------------------------------------------------
def _stream_into_container(generator: types.GeneratorType) -> str:
    """
    在一个干净的 st.container() 内运行 st.write_stream()。
    避免周围 HTML/markdown 块干扰 Streamlit 的增量更新机制。
    返回完整文本。
    """
    with st.container():
        full_text: str = st.write_stream(generator)  # type: ignore[arg-type]
    return full_text


# ---------------------------------------------------------------------------
# 统一入口：show_result
# ---------------------------------------------------------------------------
def show_result(
    result: str | types.GeneratorType,
    result_key: str,
    label: str = "📝 生成结果",
    file_name: str = "result.txt",
    height: int = 220,
    balloons: bool = True,
    show_subject_line: bool = False,
    history_feature: str = "",
    history_title: str = "",
) -> None:
    """
    统一渲染生成结果区域。

    流式模式（result 是 GeneratorType）：
      1. 显示"⚡ 正在生成中..."提示
      2. 在干净容器内调用 st.write_stream()，token 实时滚动显示
      3. 流式完成后：保存到 session_state + 历史记录，渲染结果

    非流式模式（result 是 str）：
      直接调用 _render_result_area() 展示。

    history_feature/history_title: 如果传入则自动保存到历史记录。
    """
    if not result:
        return

    if "results" not in st.session_state:
        st.session_state.results = {}

    # ── 流式模式 ──────────────────────────────────────
    if isinstance(result, types.GeneratorType):
        # 1. 状态提示（放在流式区域之前，不影响 write_stream）
        status_placeholder = st.empty()
        status_placeholder.markdown(
            '<div class="success-box">'
            '<div style="font-size:1.2rem;">⚡ 正在生成中，请稍候...</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # 2. 流式输出（独立容器，避免 HTML 块干扰）
        full_text = _stream_into_container(result)

        # 3. 清除"正在生成"提示
        status_placeholder.empty()

        # 4. 保存结果
        st.session_state.results[result_key] = full_text

        # 5. 保存到历史记录
        if history_feature and full_text and not full_text.startswith("⚠️"):
            from utils.history import add_to_history
            add_to_history(history_feature, history_title or result_key, full_text)

        if balloons:
            st.balloons()

        # 6. 渲染静态结果区（Subject Line + 下载 + 复制）
        _render_result_area(full_text, result_key, label, file_name, height, show_subject_line)
        return

    # ── 非流式模式 ────────────────────────────────────
    # 保存到历史记录
    if history_feature and result and not result.startswith("⚠️"):
        from utils.history import add_to_history
        add_to_history(history_feature, history_title or result_key, result)

    _render_result_area(result, result_key, label, file_name, height, show_subject_line)


# ---------------------------------------------------------------------------
# 再生成按钮：再来一版 / 换个风格
# ---------------------------------------------------------------------------
def show_regenerate_buttons(result_key: str, show_style_button: bool = True) -> None:
    """
    Show 'Try again' and optionally 'Change style' buttons after AI generation results.

    Sets session_state flags that the page can check to trigger regeneration:
    - st.session_state[f"{result_key}_regenerate"] = "same" (try again)
    - st.session_state[f"{result_key}_regenerate"] = "style" (change style)

    Parameters:
        result_key: The session_state key for the generated result.
        show_style_button: If True, show both buttons. If False, only show
            '再来一版' (pages without meaningful style differentiation).
    """
    if show_style_button:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 再来一版", key=f"regen_same_{result_key}", use_container_width=True):
                st.session_state[f"{result_key}_regenerate"] = "same"
                st.session_state.results.pop(result_key, None)
                st.rerun()
        with col2:
            if st.button("🎨 换个风格", key=f"regen_style_{result_key}", use_container_width=True):
                st.session_state[f"{result_key}_regenerate"] = "style"
                st.session_state.results.pop(result_key, None)
                st.rerun()
    else:
        if st.button("🔄 再来一版", key=f"regen_same_{result_key}", use_container_width=True):
            st.session_state[f"{result_key}_regenerate"] = "same"
            st.session_state.results.pop(result_key, None)
            st.rerun()
