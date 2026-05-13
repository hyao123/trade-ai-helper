"""
app.py — 首页（功能入口 + 导航）
"""
import streamlit as st
from utils.logger import configure_logging
from utils.ui_helpers import inject_css, check_auth

configure_logging()

st.set_page_config(
    page_title="外贸AI助手 | TradeAI Pro",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
check_auth()

# ── Hero ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">💼 外贸AI助手</h1>
    <p class="hero-subtitle">AI 赋能外贸 · 开发信 · 询盘回复 · 报价单 · 多语种产品介绍</p>
    <div class="price-tag">
        <span>🆓 免费试用</span>
        <span style="font-weight:700;font-size:1.1rem;">每小时20次</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Stats ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
for col, val, label in [
    (c1, "10",     "核心功能"),
    (c2, "5+",     "语种支持"),
    (c3, "⚡ 流式", "实时输出"),
    (c4, "Listing","Amazon/Shopify"),
    (c5, "PDF",    "多SKU报价单"),
]:
    col.markdown(
        f'<div class="stat-card">'
        f'<div class="stat-value">{val}</div>'
        f'<div class="stat-label">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── 功能卡片导航 ─────────────────────────────────────────────────────────
st.markdown("### 🚀 选择功能开始使用")

FEATURES = [
    {
        "icon": "📧",
        "title": "开发信生成",
        "desc": "输入产品和客户信息，AI 生成高转化英文开发信 + 邮件主题行，支持3种风格",
        "badge": "⚡ 流式输出",
        "page": "pages/1_📧_开发信.py",
    },
    {
        "icon": "📩",
        "title": "询盘回复",
        "desc": "粘贴客户询盘，AI 逐条回答并给出报价区间，省时省力",
        "badge": "⚡ 流式输出",
        "page": "pages/2_📩_询盘回复.py",
    },
    {
        "icon": "📄",
        "title": "报价单 PDF",
        "desc": "支持多产品 SKU，填写交易条款，一键生成专业 PDF 报价单",
        "badge": "📥 多SKU · PDF",
        "page": "pages/3_📄_报价单.py",
    },
    {
        "icon": "📑",
        "title": "多语种产品介绍",
        "desc": "一次输入，同时生成英/西/法/德/日多语言产品文案",
        "badge": "🌍 5 种语言",
        "page": "pages/4_📑_产品介绍.py",
    },
    {
        "icon": "📬",
        "title": "跟进邮件",
        "desc": "按跟进阶段（已报价/发样/谈判/下单/未回复）智能生成跟进邮件",
        "badge": "⚡ 流式输出",
        "page": "pages/5_📬_跟进邮件.py",
    },
    {
        "icon": "🛒",
        "title": "产品上架",
        "desc": "生成 Amazon/Shopify Listing（标题+卖点+描述+搜索词）",
        "badge": "🔥 跨境电商",
        "page": "pages/6_🛒_产品上架.py",
    },
    {
        "icon": "📇",
        "title": "客户管理",
        "desc": "轻量 CRM，记录客户信息，追踪阶段，一键生成邮件",
        "badge": "🆕 CRM",
        "page": "pages/7_📇_客户管理.py",
    },
    {
        "icon": "💬",
        "title": "社媒文案",
        "desc": "生成 LinkedIn/Instagram/Facebook 营销文案，含 hashtag",
        "badge": "🔥 获客利器",
        "page": "pages/8_💬_社媒文案.py",
    },
    {
        "icon": "📋",
        "title": "历史记录",
        "desc": "查看所有 AI 生成结果，随时回看复用，最多保存 50 条",
        "badge": "💾 自动保存",
        "page": "pages/9_📋_历史记录.py",
    },
    {
        "icon": "📅",
        "title": "跟进日历",
        "desc": "记录已发邮件，系统自动提醒 3天/1周/2周/1月 跟进节点",
        "badge": "🤖 自动化",
        "page": "pages/10_📅_跟进日历.py",
    },
]

cols = st.columns(5)
for col, feat in zip(cols[:5], FEATURES[:5]):
    with col:
        st.markdown(
            f"""
            <div class="main-form" style="text-align:center;cursor:pointer;min-height:200px;">
                <div style="font-size:2.5rem;margin-bottom:0.5rem;">{feat['icon']}</div>
                <div class="form-title" style="margin-bottom:0.5rem;">{feat['title']}</div>
                <p style="font-size:0.82rem;color:#6b7280;line-height:1.5;margin-bottom:0.75rem;">
                    {feat['desc']}
                </p>
                <span style="background:#eff6ff;color:#3b82f6;padding:0.2rem 0.6rem;
                             border-radius:12px;font-size:0.75rem;font-weight:600;">
                    {feat['badge']}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"进入 {feat['title']}", key=f"nav_{feat['title']}", use_container_width=True):
            st.switch_page(feat["page"])

cols2 = st.columns(5)
for col, feat in zip(cols2, FEATURES[5:]):
    with col:
        st.markdown(
            f"""
            <div class="main-form" style="text-align:center;cursor:pointer;min-height:200px;">
                <div style="font-size:2.5rem;margin-bottom:0.5rem;">{feat['icon']}</div>
                <div class="form-title" style="margin-bottom:0.5rem;">{feat['title']}</div>
                <p style="font-size:0.82rem;color:#6b7280;line-height:1.5;margin-bottom:0.75rem;">
                    {feat['desc']}
                </p>
                <span style="background:#eff6ff;color:#3b82f6;padding:0.2rem 0.6rem;
                             border-radius:12px;font-size:0.75rem;font-weight:600;">
                    {feat['badge']}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"进入 {feat['title']}", key=f"nav2_{feat['title']}", use_container_width=True):
            st.switch_page(feat["page"])

# ── 使用提示 ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💡 使用提示")
t1, t2, t3, t4 = st.columns(4)
with t1:
    st.info("**⚡ 流式输出**\n\n开发信、询盘回复、产品介绍、跟进邮件均支持实时流式显示，无需等待即可看到内容逐字输出。")
with t2:
    st.info("**📌 邮件主题行**\n\n开发信页面会同时生成 Subject Line，提高开信率，可一键复制直接使用。")
with t3:
    st.info("**📋 一键复制**\n\n所有生成结果均可一键复制到剪贴板，也可下载为 .txt 文件存档。")
with t4:
    st.info("**📅 跟进日历**\n\n发完开发信记录到跟进日历，3天/1周/2周/1月自动提醒，不再漏掉任何商机。")

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 | 让外贸更简单 · Powered by NVIDIA NIM</div>', unsafe_allow_html=True)
