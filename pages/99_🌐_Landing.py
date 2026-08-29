"""
pages/99_🌐_Landing.py
商业化落地页：产品价值展示 + 等候名单注册 + 定价方案
这是面向新用户的第一印象页面，无需登录即可访问。
"""
from __future__ import annotations

import datetime
import re

import streamlit as st

from utils.analytics import track_event
from utils.storage import load_json, save_json


def _is_valid_email(value: str) -> bool:
    """Basic email format check (e.g. user@example.com)."""
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value) is not None

st.set_page_config(page_title="外贸AI助手 | TradeAI Pro", page_icon="💼", layout="wide")

# ── 全局样式 ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;600;700&display=swap');
* { font-family: 'Noto Sans SC', sans-serif !important; }

.landing-hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 40%, #3b82f6 100%);
    padding: 4rem 2rem; border-radius: 20px; color: white;
    text-align: center; margin-bottom: 2rem;
}
.landing-hero h1 { font-size: 2.8rem; font-weight: 700; margin-bottom: 0.5rem; }
.landing-hero p { font-size: 1.2rem; opacity: 0.9; max-width: 600px; margin: 0 auto; }
.landing-hero .cta-badge {
    display: inline-block; margin-top: 1.5rem; padding: 0.6rem 1.5rem;
    background: rgba(255,255,255,0.15); border-radius: 30px;
    font-size: 0.95rem; border: 1px solid rgba(255,255,255,0.3);
}

.feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin: 2rem 0; }
.feature-card {
    background: white; border-radius: 16px; padding: 1.5rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #e5e7eb;
    transition: transform 0.2s, box-shadow 0.2s;
}
.feature-card:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(0,0,0,0.1); }
.feature-icon { font-size: 2rem; margin-bottom: 0.75rem; }
.feature-title { font-size: 1.05rem; font-weight: 600; color: #1e3a5f; margin-bottom: 0.5rem; }
.feature-desc { font-size: 0.85rem; color: #6b7280; line-height: 1.6; }

.pricing-table { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin: 2rem 0; }
.pricing-card {
    background: white; border-radius: 16px; padding: 2rem 1.5rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #e5e7eb;
    text-align: center; position: relative;
}
.pricing-card.popular { border: 2px solid #3b82f6; }
.pricing-card.popular::before {
    content: "最受欢迎"; position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
    background: #3b82f6; color: white; padding: 0.25rem 1rem; border-radius: 20px; font-size: 0.75rem;
}
.pricing-name { font-size: 1.1rem; font-weight: 600; color: #1e3a5f; }
.pricing-price { font-size: 2rem; font-weight: 700; color: #1e3a5f; margin: 0.75rem 0; }
.pricing-price span { font-size: 0.9rem; font-weight: 400; color: #6b7280; }
.pricing-features { text-align: left; font-size: 0.85rem; color: #4b5563; line-height: 2; }

.testimonial-card {
    background: #f8fafc; border-radius: 12px; padding: 1.5rem;
    border-left: 4px solid #3b82f6; margin-bottom: 1rem;
}
.testimonial-quote { font-style: italic; color: #374151; margin-bottom: 0.5rem; }
.testimonial-author { font-size: 0.8rem; color: #6b7280; }

.waitlist-section {
    background: linear-gradient(135deg, #eff6ff, #dbeafe);
    border-radius: 16px; padding: 2.5rem; text-align: center; margin: 2rem 0;
}
.stats-row { display: flex; justify-content: center; gap: 3rem; margin: 2rem 0; flex-wrap: wrap; }
.stat-item { text-align: center; }
.stat-number { font-size: 2rem; font-weight: 700; color: #3b82f6; }
.stat-label { font-size: 0.8rem; color: #6b7280; margin-top: 0.25rem; }

.footer-landing { text-align: center; padding: 2rem; color: #9ca3af; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ── Hero Section ──────────────────────────────────────
st.markdown("""
<div class="landing-hero">
    <h1>💼 外贸AI助手</h1>
    <p>从开发信到成单，AI 陪你跑完全程。28+ 智能工具，覆盖外贸全链路。</p>
    <div class="cta-badge">🚀 已有 2,000+ 外贸人在使用 · 平均回复率提升 3.2 倍</div>
</div>
""", unsafe_allow_html=True)

# ── 数据指标 ──────────────────────────────────────────
st.markdown("""
<div class="stats-row">
    <div class="stat-item"><div class="stat-number">28+</div><div class="stat-label">AI 功能</div></div>
    <div class="stat-item"><div class="stat-number">7</div><div class="stat-label">语言支持</div></div>
    <div class="stat-item"><div class="stat-number">3.2x</div><div class="stat-label">回复率提升</div></div>
    <div class="stat-item"><div class="stat-number">50%</div><div class="stat-label">时间节省</div></div>
</div>
""", unsafe_allow_html=True)

# ── 核心功能 ──────────────────────────────────────────
st.markdown("## ✨ 核心功能")
st.markdown("""
<div class="feature-grid">
    <div class="feature-card">
        <div class="feature-icon">📧</div>
        <div class="feature-title">AI 开发信</div>
        <div class="feature-desc">输入产品+客户信息，AI 秒生高转化开发信 + 主题行，支持 7 种语言</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">📨</div>
        <div class="feature-title">批量个性化</div>
        <div class="feature-desc">上传 CSV 客户名单，AI 逐个生成个性化邮件，告别千篇一律</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">🔍</div>
        <div class="feature-title">意图识别</div>
        <div class="feature-desc">AI 分析客户回复邮件意图，自动判断紧急度并建议下一步行动</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">💰</div>
        <div class="feature-title">智能报价</div>
        <div class="feature-desc">基于市场、成本、竞品的 AI 定价策略分析 + 阶梯报价建议</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">📅</div>
        <div class="feature-title">自动跟进</div>
        <div class="feature-desc">3天/1周/2周/1月智能提醒，不漏跟任何商机，邮件自动推送</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">📇</div>
        <div class="feature-title">客户 CRM</div>
        <div class="feature-desc">轻量级客户管理，自动评分+标签+漏斗分析，全程追踪</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">🏷️</div>
        <div class="feature-title">HS编码 + 提单</div>
        <div class="feature-desc">AI 智能匹配 HS 编码、解读提单，减少申报错误</div>
    </div>
    <div class="feature-card">
        <div class="feature-icon">📄</div>
        <div class="feature-title">文档生成</div>
        <div class="feature-desc">报价单、形式发票、装箱单 PDF 一键生成，专业美观</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 用户评价 ──────────────────────────────────────────
st.markdown("## 💬 用户评价")
st.markdown("""
<div class="testimonial-card">
    <div class="testimonial-quote">"以前写一封开发信要 30 分钟，现在 30 秒。上个月用 AI 批量发信拿下了 3 个新客户。"</div>
    <div class="testimonial-author">— 李明, LED 灯具出口 · 深圳</div>
</div>
<div class="testimonial-card">
    <div class="testimonial-quote">"意图识别功能太好用了，客户回复一到就知道该怎么跟进，再也不纠结该怎么回复。"</div>
    <div class="testimonial-author">— Sarah W., 家居用品贸易 · 义乌</div>
</div>
<div class="testimonial-card">
    <div class="testimonial-quote">"智能报价帮我找到了合理定价区间，之前总是凭感觉报价，现在有数据支撑了。"</div>
    <div class="testimonial-author">— 王强, 五金配件 · 佛山</div>
</div>
""", unsafe_allow_html=True)

# ── 定价方案 ──────────────────────────────────────────
st.markdown("## 💎 定价方案")
st.markdown("""
<div class="pricing-table">
    <div class="pricing-card">
        <div class="pricing-name">Free</div>
        <div class="pricing-price">¥0<span>/月</span></div>
        <div class="pricing-features">
            ✅ 5 次/天 AI 生成<br>
            ✅ 基础开发信/询盘回复<br>
            ✅ 客户管理 (20 条)<br>
            ✅ 历史记录保存<br>
            ❌ 批量发信<br>
            ❌ 数据导出
        </div>
    </div>
    <div class="pricing-card popular">
        <div class="pricing-name">Pro</div>
        <div class="pricing-price">¥99<span>/月</span></div>
        <div class="pricing-features">
            ✅ 50 次/天 AI 生成<br>
            ✅ 全部 28+ 功能<br>
            ✅ 批量发信 (CSV)<br>
            ✅ 多模型选择<br>
            ✅ 数据导出 (JSON/CSV)<br>
            ✅ 邮件打开率追踪<br>
            ✅ 优先客服支持
        </div>
    </div>
    <div class="pricing-card">
        <div class="pricing-name">Team</div>
        <div class="pricing-price">¥299<span>/月 (5人)</span></div>
        <div class="pricing-features">
            ✅ 无限 AI 生成<br>
            ✅ 团队协作空间<br>
            ✅ 客户分配 + 公海池<br>
            ✅ 团队业绩看板<br>
            ✅ API 接口<br>
            ✅ 管理员后台<br>
            ✅ 专属客户成功经理
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.caption("💡 所有付费套餐支持 7 天免费试用，不满意随时取消")

# ── 等候名单注册 ──────────────────────────────────────
st.markdown("---")
st.markdown("""
<div class="waitlist-section">
    <h2 style="color:#1e3a5f; margin-bottom:0.5rem;">🎯 加入等候名单，抢先体验</h2>
    <p style="color:#4b5563; margin-bottom:1.5rem;">留下邮箱，新功能上线第一时间通知你，还有独家早鸟优惠</p>
</div>
""", unsafe_allow_html=True)

with st.form("waitlist_form", clear_on_submit=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        waitlist_email = st.text_input(
            "邮箱地址",
            placeholder="your@company.com",
            label_visibility="collapsed",
        )
    with col2:
        submitted = st.form_submit_button("🚀 加入等候名单", use_container_width=True, type="primary")

    if submitted:
        if not waitlist_email or not _is_valid_email(waitlist_email.strip()):
            st.warning("⚠️ 请输入有效的邮箱地址")
        else:
            email_clean = waitlist_email.strip().lower()
            try:
                waitlist = load_json("waitlist.json", default=[])
                existing_emails = {entry["email"].lower() for entry in waitlist}
                if email_clean in existing_emails:
                    st.info("📬 你已经在等候名单中了，我们会尽快联系你！")
                else:
                    waitlist.append({
                        "email": waitlist_email.strip(),
                        "source": "landing_page",
                        "timestamp": datetime.datetime.now().isoformat(),
                    })
                    save_json("waitlist.json", waitlist)
                    track_event("waitlist_signup", {"email": waitlist_email})
                    st.success(f"🎉 成功加入等候名单！我们会在新功能上线时通知 {waitlist_email}")
                    st.balloons()
            except Exception as exc:  # noqa: BLE001 - a write failure must not crash the public landing page
                st.warning("⚠️ 暂时无法保存，请稍后再试。")

# ── FAQ ──────────────────────────────────────────────
st.markdown("---")
st.markdown("## ❓ 常见问题")

with st.expander("AI 生成的邮件质量如何？"):
    st.write("我们使用业界领先的大语言模型（GPT-4o、Llama-3.3-70b 等），并针对外贸场景做了深度 prompt 优化。"
             "同时支持多轮对话优化，直到你满意为止。")

with st.expander("数据安全吗？"):
    st.write("所有数据传输使用 TLS 加密，密码使用 PBKDF2-SHA256 哈希存储。"
             "我们不会将你的客户数据用于模型训练。付费用户支持数据导出和账户删除。")

with st.expander("支持哪些语言？"):
    st.write("目前支持：英语、西班牙语、法语、德语、葡萄牙语、阿拉伯语、俄语。更多语言即将上线。")

with st.expander("可以免费试用吗？"):
    st.write("注册即可获得 Free 套餐（每天 5 次 AI 生成），永久免费。付费套餐支持 7 天无理由退款。")

with st.expander("团队版如何计费？"):
    st.write("Team 套餐 ¥299/月包含 5 个成员席位，超出按 ¥50/人/月 增加。年付享 8 折优惠。")

# ── Footer ──────────────────────────────────────────────
st.markdown("""
<div class="footer-landing">
    💼 外贸AI助手 | TradeAI Pro<br>
    让外贸更简单 · Powered by GPT-4o & Llama-3.3<br>
    <a href="mailto:support@tradeai.pro">support@tradeai.pro</a>
</div>
""", unsafe_allow_html=True)
