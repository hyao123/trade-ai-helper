"""
app.py — 首页（精致紧凑专业化设计）
使用纯 HTML/CSS Grid 渲染快捷卡片和指标区，避免 Streamlit 默认列间距。
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

# ══════════════════════════════════════════════════════════════════════
# 首页专属额外样式（紧凑 grid、微交互）
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Quick Grid ── */
.q-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin: 0.6rem 0 1.2rem;
}
@media (max-width: 992px) { .q-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 600px) { .q-grid { grid-template-columns: repeat(2, 1fr); } }

.q-card {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 14px 10px 12px;
    text-align: center;
    cursor: default;
    transition: all .2s ease;
    position: relative;
    overflow: hidden;
}
.q-card::before {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(135deg, rgba(37,99,235,0.04) 0%, rgba(124,58,237,0.04) 100%);
    opacity: 0; transition: opacity .2s;
}
.q-card:hover::before { opacity: 1; }
.q-card:hover {
    border-color: var(--primary);
    box-shadow: 0 4px 14px rgba(37,99,235,0.12);
    transform: translateY(-2px);
}
.q-card-icon { font-size: 1.6rem; line-height: 1; }
.q-card-title {
    font-size: 0.82rem; font-weight: 700; color: var(--text-1);
    margin-top: 6px; line-height: 1.2;
}
.q-card-desc {
    font-size: 0.68rem; color: var(--text-3); margin-top: 3px;
    line-height: 1.3;
}

/* ── Stat Bar ── */
.stat-bar {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin: 0.4rem 0 1.4rem;
}
@media (max-width: 768px) { .stat-bar { grid-template-columns: repeat(3, 1fr); } }
.stat-pill {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    display: flex; align-items: center; gap: 10px;
}
.stat-pill:hover { border-color: #93c5fd; }
.stat-pill-icon {
    width: 36px; height: 36px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; flex-shrink: 0;
}
.stat-pill-val { font-size: 1.2rem; font-weight: 800; color: var(--text-1); line-height: 1; }
.stat-pill-lbl { font-size: 0.7rem; color: var(--text-2); margin-top: 1px; }

/* ── Nav list compact ── */
.nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid transparent;
    transition: all .15s;
    margin-bottom: 3px;
}
.nav-item:hover { background: var(--primary-light); border-color: #bfdbfe; }
.nav-item-icon { font-size: 1rem; flex-shrink: 0; }
.nav-item-title { font-size: 0.84rem; font-weight: 600; color: var(--text-1); }
.nav-item-desc  { font-size: 0.75rem; color: var(--text-3); }
.nav-item-arr   { margin-left: auto; color: var(--text-3); font-size: 0.8rem; }

/* ── Tips row ── */
.tips-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 0.6rem 0 1rem;
}
@media (max-width: 768px) { .tips-grid { grid-template-columns: repeat(2, 1fr); } }
.tip-pill {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 0.8rem; line-height: 1.5;
    color: var(--text-2);
    border-top: 3px solid var(--primary);
}
.tip-pill strong { color: var(--text-1); display: block; margin-bottom: 4px; font-size: 0.84rem; }

/* ── Compact hero override ── */
.hero-section { padding: 2.2rem 2rem 1.8rem !important; margin-bottom: 1.2rem !important; }
.hero-title { font-size: 2rem !important; }
.hero-subtitle { font-size: 0.9rem !important; }
.hero-stats { gap: 1.4rem !important; margin-top: 1.2rem !important; padding-top: 1rem !important; }
.hero-stat-num { font-size: 1.3rem !important; }
.hero-tags { margin-top: 1rem !important; gap: 6px !important; }
.hero-tag { font-size: 0.72rem !important; padding: 3px 10px !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-section">
  <div class="hero-badge">✦ AI-Powered &nbsp;·&nbsp; 外贸全流程 &nbsp;·&nbsp; 7 种语言</div>
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
    <span class="hero-tag">🔒 安全</span>
  </div>
  <div class="hero-stats">
    <div><div class="hero-stat-num">30+</div><div class="hero-stat-lbl">功能模块</div></div>
    <div><div class="hero-stat-num">7</div><div class="hero-stat-lbl">输出语言</div></div>
    <div><div class="hero-stat-num">4</div><div class="hero-stat-lbl">PDF 文档</div></div>
    <div><div class="hero-stat-num">∞</div><div class="hero-stat-lbl">自定义模型</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# 平台概览指标（纯 HTML Grid，无 st.columns）
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="stat-bar">
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#eff6ff;">🧩</div><div><div class="stat-pill-val">30+</div><div class="stat-pill-lbl">功能页面</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#f0fdf4;">🌍</div><div><div class="stat-pill-val">7</div><div class="stat-pill-lbl">输出语言</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#fdf4ff;">📄</div><div><div class="stat-pill-val">4</div><div class="stat-pill-lbl">PDF 文档类型</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#fff7ed;">🤖</div><div><div class="stat-pill-val">16+</div><div class="stat-pill-lbl">AI 场景</div></div></div>
  <div class="stat-pill"><div class="stat-pill-icon" style="background:#f0f9ff;">📊</div><div><div class="stat-pill-val">CRM</div><div class="stat-pill-lbl">客户管理</div></div></div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# 快捷入口 — 纯 HTML 5 列 Grid（精巧紧凑）
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

# 用纯 HTML Grid 渲染（不用 st.columns）
_cards_html = '<div class="q-grid">'
for icon, title, desc, _ in QUICK_ACCESS:
    _cards_html += f"""
    <div class="q-card">
      <div class="q-card-icon">{icon}</div>
      <div class="q-card-title">{title}</div>
      <div class="q-card-desc">{desc}</div>
    </div>"""
_cards_html += "</div>"
st.markdown(_cards_html, unsafe_allow_html=True)

# 仍需 streamlit 按钮来做路由跳转（但用紧凑的 5 列）
cols = st.columns(5)
for i, (_, title, _, page) in enumerate(QUICK_ACCESS):
    with cols[i % 5]:
        if st.button(title, key=f"qa_{i}", use_container_width=True):
            st.switch_page(page)

# ══════════════════════════════════════════════════════════════════════
# 全功能分类导航
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">全功能导航</div>', unsafe_allow_html=True)

tab_email, tab_doc, tab_crm, tab_tools, tab_platform = st.tabs([
    "📧 邮件", "📝 文案", "👥 CRM", "🔧 工具", "⚙️ 设置",
])


def _nav_section(items):
    """渲染紧凑导航列表，纯 HTML 行 + 小按钮"""
    html_parts = []
    for icon, title, desc, _ in items:
        html_parts.append(
            f'<div class="nav-item">'
            f'<span class="nav-item-icon">{icon}</span>'
            f'<span class="nav-item-title">{title}</span>'
            f'<span class="nav-item-desc">{desc}</span>'
            f'<span class="nav-item-arr">→</span>'
            f'</div>'
        )
    st.markdown("".join(html_parts), unsafe_allow_html=True)
    # 按钮行（紧凑）
    btn_cols = st.columns(min(len(items), 5))
    for idx, (_, title, _, page) in enumerate(items):
        with btn_cols[idx % min(len(items), 5)]:
            if st.button(title, key=f"nav2_{title}", use_container_width=True):
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

# ══════════════════════════════════════════════════════════════════════
# 使用技巧（纯 HTML Grid）
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
    '💼 <strong>TradeAI Pro</strong> &nbsp;·&nbsp; '
    '外贸全流程 AI 助手 &nbsp;·&nbsp; '
    'Powered by NVIDIA NIM · OpenAI · DeepSeek'
    '</div>',
    unsafe_allow_html=True,
)
