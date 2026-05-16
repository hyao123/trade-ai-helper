"""
app.py — 首页（仪表盘 + 快捷入口）
"""
import streamlit as st

from config.i18n import t
from utils.logger import configure_logging
from utils.ui_helpers import check_auth, inject_css

configure_logging()

st.set_page_config(
    page_title="外贸AI助手 | TradeAI Pro",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
check_auth()

# ── Hero（精简版）──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-section">
    <h1 class="hero-title">{t('hero_title')}</h1>
    <p class="hero-subtitle">{t('hero_subtitle')}</p>
    <div class="price-tag">
        <span>{t('free_trial')}</span>
        <span style="font-weight:700;font-size:1.1rem;">{t('per_hour_20')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 快捷入口（高频功能 Top 8）──────────────────────────────────────────────
st.markdown(f"### 🚀 {t('select_function')}")

QUICK_ACCESS = [
    {"icon": "📧", "title": "开发信", "page": "pages/1_📧_开发信.py"},
    {"icon": "📩", "title": "询盘回复", "page": "pages/2_📩_询盘回复.py"},
    {"icon": "📄", "title": "报价单", "page": "pages/3_📄_报价单.py"},
    {"icon": "📬", "title": "跟进邮件", "page": "pages/5_📬_跟进邮件.py"},
    {"icon": "💰", "title": "智能报价", "page": "pages/17_💰_智能报价.py"},
    {"icon": "📦", "title": "装箱计算", "page": "pages/18_📦_装箱计算器.py"},
    {"icon": "🔍", "title": "意图识别", "page": "pages/26_🔍_意图识别.py"},
    {"icon": "🏷️", "title": "HS编码", "page": "pages/27_🏷️_HS编码.py"},
]

cols = st.columns(4)
for i, item in enumerate(QUICK_ACCESS):
    with cols[i % 4]:
        st.markdown(
            f'<div class="main-form" style="text-align:center;padding:1.2rem;cursor:pointer;">'
            f'<div style="font-size:2rem;">{item["icon"]}</div>'
            f'<div style="font-size:0.9rem;font-weight:600;color:#1e3a5f;margin-top:0.3rem;">{item["title"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(f"{t('enter_feature')} {item['title']}", key=f"qa_{item['title']}", use_container_width=True):
            st.switch_page(item["page"])

st.markdown("---")

# ── 平台概览指标 ──────────────────────────────────────────────────────────
st.markdown("### 📊 平台概览")
m1, m2, m3, m4 = st.columns(4)
m1.metric("🧩 功能页面", "28")
m2.metric("🌍 语言支持", "7 种")
m3.metric("📥 PDF 文档", "4 类")
m4.metric("🤖 AI 场景", "16 个")

st.markdown("---")

# ── 功能分类导航（替代原来的全量卡片网格）──────────────────────────────────
st.markdown("### 📁 功能分类")

tab_email, tab_content, tab_tools, tab_platform = st.tabs([
    "📧 邮件 & 沟通", "📝 文案 & 内容", "🔧 贸易工具", "⚙️ 平台 & 设置"
])

with tab_email:
    items = [
        ("📧 开发信生成", "AI 撰写高转化冷邮件 + Subject Line", "pages/1_📧_开发信.py"),
        ("📩 询盘回复", "逐条回答客户问题，给出报价区间", "pages/2_📩_询盘回复.py"),
        ("📬 跟进邮件", "5阶段智能跟进邮件", "pages/5_📬_跟进邮件.py"),
        ("📨 批量开发信", "CSV上传，批量个性化发送", "pages/12_📨_批量开发信.py"),
        ("🔁 批量生成", "同一产品多策略批量生成", "pages/24_🔁_批量生成.py"),
        ("🗣️ 谈判话术", "6种场景谈判应对脚本", "pages/13_🗣️_谈判话术.py"),
        ("🎄 节日问候", "文化适配节日祝福邮件", "pages/14_🎄_节日问候.py"),
        ("🌐 邮件润色", "翻译 + 润色 + 对比", "pages/15_🌐_邮件润色.py"),
        ("😟 投诉处理", "专业客诉回复生成", "pages/16_😟_投诉处理.py"),
        ("🔍 意图识别", "分析客户回复邮件意图", "pages/26_🔍_意图识别.py"),
    ]
    for title, desc, page in items:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**{title}** — {desc}")
        with c2:
            if st.button("进入", key=f"cat_{title}", use_container_width=True):
                st.switch_page(page)

with tab_content:
    items = [
        ("📑 多语种产品介绍", "英/西/法/德/日 5语言", "pages/4_📑_产品介绍.py"),
        ("🛒 产品上架", "Amazon/Shopify Listing", "pages/6_🛒_产品上架.py"),
        ("💬 社媒文案", "LinkedIn/IG/Facebook", "pages/8_💬_社媒文案.py"),
        ("💰 智能报价", "AI 定价策略分析", "pages/17_💰_智能报价.py"),
        ("🧪 A/B 测试", "邮件变体对比优化", "pages/21_🧪_AB测试.py"),
    ]
    for title, desc, page in items:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**{title}** — {desc}")
        with c2:
            if st.button("进入", key=f"cat_{title}", use_container_width=True):
                st.switch_page(page)

with tab_tools:
    items = [
        ("📄 报价单 PDF", "多SKU专业PDF报价单", "pages/3_📄_报价单.py"),
        ("📜 形式发票", "Proforma Invoice PDF", "pages/25_📜_形式发票.py"),
        ("📋 装箱发票", "Packing List + 商业发票", "pages/19_📋_装箱发票.py"),
        ("📦 装箱计算器", "20GP/40GP/40HQ装载优化", "pages/18_📦_装箱计算器.py"),
        ("🏷️ HS编码查询", "AI建议HS Code+关税", "pages/27_🏷️_HS编码.py"),
        ("📇 客户管理", "CRM + 评分 + 标签", "pages/7_📇_客户管理.py"),
        ("📅 跟进日历", "自动提醒 + 邮件推送", "pages/10_📅_跟进日历.py"),
        ("📊 客户分析", "转化漏斗 + 地区分布", "pages/20_📊_客户分析.py"),
    ]
    for title, desc, page in items:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**{title}** — {desc}")
        with c2:
            if st.button("进入", key=f"cat_{title}", use_container_width=True):
                st.switch_page(page)

with tab_platform:
    items = [
        ("⚙️ AI偏好设置", "公司预填 + 风格 + 指令", "pages/0_⚙️_AI偏好.py"),
        ("📋 历史记录", "所有生成结果归档", "pages/9_📋_历史记录.py"),
        ("📈 数据导出", "JSON/CSV备份 (Pro)", "pages/22_📈_数据导出.py"),
        ("💳 套餐升级", "Free/Pro/Enterprise", "pages/23_💳_套餐升级.py"),
        ("👤 账户管理", "资料 + 密码 + 套餐", "pages/11_👤_账户管理.py"),
    ]
    for title, desc, page in items:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**{title}** — {desc}")
        with c2:
            if st.button("进入", key=f"cat_{title}", use_container_width=True):
                st.switch_page(page)

st.markdown("---")

# ── 使用提示 ─────────────────────────────────────────────────────────────
st.markdown(f"### 💡 {t('usage_tips')}")
t1, t2 = st.columns(2)
with t1:
    st.info("**⚡ 流式输出**\n\n所有 AI 生成功能支持实时流式显示。")
    st.info("**💬 多轮对话**\n\n开发信和询盘回复支持生成后「继续优化」，直到满意。")
with t2:
    st.info("**⚙️ 一次设置**\n\n在「AI偏好」页设置公司信息和风格，全站自动预填。")
    st.info("**📅 不漏单**\n\n跟进日历自动提醒 3天/1周/2周/1月，配合邮件推送。")

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f'<div class="footer">{t("footer")}</div>', unsafe_allow_html=True)
