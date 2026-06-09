"""
utils/ui_helpers.py
-------------------
所有页面共享的 UI 组件：
- inject_css()   注入全局样式（幂等，用 session_state 控制）
- check_auth()   登录/注册/密码找回鉴权入口
- copy_button()  真实可用的“复制到剪贴板”按钮
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
from utils.ui_styles import _CSS
from utils.user_auth import (
    authenticate_user,
    get_current_user,
    register_user,
    request_password_reset,
    reset_password,
)

_AUTH_CSS = """
<style>
.auth-shell {
    max-width: 1120px;
    margin: 2.2rem auto 1.5rem;
}
.auth-hero-card {
    min-height: 560px;
    border-radius: 28px;
    padding: 2.4rem;
    color: white;
    background:
        radial-gradient(circle at 15% 20%, rgba(147,197,253,0.24), transparent 30%),
        radial-gradient(circle at 85% 75%, rgba(167,139,250,0.28), transparent 34%),
        linear-gradient(135deg, #0f172a 0%, #1e3a8a 48%, #4f46e5 100%);
    box-shadow: 0 24px 70px rgba(15,23,42,0.22);
    position: relative;
    overflow: hidden;
}
.auth-hero-card::after {
    content: '';
    position: absolute;
    inset: auto -40px -70px auto;
    width: 220px;
    height: 220px;
    background: rgba(255,255,255,0.08);
    border-radius: 999px;
}
.auth-brand-row { display: flex; align-items: center; gap: 12px; margin-bottom: 2rem; }
.auth-logo {
    width: 46px; height: 46px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.22);
    font-size: 1.35rem;
}
.auth-brand-title { font-size: 1.05rem; font-weight: 800; letter-spacing: -0.02em; }
.auth-brand-sub { font-size: 0.76rem; color: rgba(226,232,240,0.82); margin-top: 2px; }
.auth-eyebrow {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 12px; border-radius: 999px;
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.18);
    font-size: 0.78rem; font-weight: 700; color: #dbeafe;
    margin-bottom: 1.1rem;
}
.auth-headline {
    font-size: clamp(2rem, 4vw, 3.05rem);
    font-weight: 900;
    line-height: 1.08;
    letter-spacing: -0.045em;
    margin-bottom: 1rem;
}
.auth-headline span { color: #bfdbfe; }
.auth-copy {
    max-width: 470px;
    color: rgba(226,232,240,0.86);
    line-height: 1.75;
    font-size: 0.98rem;
}
.auth-proof-grid {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px; margin: 1.8rem 0;
}
.auth-proof {
    padding: 0.9rem 0.85rem;
    border-radius: 16px;
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.16);
    backdrop-filter: blur(8px);
}
.auth-proof strong { display: block; font-size: 1.15rem; color: #ffffff; }
.auth-proof span { display: block; margin-top: 3px; font-size: 0.72rem; color: rgba(226,232,240,0.76); }
.auth-check-list { margin-top: 1.2rem; display: grid; gap: 0.7rem; }
.auth-check-item {
    display: flex; align-items: center; gap: 9px;
    color: rgba(248,250,252,0.92); font-size: 0.88rem;
}
.auth-check-dot {
    width: 22px; height: 22px; border-radius: 999px;
    display: inline-flex; align-items: center; justify-content: center;
    background: rgba(34,197,94,0.18); color: #bbf7d0;
    border: 1px solid rgba(187,247,208,0.24);
    font-size: 0.72rem; flex: 0 0 auto;
}
.auth-panel {
    border-radius: 28px;
    padding: 2rem;
    background: rgba(255,255,255,0.96);
    border: 1px solid rgba(226,232,240,0.9);
    box-shadow: 0 24px 70px rgba(15,23,42,0.12);
}
.auth-panel-title { font-size: 1.35rem; font-weight: 850; color: #0f172a; letter-spacing: -0.025em; }
.auth-panel-sub { color: #64748b; font-size: 0.88rem; line-height: 1.6; margin: 0.35rem 0 1.1rem; }
.auth-note {
    padding: 0.75rem 0.9rem;
    border-radius: 14px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #475569;
    font-size: 0.78rem;
    line-height: 1.6;
    margin: 0.75rem 0 1rem;
}
.auth-mini-row {
    display: flex; justify-content: space-between; gap: 8px;
    color: #64748b; font-size: 0.74rem; margin-top: 1rem;
}
.auth-required { color: #dc2626; font-weight: 700; }
.auth-panel [data-baseweb="tab-list"] { gap: 8px; }
.auth-panel [data-baseweb="tab"] {
    border-radius: 12px !important;
    background: #f8fafc !important;
    padding: 0.7rem 1rem !important;
}
.auth-panel [aria-selected="true"] {
    background: linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%) !important;
    color: #1d4ed8 !important;
    font-weight: 800 !important;
}
@media (max-width: 900px) {
    .auth-shell { margin: 0.5rem auto; }
    .auth-hero-card { min-height: auto; padding: 1.6rem; }
    .auth-proof-grid { grid-template-columns: 1fr; }
    .auth-panel { padding: 1.4rem; }
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

        lang_options = list(LANGUAGES.keys())
        current_lang = st.session_state.get("language", "zh")
        current_display = next((k for k, v in LANGUAGES.items() if v == current_lang), lang_options[0])
        current_idx = lang_options.index(current_display) if current_display in lang_options else 0
        selected_display = st.selectbox(t("language"), lang_options, index=current_idx, key="_lang_selector")
        new_lang = LANGUAGES[selected_display]
        if new_lang != st.session_state.get("language", "zh"):
            st.session_state["language"] = new_lang
            current_user = get_current_user()
            if current_user and current_user.get("username") not in (None, "admin"):
                from utils.repositories import load_users, save_users
                users_db = load_users()
                if current_user["username"] in users_db:
                    users_db[current_user["username"]]["language"] = new_lang
                    save_users(users_db)
            st.rerun()

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


def _render_auth_brand_panel() -> None:
    """Render the professional SaaS marketing panel for authentication screens."""
    st.markdown(
        """
        <div class="auth-hero-card">
            <div class="auth-brand-row">
                <div class="auth-logo">💼</div>
                <div>
                    <div class="auth-brand-title">AI-Trade Pro</div>
                    <div class="auth-brand-sub">外贸全流程 AI 工作台</div>
                </div>
            </div>
            <div class="auth-eyebrow">✦ B2B Sales Copilot</div>
            <div class="auth-headline">把外贸跟进、报价和回复交给 <span>AI 工作流</span></div>
            <div class="auth-copy">
                面向外贸团队的专业 AI 助手：从开发信、询盘回复、报价单到客户管理，统一沉淀到账号历史中，方便复用、追踪和协作。
            </div>
            <div class="auth-proof-grid">
                <div class="auth-proof"><strong>30+</strong><span>业务场景</span></div>
                <div class="auth-proof"><strong>7</strong><span>输出语言</span></div>
                <div class="auth-proof"><strong>CRM</strong><span>客户沉淀</span></div>
            </div>
            <div class="auth-check-list">
                <div class="auth-check-item"><span class="auth-check-dot">✓</span> 登录后自动保存生成历史，换设备也能查看</div>
                <div class="auth-check-item"><span class="auth-check-dot">✓</span> 邮箱用于密码找回和重要账户通知</div>
                <div class="auth-check-item"><span class="auth-check-dot">✓</span> 支持 Free / Pro / Enterprise 套餐升级</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------
def check_auth() -> None:
    """
    Multi-user authentication with login/register tabs.
    - Auth required by default; set AUTH_REQUIRED=false to bypass.
    - Already authenticated: pass through
    - Not authenticated: show login/register UI and st.stop()
    - APP_PASSWORD as admin fallback: if login password matches APP_PASSWORD,
      authenticate as admin with enterprise tier.
    """
    app_password = get_secret("APP_PASSWORD")
    if not app_password:
        st.session_state["authenticated"] = True
        return
    if st.session_state.get("authenticated"):
        return

    auth_view = st.session_state.get("_auth_view", "login")
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    left_col, right_col = st.columns([1.08, 0.92], gap="large")
    with left_col:
        _render_auth_brand_panel()

    with right_col:
        st.markdown(
            """
            <div class="auth-panel-title">欢迎使用 AI-Trade Pro</div>
            <div class="auth-panel-sub">登录已有账号，或创建新账号开始保存你的外贸 AI 工作记录。</div>
            <div class="auth-note">🔒 新账号必须提供邮箱，用于密码找回、账户通知和必要的用户联系。</div>
            """,
            unsafe_allow_html=True,
        )

        if auth_view == "forgot":
            _show_forgot_password_view()
            st.stop()
        if auth_view == "reset":
            _show_reset_password_view()
            st.stop()

        login_tab, register_tab = st.tabs([t("login_tab"), t("register_tab")])

        with login_tab:
            with st.form("login_form"):
                login_username = st.text_input(t("username"), placeholder=t("username_placeholder"), key="login_username")
                login_password = st.text_input(t("password"), type="password", placeholder=t("password_placeholder"), key="login_password")
                if st.form_submit_button(t("login_button"), use_container_width=True, type="primary"):
                    login_name_lower = login_username.strip().lower()
                    if hmac.compare_digest(login_password, app_password) and login_name_lower in ("admin", ""):
                        st.session_state["authenticated"] = True
                        st.session_state["current_user"] = {"username": "admin", "tier": "enterprise"}
                        st.rerun()
                    else:
                        success, user_info = authenticate_user(login_username, login_password)
                        if success:
                            st.session_state["authenticated"] = True
                            st.session_state["current_user"] = user_info
                            saved_lang = user_info.get("language")
                            if saved_lang:
                                st.session_state["language"] = saved_lang
                            from utils.history import migrate_session_history_to_user
                            migrate_session_history_to_user(user_info["username"])
                            st.rerun()
                        else:
                            st.error(f"❌ {t('invalid_credentials')}")

            if st.button(f"🔑 {t('forgot_password')}", key="_forgot_pw_btn", use_container_width=True):
                st.session_state["_auth_view"] = "forgot"
                st.rerun()

        with register_tab:
            with st.form("register_form"):
                reg_username = st.text_input(t("username"), placeholder=t("choose_username_placeholder"), key="reg_username")
                reg_email = st.text_input(t("email_optional"), placeholder=t("email_required_placeholder"), key="reg_email")
                st.caption(t("email_required_help"))
                reg_password = st.text_input(t("password"), type="password", placeholder=t("choose_password_placeholder"), key="reg_password")
                reg_confirm = st.text_input(t("confirm"), type="password", placeholder=t("confirm_password_placeholder"), key="reg_confirm")
                _ref_default = st.query_params.get("ref", "") if hasattr(st, "query_params") else ""
                reg_referral = st.text_input(
                    "🎁 邀请码（选填）",
                    placeholder="朋友的邀请码，双方各得额度奖励",
                    value=_ref_default,
                    key="reg_referral",
                )
                if st.form_submit_button(t("register_button"), use_container_width=True, type="primary"):
                    if not reg_email or not reg_email.strip():
                        st.error(f"❌ {t('email_required_error')}")
                    elif "@" not in reg_email or "." not in reg_email.split("@")[-1]:
                        st.error(f"❌ {t('email_invalid_error')}")
                    elif reg_password != reg_confirm:
                        st.error(f"❌ {t('passwords_not_match')}")
                    else:
                        success, msg = register_user(reg_username, reg_password, reg_email)
                        if success:
                            if reg_referral and reg_referral.strip():
                                try:
                                    from utils.referral import apply_referral
                                    apply_referral(reg_referral.strip(), reg_username.strip().lower())
                                except Exception:
                                    pass
                            from utils.history import migrate_session_history_to_user
                            migrate_session_history_to_user(reg_username.strip().lower())
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

        st.markdown(
            """
            <div class="auth-mini-row">
                <span>企业级数据隔离</span>
                <span>邮箱找回密码</span>
                <span>AI 用量追踪</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


def _show_forgot_password_view() -> None:
    """Show the forgot password form for requesting a reset email."""
    from utils.email_service import is_email_configured

    with st.form("forgot_password_form"):
        st.subheader(f"🔑 {t('forgot_password')}")
        if not is_email_configured():
            st.warning(f"⚠️ {t('email_not_configured')}")
        email_or_user = st.text_input(t("enter_email_or_username"), placeholder=t("enter_email_or_username"), key="_forgot_input")
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
        reset_username = st.text_input(t("username"), placeholder=t("username_placeholder"), key="_reset_username")
        reset_token = st.text_input(t("enter_reset_token"), placeholder=t("enter_reset_token"), key="_reset_token")
        reset_new_pw = st.text_input(t("new_password"), type="password", placeholder=t("new_password"), key="_reset_new_pw")
        reset_confirm_pw = st.text_input(t("confirm_new_password"), type="password", placeholder=t("confirm_new_password"), key="_reset_confirm_pw")
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
    safe_js = json.dumps(text)
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
    """从 AI 输出中提取邮件主题行。"""
    lines = text.strip().splitlines()
    if not lines:
        return "", text
    first = lines[0].strip()
    pattern = r'^\s*(?:\*\*)?(?:subject(?:\s*line)?|邮件主题行?)\s*[:：]\s*(?:\*\*)?\s*(.+?)(?:\*\*)?\s*$'
    match = re.match(pattern, first, re.IGNORECASE)
    if match:
        subject = match.group(1).strip()
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
        st.download_button("📥 下载", display_text, file_name=file_name, mime="text/plain", use_container_width=True)
    with col2:
        copy_button(display_text, result_key)
    st.markdown("</div>", unsafe_allow_html=True)


def _stream_into_container(generator: types.GeneratorType) -> str:
    """在一个干净的 st.container() 内运行 st.write_stream()。"""
    with st.container():
        full_text: str = st.write_stream(generator)  # type: ignore[arg-type]
    return full_text


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
    """统一渲染生成结果区域。"""
    if not result:
        return
    if "results" not in st.session_state:
        st.session_state.results = {}

    if isinstance(result, types.GeneratorType):
        status_placeholder = st.empty()
        status_placeholder.markdown(
            '<div class="success-box"><div style="font-size:1.2rem;">⚡ 正在生成中，请稍候...</div></div>',
            unsafe_allow_html=True,
        )
        full_text = _stream_into_container(result)
        status_placeholder.empty()
        st.session_state.results[result_key] = full_text
        if history_feature and full_text and not full_text.startswith("⚠️"):
            from utils.history import add_to_history
            add_to_history(history_feature, history_title or result_key, full_text)
        if balloons:
            st.balloons()
        _render_result_area(full_text, result_key, label, file_name, height, show_subject_line)
        return

    if history_feature and result and not result.startswith("⚠️"):
        from utils.history import add_to_history
        add_to_history(history_feature, history_title or result_key, result)
    _render_result_area(result, result_key, label, file_name, height, show_subject_line)


def show_regenerate_buttons(result_key: str, show_style_button: bool = True) -> None:
    """Show 'Try again' and optionally 'Change style' buttons after AI generation results."""
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
