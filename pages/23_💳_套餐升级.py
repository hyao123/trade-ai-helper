"""
pages/23_💳_套餐升级.py
套餐升级页：三档套餐对比、Stripe 支付、验证支付。
"""
from __future__ import annotations

import streamlit as st

from config.i18n import t
from utils.payment import (
    STRIPE_AVAILABLE,
    complete_upgrade,
    create_checkout_session,
    is_payment_configured,
)
from utils.pricing import TIER_CONFIG, get_daily_usage
from utils.ui_helpers import check_auth, inject_css
from utils.user_auth import get_current_user

st.set_page_config(page_title="套餐升级 | 外贸AI助手", page_icon="💳", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">💳 套餐升级</h1>
    <p class="hero-subtitle">解锁 Pro / Enterprise 功能 · Logo 上传 · 无限导出 · 优先支持</p>
</div>
""", unsafe_allow_html=True)

current_user = get_current_user()
if not current_user:
    st.warning(t("please_login"))
    st.stop()

username = current_user.get("username", "")
tier = current_user.get("tier", "free")

# ── 当前用量摘要 ──────────────────────────────────────
config = TIER_CONFIG.get(tier, TIER_CONFIG["free"])
daily_limit = config["daily_limit"]
today_usage = get_daily_usage(username)

tier_badge_colors = {"free": "#6b7280", "pro": "#3b82f6", "enterprise": "#8b5cf6"}
tier_badge = f"""<span style="background:{tier_badge_colors.get(tier,'#6b7280')};
    color:white; padding:0.3rem 0.8rem; border-radius:12px;
    font-size:0.9rem; font-weight:700;">{tier.upper()}</span>"""

usage_str = f"{today_usage}/{daily_limit}" if daily_limit else f"{today_usage}/∞"
st.markdown(
    f'<div class="main-form" style="display:flex;align-items:center;gap:1rem;">'
    f'  <span style="font-size:1.5rem;">👤</span>'
    f'  <span style="font-size:1.1rem;font-weight:600;">{username}</span>'
    f'  {tier_badge}'
    f'  <span style="margin-left:auto;color:#6b7280;">今日已用 {usage_str} 次</span>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# ══════════════════════════════════════════════════════
# 套餐对比卡片
# ══════════════════════════════════════════════════════
st.markdown("### 🎯 选择适合你的套餐")

PLANS = [
    {
        "key": "free",
        "name": "Free",
        "price_cny": "免费",
        "price_usd": "$0/月",
        "color": "#6b7280",
        "limit": "20 次/天",
        "highlight": False,
        "features": [
            "✅ 开发信 / 询盘回复 / 跟进邮件",
            "✅ 多语种产品介绍",
            "✅ Amazon/Shopify Listing",
            "✅ 社媒文案生成",
            "✅ 客户 CRM + 跟进日历",
            "✅ 智能报价建议",
            "✅ 装箱计算器",
            "✅ 装箱发票 PDF",
            "✅ 客户分析仪表盘",
            "✅ A/B 测试框架",
            "❌ Logo 上传",
            "❌ 数据导出/导入",
            "❌ 优先技术支持",
        ],
    },
    {
        "key": "pro",
        "name": "Pro",
        "price_cny": "¥99/月",
        "price_usd": "$29/月",
        "color": "#3b82f6",
        "limit": "100 次/天",
        "highlight": True,  # 推荐
        "features": [
            "✅ Free 全部功能",
            "✅ **100 次/天 AI 生成**",
            "✅ **Logo 上传**（PDF 报价单）",
            "✅ **数据导出/导入**（JSON + CSV）",
            "✅ 优先邮件支持",
            "❌ 企业级 SLA",
            "❌ 专属客服",
        ],
    },
    {
        "key": "enterprise",
        "name": "Enterprise",
        "price_cny": "¥299/月",
        "price_usd": "$99/月",
        "color": "#8b5cf6",
        "limit": "无限次/天",
        "highlight": False,
        "features": [
            "✅ Pro 全部功能",
            "✅ **无限次 AI 生成**",
            "✅ **优先支持** (< 4h 响应)",
            "✅ 企业级 SLA",
            "✅ 专属客户成功经理",
            "✅ 自定义 AI 模型接入",
        ],
    },
]

cols = st.columns(3)
for i, plan in enumerate(PLANS):
    with cols[i]:
        is_current = plan["key"] == tier
        border = f"3px solid {plan['color']}" if is_current or plan["highlight"] else "1px solid #e5e7eb"
        bg = f"linear-gradient(135deg, {'#eff6ff' if plan['highlight'] else '#fff'} 0%, #fff 100%)"

        badge_html = ""
        if is_current:
            badge_html = f'<div style="background:{plan["color"]};color:white;padding:0.2rem 0.7rem;border-radius:8px;font-size:0.75rem;font-weight:700;display:inline-block;margin-bottom:0.5rem;">当前套餐</div>'
        elif plan["highlight"]:
            badge_html = '<div style="background:#f59e0b;color:white;padding:0.2rem 0.7rem;border-radius:8px;font-size:0.75rem;font-weight:700;display:inline-block;margin-bottom:0.5rem;">⭐ 推荐</div>'

        feats_html = "".join(
            f'<div style="padding:0.25rem 0;font-size:0.85rem;">{f}</div>'
            for f in plan["features"]
        )

        st.markdown(f"""
        <div style="background:{bg};border-radius:14px;padding:1.5rem;
                    border:{border};text-align:center;min-height:480px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:0.5rem;">
            {badge_html}
            <div style="font-size:1.4rem;font-weight:700;color:{plan['color']};margin-bottom:0.3rem;">
                {plan['name']}
            </div>
            <div style="font-size:1.6rem;font-weight:800;color:#1e3a5f;">
                {plan['price_cny']}
            </div>
            <div style="font-size:0.85rem;color:#6b7280;margin-bottom:0.3rem;">
                {plan['price_usd']} · {plan['limit']}
            </div>
            <hr style="border-top:1px dashed #e5e7eb;margin:0.75rem 0;">
            <div style="text-align:left;">{feats_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Upgrade button
        tier_order = ["free", "pro", "enterprise"]
        current_idx = tier_order.index(tier) if tier in tier_order else 0
        plan_idx = tier_order.index(plan["key"])

        if plan_idx > current_idx:
            btn_label = f"升级到 {plan['name']}"
            if st.button(btn_label, key=f"upgrade_btn_{plan['key']}", use_container_width=True, type="primary"):
                if not STRIPE_AVAILABLE:
                    st.info("💡 支付功能仅在云端部署时可用（Stripe SDK 未安装）")
                elif not is_payment_configured():
                    st.info("💡 支付系统配置中，请联系管理员或稍后再试。")
                    # Demo: show simulated upgrade for testing
                    st.markdown("**演示模式：** 真实支付上线前，请联系 [support@tradeai.pro](mailto:support@tradeai.pro) 获取优惠价格。")
                else:
                    with st.spinner("正在创建支付会话..."):
                        success, result = create_checkout_session(username, plan["key"])
                    if success:
                        st.success("✅ 支付会话已创建！")
                        st.markdown(
                            f'<a href="{result}" target="_blank">'
                            f'<button style="width:100%;background:#3b82f6;color:white;border:none;'
                            f'border-radius:8px;padding:0.6rem;font-weight:700;cursor:pointer;font-size:1rem;">'
                            f'💳 前往 Stripe 支付</button></a>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error(f"❌ {result}")
        elif is_current:
            st.button("✅ 当前套餐", key=f"current_btn_{plan['key']}", use_container_width=True, disabled=True)

st.markdown("---")

# ══════════════════════════════════════════════════════
# 支付验证
# ══════════════════════════════════════════════════════
if tier != "enterprise":
    with st.expander("🔍 已付款？验证支付并升级", expanded=False):
        st.markdown("完成 Stripe 支付后，将支付会话 ID 粘贴到下方进行验证。")
        session_id = st.text_input("Stripe 支付会话 ID", placeholder="cs_live_xxxxxxxxxxxx", key="payment_session_id_upgrade")
        if st.button("✅ 验证并升级", type="primary", use_container_width=True, key="verify_upgrade_btn"):
            if not session_id.strip():
                st.warning("请输入支付会话 ID")
            else:
                with st.spinner("正在验证支付..."):
                    success, msg = complete_upgrade(username, session_id.strip())
                if success:
                    st.success(f"🎉 {msg}！请刷新页面查看新套餐。")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ 验证失败：{msg}")

# ══════════════════════════════════════════════════════
# FAQ
# ══════════════════════════════════════════════════════
st.markdown("### ❓ 常见问题")

with st.expander("💬 支付后多久生效？"):
    st.markdown("支付完成后，在本页面输入 **Stripe 支付会话 ID** 即可立即生效，无需等待。")

with st.expander("💬 可以随时取消吗？"):
    st.markdown("套餐为一次性购买（按月），到期后不会自动续费。如需继续使用，到期前手动续费即可。")

with st.expander("💬 数据会丢失吗？"):
    st.markdown("降级不会删除数据，只是限制功能访问。Pro 功能（Logo、导出）降级后暂时不可用，升级后立即恢复。")

with st.expander("💬 企业团队采购？"):
    st.markdown("如需 5+ 账号团队采购或私有化部署，请发邮件至 **support@tradeai.pro** 获取报价。")

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 套餐升级</div>', unsafe_allow_html=True)
