"""
app.py — 首页（精致紧凑专业化设计 v3）
快捷入口：卡片即按钮，点击直接跳转。
指标区域：浅色柔和配色，高可读性。
"""
import streamlit as st

from config.i18n import t
from utils.logger import configure_logging
from utils.ui_helpers import check_auth, inject_css


def application(environ, start_response):
    """Minimal WSGI fallback for platforms that probe app.py exports.

    The production web process is still Streamlit via Procfile; this keeps
    generic Python app detectors from failing before Streamlit is launched.
    """
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"AI-Trade Pro Streamlit app. Start with: streamlit run app.py"]


def handler(event=None, context=None):
    """Minimal serverless-style fallback for app export probes."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
        "body": "AI-Trade Pro Streamlit app. Start with: streamlit run app.py",
    }


app = application


configure_logging()

st.set_page_config(
    page_title="外贸AI助手 | AI-Trade Pro",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
check_auth()

# ══════════════════════════════════════════════════════════════════════
# 首页专属样式
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Stat Bar: 浅色优雅配色 ── */
.stat-bar {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin: 0.5rem 0 1.6rem;
}
@media (max-width: 768px) { .stat-bar { grid-template-columns: repeat(3, 1fr); } }
.stat-pill {
    background: #ffffff;
    border: 1px solid #e8ecf0;
    border-radius: 12px;
    padding: 14px 16px;
    display: flex; align-items: center; gap: 12px;
    transition: border-color .2s, box-shadow .2s;
}
.stat-pill:hover {
    border-color: #a5b4fc;
    box-shadow: 0 2px 10px rgba(99,102,241,0.08);
}
.stat-pill-icon {
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem; flex-shrink: 0;
}
.stat-pill-val {
    font-size: 1.3rem; font-weight: 800; line-height: 1;
    color: #1e293b;
}
.stat-pill-lbl {
    font-size: 0.72rem; margin-top: 2px;
    color: #64748b;
    font-weight: 500;
}

/* ── Quick Access: 卡片=按钮，紧凑美观 ── */
.qa-section .stButton > button {
    background: #ffffff !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 14px !important;
    padding: 18px 8px 14px !important;
    min-height: 100px !important;
    white-space: pre-line !important;
    line-height: 1.5 !important;
    font-size: 0.78rem !important;
    color: #475569 !important;
    font-weight: 500 !important;
    transition: all .2s ease !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
.qa-section .stButton > button:hover {
    border-color: #6366f1 !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.12) !important;
    transform: translateY(-2px) !important;
    color: #312e81 !important;
    background: linear-gradient(180deg, #ffffff 0%, #f5f3ff 100%) !important;
}
.qa-section .stButton > button:active {
    transform: translateY(0px) !important;
    box-shadow: 0 1px 4px rgba(99,102,241,0.1) !important;
}

/* ── (nav-item styles removed — buttons are now the rows) ── */

/* ── Nav → button: Apple-style 长条按钮 ── */
.nav-section .stButton > button {
    background: #f8f8fa !important;
    color: #1d1d1f !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 500 !important;
    font-size: 0.92rem !important;
    padding: 14px 20px !important;
    text-align: left !important;
    box-shadow: none !important;
    transition: all .2s cubic-bezier(.4,0,.2,1) !important;
    margin-bottom: 6px !important;
    letter-spacing: -0.01em !important;
    -webkit-font-smoothing: antialiased !important;
}
.nav-section .stButton > button:hover {
    background: #f0eef5 !important;
    color: #1d1d1f !important;
    box-shadow: none !important;
    transform: scale(0.985) !important;
}
.nav-section .stButton > button:active {
    background: #e8e6ef !important;
    transform: scale(0.975) !important;
    transition: all .08s !important;
}

/* ── Tips row ── */
.tips-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 0.6rem 0 1rem;
}
@media (max-width: 768px) { .tips-grid { grid-template-columns: repeat(2, 1fr); } }
.tip-pill {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 18px;
    font-size: 0.88rem; line-height: 1.55;
    color: #64748b;
    border-top: 3px solid #6366f1;
}
.tip-pill strong { color: #1e293b; display: block; margin-bottom: 5px; font-size: 0.92rem; }

/* ── Hero: 改为深蓝紫渐变，白色文字高对比 ── */
.hero-section {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 30%, #4338ca 65%, #6366f1 100%) !important;
    padding: 2.4rem 2.2rem 2rem !important;
    margin-bottom: 1.4rem !important;
    border-radius: 20px !important;
}
.hero-badge {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    color: #e0e7ff !important;
}
.hero-title {
    font-size: 2.1rem !important;
    color: #ffffff !important;
}
.hero-title span { color: #a5b4fc !important; }
.hero-subtitle {
    font-size: 0.92rem !important;
    color: #c7d2fe !important;
    opacity: 1 !important;
}
.hero-tags { margin-top: 1rem !important; gap: 6px !important; }
.hero-tag {
    font-size: 0.72rem !important;
    padding: 4px 11px !important;
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #e0e7ff !important;
}
.hero-stats {
    gap: 1.6rem !important; margin-top: 1.3rem !important;
    padding-top: 1.1rem !important;
    border-top: 1px solid rgba(255,255,255,0.12) !important;
}
.hero-stat-num { font-size: 1.35rem !important; color: #ffffff !important; }
.hero-stat-lbl { color: #a5b4fc !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-section">
  <div class="hero-badge">✦ AI-Powered · 外贸全流程 · 7 种语言</div>
  <h1 class="hero-title">让 AI 替你写每一封<span>外贸邮件</span></h1>
  <p class="hero-subtitle">
    开发信 · 询盘回复 · 报价单 · 合同 · 节日问候 · 谈判话术 —
    一站式 AI 外贸助手，30 秒完成过去 30 分钟的工作
  </p>
  <div class="hero-tags">
    <span class="hero-tag">⚡ 流式生成</span>
    <span class="hero-tag">🌍 多语言</span>
    <span class="hero-tag">📄 PDF</span>
    <span class="hero-tag">🤖 自定义模型</span>
    <span class="hero-tag">📊 CRM</span>
    <span class="hero-tag">🔒 数据安全</span>
  </div>

</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# 平台概览指标（浅色柔和配色）
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="stat-bar">
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#eef2ff;">🧩</div><div><div class="stat-pill-val">30+</div><div class="stat-pill-lbl">功能页面</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#ecfdf5;">🌍</div><div><div class="stat-pill-val">7</div><div class="stat-pill-lbl">输出语言</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#faf5ff;">📄</div><div><div class="stat-pill-val">4</div><div class="stat-pill-lbl">PDF 文档</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#fffbeb;">🤖</div><div><div class="stat-pill-val">16+</div><div class="stat-pill-lbl">AI 场景</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#f0f9ff;">📊</div><div><div class="stat-pill-val">CRM</div><div class="stat-pill-lbl">客户管理</div></div></div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# 快捷入口 — 卡片即按钮，合二为一（每个按钮就是卡片）
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">快捷入口</div>', unsafe_allow_html=True)

QUICK_ACCESS = [
    ("📧", "开发信",    "AI 高转化冷邮件",    "pages/1_📧_开发信.py"),
    ("📩", "询盘回复",  "逐条回答+报价",      "pages/2_📩_询盘回复.py"),
    ("📄", "报价单",    "多SKU专业PDF",       "pages/3_📄_报价单.py"),
    ("📬", "跟进邮件",  "5阶段智能跟进",      "pages/5_📬_跟进邮件.py"),
    ("💰", "智能报价",  "AI定价策略",         "pages/17_💰_智能报价.py"),
    ("🗣️", "谈判话术",  "6场景应对脚本",      "pages/13_🗣️_谈判话术.py"),
    ("🔍", "意图识别",  "分析回复意图",       "pages/26_🔍_意图识别.py"),
    ("🏷️", "HS编码",    "AI建议+关税",        "pages/27_🏷️_HS编码.py"),
    ("👤", "客户画像",  "B2B企业分析",        "pages/28_👤_客户画像.py"),
    ("🌐", "邮件润色",  "翻译+润色+对比",     "pages/15_🌐_邮件润色.py"),
]

# 用 CSS class 包裹 → 让按钮继承卡片样式
st.markdown('<div class="qa-section">', unsafe_allow_html=True)
for row_start in range(0, len(QUICK_ACCESS), 5):
    row_items = QUICK_ACCESS[row_start:row_start + 5]
    cols = st.columns(len(row_items))
    for col, (icon, title, desc, page) in zip(cols, row_items):
        with col:
            # 按钮文本用换行分隔 icon / title / desc
            btn_label = f"{icon}\n{title}\n{desc}"
            if st.button(btn_label, key=f"qa_{row_start}_{title}", use_container_width=True):
                st.switch_page(page)
st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# 全功能分类导航
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">全功能导航</div>', unsafe_allow_html=True)
st.markdown('<div class="nav-section">', unsafe_allow_html=True)

tab_email, tab_doc, tab_crm, tab_tools, tab_platform = st.tabs([
    "📧 邮件", "📝 文案", "👥 CRM", "🔧 工具", "⚙️ 设置",
])


def _nav_section(items):
    """每行是一个可点击按钮，整行跳转，无需单独箭头"""
    for icon, title, desc, page in items:
        if st.button(
            f"{icon}  {title}  —  {desc}",
            key=f"nav_{icon}_{title}",
            use_container_width=True,
        ):
            st.switch_page(page)


with tab_email:
    _nav_section([
        ("📧", "开发信",    "AI 高转化冷邮件 + Subject",     "pages/1_📧_开发信.py"),
        ("📩", "询盘回复",  "逐条回答 + 报价区间",           "pages/2_📩_询盘回复.py"),
        ("📬", "跟进邮件",  "5阶段智能跟进",                 "pages/5_📬_跟进邮件.py"),
        ("📨", "批量开发信", "CSV批量个性化发送",            "pages/12_📨_批量开发信.py"),
        ("🗣️", "谈判话术",  "6场景谈判应对",                "pages/13_🗣️_谈判话术.py"),
        ("🎄", "节日问候",  "文化适配祝福邮件",             "pages/14_🎄_节日问候.py"),
        ("🌐", "邮件润色",  "翻译+润色+对比",               "pages/15_🌐_邮件润色.py"),
        ("😟", "投诉处理",  "专业客诉回复",                 "pages/16_😟_投诉处理.py"),
        ("🔍", "意图识别",  "分析邮件真实意图",             "pages/26_🔍_意图识别.py"),
        ("🔁", "批量生成",  "多策略批量对比",               "pages/24_🔁_批量生成.py"),
    ])

with tab_doc:
    _nav_section([
        ("📑", "产品介绍",  "5语言产品文案",                "pages/4_📑_产品介绍.py"),
        ("🛒", "产品上架",  "Amazon/Shopify Listing",       "pages/6_🛒_产品上架.py"),
        ("💬", "社媒文案",  "LinkedIn/IG/FB",               "pages/8_💬_社媒文案.py"),
        ("💰", "智能报价",  "AI定价策略分析",               "pages/17_💰_智能报价.py"),
        ("🧪", "AB测试",    "邮件变体对比",                 "pages/21_▪_AB测试.py"),
        ("🏆", "竞品分析",  "Battle Card + 话术",           "pages/32_🏆_竞品分析.py"),
        ("📝", "合同模板",  "6类国际贸易合同",              "pages/29_📝_合同模板.py"),
    ])

with tab_crm:
    _nav_section([
        ("📇", "客户管理",  "CRM+评分+标签",                "pages/7_📇_客户管理.py"),
        ("📅", "跟进日历",  "自动提醒+邮件推送",            "pages/10_📅_跟进日历.py"),
        ("📊", "客户分析",  "转化漏斗+地区分布",            "pages/20_🔍_客户分析.py"),
        ("👤", "客户画像",  "B2B企业深度分析",              "pages/28_👤_客户画像.py"),
        ("📈", "仪表盘",    "核心指标可视化",               "pages/33_📊_仪表盘.py"),
    ])

with tab_tools:
    _nav_section([
        ("📄", "报价单PDF", "多SKU专业PDF",                 "pages/3_📄_报价单.py"),
        ("📜", "形式发票",  "Proforma Invoice",             "pages/25_📜_形式发票.py"),
        ("▪",  "装箱发票",  "Packing List+商业发票",        "pages/19_▪_装箱发票.py"),
        ("📦", "装箱计算",  "20/40GP装载优化",              "pages/18_📦_装箱计算.py"),
        ("🏷️", "HS编码",    "AI建议+关税",                  "pages/27_🏷️_HS编码.py"),
        ("🚢", "提单解读",  "B/L字段+风险提示",             "pages/30_🚢_提单解读.py"),
        ("💱", "汇率计算",  "实时多币种换算",               "pages/31_💱_汇率计算.py"),
    ])

with tab_platform:
    _nav_section([
        ("⚙️", "AI偏好",    "预填+风格+自定义模型",         "pages/0_⚙️_AI偏好.py"),
        ("📋", "历史记录",  "生成结果归档",                 "pages/9_📋_历史记录.py"),
        ("📈", "数据导出",  "JSON/CSV备份",                 "pages/22_📈_数据导出.py"),
        ("💳", "套餐升级",  "Free/Pro/Enterprise",          "pages/23_💳_套餐升级.py"),
        ("👤", "账户管理",  "资料+密码+套餐",               "pages/11_👤_账户管理.py"),
    ])

st.markdown('</div>', unsafe_allow_html=True)  # close nav-section

# ══════════════════════════════════════════════════════════════════════
# 使用技巧
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="section-label">使用技巧</div>
<div class="tips-grid">
  <div class="tip-pill"><strong>⚡ 流式实时输出</strong>所有 AI 功能逐字流式显示，无需等待即可预览。</div>
  <div class="tip-pill"><strong>⚙️ 一次设置全用</strong>「AI 偏好」页设置公司信息，全站自动预填。</div>
  <div class="tip-pill"><strong>🔑 接入任意模型</strong>SiliconFlow / Moonshot / Groq / Ollama 等。</div>
  <div class="tip-pill"><strong>📅 跟进不漏单</strong>自动提醒 3天/1周/2周/1月 + 邮件推送。</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    '<div class="footer">'
    '💼 <strong>AI-Trade Pro</strong> &nbsp;·&nbsp; '
    '外贸全流程 AI 助手 &nbsp;·&nbsp; '
    'Powered by NVIDIA NIM · OpenAI · DeepSeek'
    '</div>',
    unsafe_allow_html=True,
)
