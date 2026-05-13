"""
pages/11_👤_账户管理.py
账户管理页面：个人资料、使用统计、套餐对比、密码修改。
"""
import streamlit as st

from config.i18n import t
from utils.payment import (
    STRIPE_AVAILABLE,
    complete_upgrade,
    create_checkout_session,
    is_payment_configured,
)
from utils.pricing import (
    TIER_CONFIG,
    get_daily_usage,
    get_usage_history,
)
from utils.ui_helpers import check_auth, inject_css
from utils.user_auth import (
    change_password,
    get_current_user,
    resend_verification_email,
    verify_email_token,
)

st.set_page_config(page_title="账户管理 | 外贸AI助手", page_icon="👤", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown(f"""
<div class="hero-section">
    <h1 class="hero-title">{t('account_management')}</h1>
    <p class="hero-subtitle">{t('account_subtitle')}</p>
</div>
""", unsafe_allow_html=True)

# ── 获取当前用户信息 ──────────────────────────────────
current_user = get_current_user()
if not current_user:
    st.warning(t("please_login"))
    st.stop()

username = current_user.get("username", "")
email = current_user.get("email", "")
tier = current_user.get("tier", "free")
created_at = current_user.get("created_at", "未知")

# ══════════════════════════════════════════════════════════
# Section 1: Profile Card
# ══════════════════════════════════════════════════════════
st.markdown(f"## {t('profile')}")

tier_colors = {"free": "#6b7280", "pro": "#3b82f6", "enterprise": "#8b5cf6"}
tier_labels = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}
tier_color = tier_colors.get(tier, "#6b7280")
tier_label = tier_labels.get(tier, tier)

email_display = email if email else t("email_not_set")
email_verified = current_user.get("email_verified", False)

if email and email_verified:
    verification_badge = f'<span style="background:#22c55e; color:white; padding:0.15rem 0.5rem; border-radius:8px; font-size:0.75rem; font-weight:600; margin-left:0.5rem;">{t("email_verified")}</span>'
elif email:
    verification_badge = f'<span style="background:#f97316; color:white; padding:0.15rem 0.5rem; border-radius:8px; font-size:0.75rem; font-weight:600; margin-left:0.5rem;">{t("email_unverified")}</span>'
else:
    verification_badge = ""

st.markdown(f"""
<div class="main-form">
    <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
        <div style="font-size:2.5rem;">👤</div>
        <div>
            <div style="font-size:1.3rem; font-weight:700; color:#1e3a5f;">{username}</div>
            <div style="color:#6b7280; font-size:0.9rem;">{email_display}{verification_badge}</div>
        </div>
        <div style="margin-left:auto;">
            <span style="background:{tier_color}; color:white; padding:0.3rem 0.8rem;
                         border-radius:12px; font-size:0.85rem; font-weight:600;">
                {tier_label}
            </span>
        </div>
    </div>
    <div style="color:#6b7280; font-size:0.85rem;">
        {t('register_time')}: {created_at}
    </div>
</div>
""", unsafe_allow_html=True)

# Email verification section (if email is set but not verified)
if email and not email_verified:
    with st.form("verify_email_form"):
        token_input = st.text_input(t("enter_verification_token"), placeholder=t("enter_verification_token"))
        if st.form_submit_button(t("verify_email"), use_container_width=True, type="primary"):
            if token_input.strip():
                success, msg = verify_email_token(username, token_input.strip())
                if success:
                    st.success(t("verification_success"))
                    st.rerun()
                else:
                    st.error(f"{t('verification_failed')}: {msg}")
            else:
                st.error(t("token_invalid"))

    if st.button(t("resend_verification"), use_container_width=True):
        success, msg = resend_verification_email(username)
        if success:
            st.success(t("verification_sent"))
        else:
            st.warning(msg)

# ══════════════════════════════════════════════════════════
# Section 2: Usage Statistics
# ══════════════════════════════════════════════════════════
st.markdown(f"## {t('usage_stats')}")

config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
daily_limit = config["daily_limit"]
today_usage = get_daily_usage(username)

col_stat1, col_stat2 = st.columns(2)
with col_stat1:
    if daily_limit is not None:
        st.metric(t("daily_used"), f"{today_usage} {t('times')}", delta=f"{t('remaining')} {daily_limit - today_usage} {t('times')}")
        progress_val = today_usage / daily_limit if daily_limit > 0 else 0
        st.progress(min(progress_val, 1.0))
    else:
        st.metric(t("daily_used"), f"{today_usage} {t('times')}", delta=t("unlimited"))
        st.progress(0.0)

with col_stat2:
    if daily_limit is not None:
        st.metric(t("daily_limit"), f"{daily_limit} {t('times_per_day')}")
    else:
        st.metric(t("daily_limit"), t("unlimited"))

# 7-day usage history
st.markdown(f"### {t('recent_7_days')}")
history = get_usage_history(username)
if history:
    hist_cols = st.columns(len(history))
    for i, entry in enumerate(history):
        with hist_cols[i]:
            day_label = entry.get("date", "")[-5:]  # MM-DD format
            count = entry.get("count", 0)
            st.metric(day_label, f"{count} {t('times')}")
else:
    st.info(t("no_usage_record"))

# ══════════════════════════════════════════════════════════
# Section 3: Plan Comparison
# ══════════════════════════════════════════════════════════
st.markdown(f"## {t('plan_comparison')}")

plans = [
    {
        "name": t("free"),
        "tier_key": "free",
        "limit": f"20{t('per_day')}",
        "price": t("price_free"),
        "color": "#6b7280",
        "features": [t("basic_ai_generation"), t("cold_email"), t("product_description"), t("email_reply")],
        "missing": [t("logo_upload"), t("data_export"), t("priority_support")],
    },
    {
        "name": t("pro"),
        "tier_key": "pro",
        "limit": f"100{t('per_day')}",
        "price": t("price_pro"),
        "color": "#3b82f6",
        "features": [t("basic_ai_generation"), t("cold_email"), t("product_description"), t("email_reply"), t("logo_upload"), t("data_export")],
        "missing": [t("priority_support")],
    },
    {
        "name": t("enterprise"),
        "tier_key": "enterprise",
        "limit": t("unlimited_per_day"),
        "price": t("price_enterprise"),
        "color": "#8b5cf6",
        "features": [t("basic_ai_generation"), t("cold_email"), t("product_description"), t("email_reply"), t("logo_upload"), t("data_export"), t("priority_support")],
        "missing": [],
    },
]

plan_cols = st.columns(3)
for i, plan in enumerate(plans):
    with plan_cols[i]:
        is_current = plan["tier_key"] == tier
        border_style = f"3px solid {plan['color']}" if is_current else "1px solid #e5e7eb"
        badge_html = ""
        if is_current:
            badge_html = (
                f'<div style="background:{plan["color"]}; color:white; '
                f'padding:0.2rem 0.6rem; border-radius:8px; font-size:0.75rem; '
                f'font-weight:600; display:inline-block; margin-bottom:0.5rem;">'
                f'{t("current_plan_badge")}</div>'
            )

        features_html = ""
        for feat in plan["features"]:
            features_html += f'<div style="padding:0.2rem 0; font-size:0.85rem;">\u2705 {feat}</div>'
        for feat in plan["missing"]:
            features_html += f'<div style="padding:0.2rem 0; font-size:0.85rem; color:#9ca3af;">\u274c {feat}</div>'

        st.markdown(f"""
        <div style="background:white; border-radius:14px; padding:1.5rem;
                    border:{border_style}; text-align:center; min-height:350px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.06);">
            {badge_html}
            <div style="font-size:1.3rem; font-weight:700; color:{plan['color']};">{plan['name']}</div>
            <div style="font-size:1.4rem; font-weight:700; color:#1e3a5f; margin:0.3rem 0;">
                {plan['price']}
            </div>
            <div style="font-size:0.95rem; font-weight:600; color:#6b7280; margin-bottom:0.5rem;">
                {plan['limit']}
            </div>
            <div style="text-align:left; margin-top:1rem;">
                {features_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Upgrade buttons for tiers higher than current
tier_order = ["free", "pro", "enterprise"]
current_tier_idx = tier_order.index(tier) if tier in tier_order else 0

upgrade_targets = []
if current_tier_idx < 1:
    upgrade_targets.append(("pro", t("upgrade_to_pro")))
if current_tier_idx < 2:
    upgrade_targets.append(("enterprise", t("upgrade_to_enterprise")))

if upgrade_targets:
    st.markdown("")
    for target_tier, button_label in upgrade_targets:
        if st.button(button_label, type="primary", use_container_width=True, key=f"upgrade_{target_tier}"):
            if not STRIPE_AVAILABLE:
                st.info(t("payment_not_available"))
            elif not is_payment_configured():
                st.info(t("payment_not_configured"))
            else:
                success, result = create_checkout_session(username, target_tier)
                if success:
                    st.markdown(f"[{t('payment_checkout_link')}]({result})")
                else:
                    st.error(f"{t('upgrade_failed')}: {result}")

# Verify Payment section
if tier != "enterprise":
    st.markdown(f"### {t('verify_payment')}")
    session_id_input = st.text_input(t("enter_session_id"), placeholder=t("enter_session_id"), key="payment_session_id")
    if st.button(t("verify_and_upgrade"), type="primary", use_container_width=True, key="verify_payment_btn"):
        if session_id_input.strip():
            success, msg = complete_upgrade(username, session_id_input.strip())
            if success:
                st.success(t("upgrade_success"))
                st.rerun()
            else:
                st.error(f"{t('upgrade_failed')}: {msg}")
        else:
            st.warning(t("enter_session_id"))

# ══════════════════════════════════════════════════════════
# Section 4: Change Password (not for admin)
# ══════════════════════════════════════════════════════════
if username != "admin":
    st.markdown(f"## {t('change_password')}")

    with st.form("change_password_form"):
        old_password = st.text_input(t("current_password"), type="password", placeholder=t("current_password_placeholder"))
        new_password = st.text_input(t("new_password"), type="password", placeholder=t("new_password_placeholder"))
        confirm_password = st.text_input(t("confirm_new_password"), type="password", placeholder=t("confirm_new_password_placeholder"))

        if st.form_submit_button(t("confirm_change"), use_container_width=True, type="primary"):
            if not old_password:
                st.error(f"\u274c {t('enter_current_password')}")
            elif not new_password:
                st.error(f"\u274c {t('enter_new_password')}")
            elif new_password != confirm_password:
                st.error(f"\u274c {t('new_passwords_not_match')}")
            else:
                success, msg = change_password(username, old_password, new_password)
                if success:
                    st.success(t("password_changed"))
                else:
                    st.error(f"\u274c {msg}")

# ── Footer ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f'<div class="footer">{t("footer_account")}</div>', unsafe_allow_html=True)
