"""
pages/11_👤_账户管理.py
账户管理页面：个人资料、使用统计、套餐对比、密码修改。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth
from utils.user_auth import get_current_user, change_password
from utils.pricing import (
    TIER_CONFIG,
    get_daily_usage,
    get_user_tier,
    get_usage_history,
)

st.set_page_config(page_title="账户管理 | 外贸AI助手", page_icon="👤", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">👤 账户管理</h1>
    <p class="hero-subtitle">查看个人资料、使用统计、套餐信息和安全设置</p>
</div>
""", unsafe_allow_html=True)

# ── 获取当前用户信息 ──────────────────────────────────
current_user = get_current_user()
if not current_user:
    st.warning("请先登录")
    st.stop()

username = current_user.get("username", "")
email = current_user.get("email", "")
tier = current_user.get("tier", "free")
created_at = current_user.get("created_at", "未知")

# ══════════════════════════════════════════════════════════
# Section 1: Profile Card
# ══════════════════════════════════════════════════════════
st.markdown("## 📋 个人资料")

tier_colors = {"free": "#6b7280", "pro": "#3b82f6", "enterprise": "#8b5cf6"}
tier_labels = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}
tier_color = tier_colors.get(tier, "#6b7280")
tier_label = tier_labels.get(tier, tier)

st.markdown(f"""
<div class="main-form">
    <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
        <div style="font-size:2.5rem;">👤</div>
        <div>
            <div style="font-size:1.3rem; font-weight:700; color:#1e3a5f;">{username}</div>
            <div style="color:#6b7280; font-size:0.9rem;">{email if email else "未设置邮箱"}</div>
        </div>
        <div style="margin-left:auto;">
            <span style="background:{tier_color}; color:white; padding:0.3rem 0.8rem;
                         border-radius:12px; font-size:0.85rem; font-weight:600;">
                {tier_label}
            </span>
        </div>
    </div>
    <div style="color:#6b7280; font-size:0.85rem;">
        🗓️ 注册时间: {created_at}
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# Section 2: Usage Statistics
# ══════════════════════════════════════════════════════════
st.markdown("## 📊 使用统计")

config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
daily_limit = config["daily_limit"]
today_usage = get_daily_usage(username)

col_stat1, col_stat2 = st.columns(2)
with col_stat1:
    if daily_limit is not None:
        st.metric("今日已用", f"{today_usage} 次", delta=f"剩余 {daily_limit - today_usage} 次")
        progress_val = today_usage / daily_limit if daily_limit > 0 else 0
        st.progress(min(progress_val, 1.0))
    else:
        st.metric("今日已用", f"{today_usage} 次", delta="无限制")
        st.progress(0.0)

with col_stat2:
    if daily_limit is not None:
        st.metric("每日额度", f"{daily_limit} 次/天")
    else:
        st.metric("每日额度", "无限制")

# 7-day usage history
st.markdown("### 📈 近7天使用记录")
history = get_usage_history(username)
if history:
    hist_cols = st.columns(len(history))
    for i, entry in enumerate(history):
        with hist_cols[i]:
            day_label = entry.get("date", "")[-5:]  # MM-DD format
            count = entry.get("count", 0)
            st.metric(day_label, f"{count} 次")
else:
    st.info("暂无使用记录")

# ══════════════════════════════════════════════════════════
# Section 3: Plan Comparison
# ══════════════════════════════════════════════════════════
st.markdown("## 💎 套餐对比")

plans = [
    {
        "name": "Free",
        "tier_key": "free",
        "limit": "20次/天",
        "color": "#6b7280",
        "features": ["基础AI生成", "开发信撰写", "产品描述", "邮件回复"],
        "missing": ["Logo上传", "数据导出", "优先支持"],
    },
    {
        "name": "Pro",
        "tier_key": "pro",
        "limit": "100次/天",
        "color": "#3b82f6",
        "features": ["基础AI生成", "开发信撰写", "产品描述", "邮件回复", "Logo上传", "数据导出"],
        "missing": ["优先支持"],
    },
    {
        "name": "Enterprise",
        "tier_key": "enterprise",
        "limit": "无限次",
        "color": "#8b5cf6",
        "features": ["基础AI生成", "开发信撰写", "产品描述", "邮件回复", "Logo上传", "数据导出", "优先支持"],
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
                f'当前套餐</div>'
            )

        features_html = ""
        for feat in plan["features"]:
            features_html += f'<div style="padding:0.2rem 0; font-size:0.85rem;">✅ {feat}</div>'
        for feat in plan["missing"]:
            features_html += f'<div style="padding:0.2rem 0; font-size:0.85rem; color:#9ca3af;">❌ {feat}</div>'

        st.markdown(f"""
        <div style="background:white; border-radius:14px; padding:1.5rem;
                    border:{border_style}; text-align:center; min-height:350px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.06);">
            {badge_html}
            <div style="font-size:1.3rem; font-weight:700; color:{plan['color']};">{plan['name']}</div>
            <div style="font-size:1.1rem; font-weight:600; color:#1e3a5f; margin:0.5rem 0;">
                {plan['limit']}
            </div>
            <div style="text-align:left; margin-top:1rem;">
                {features_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Upgrade button for non-enterprise users
if tier != "enterprise":
    st.markdown("")
    if st.button("🚀 升级套餐", type="primary", use_container_width=True):
        st.info("🎉 支付系统即将上线，敬请期待！")

# ══════════════════════════════════════════════════════════
# Section 4: Change Password (not for admin)
# ══════════════════════════════════════════════════════════
if username != "admin":
    st.markdown("## 🔒 修改密码")

    with st.form("change_password_form"):
        old_password = st.text_input("当前密码", type="password", placeholder="请输入当前密码")
        new_password = st.text_input("新密码", type="password", placeholder="请输入新密码（至少4位）")
        confirm_password = st.text_input("确认新密码", type="password", placeholder="请再次输入新密码")

        if st.form_submit_button("✅ 确认修改", use_container_width=True, type="primary"):
            if not old_password:
                st.error("❌ 请输入当前密码")
            elif not new_password:
                st.error("❌ 请输入新密码")
            elif new_password != confirm_password:
                st.error("❌ 两次输入的新密码不一致")
            else:
                success, msg = change_password(username, old_password, new_password)
                if success:
                    st.success("✅ 密码修改成功！")
                else:
                    st.error(f"❌ {msg}")

# ── Footer ──────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 账户管理</div>', unsafe_allow_html=True)
