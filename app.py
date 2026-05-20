"""
app.py — 首页（专业化重设计）
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

# ══════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-section">
  <div class="hero-badge">✦ AI-Powered &nbsp;·&nbsp; 外贸全流程覆盖 &nbsp;·&nbsp; 7 种语言</div>
  <h1 class="hero-title">让 AI 替你写每一封<span>外贸邮件</span></h1>
  <p class="hero-subtitle">
    开发信 · 询盘回复 · 报价单 · 合同 · 节日问候 · 谈判话术<br>
    一站式 AI 外贸助手，30 秒完成过去需要 30 分钟的工作
  </p>
  <div class="hero-tags">
    <span class="hero-tag">⚡ 流式生成</span>
    <span class="hero-tag">🌍 多语言输出</span>
    <span class="hero-tag">📄 PDF 导出</span>
    <span class="hero-tag">🤖 自定义模型</span>
    <span class="hero-tag">📊 CRM 管理</span>
    <span class="hero-tag">🔒 数据安全</span>
  </div>
  <div class="hero-stats">
    <div>
      <div class="hero-stat-num">30+</div>
      <div class="hero-stat-lbl">功能模块</div>
    </div>
    <div>
      <div class="hero-stat-num">7</div>
      <div class="hero-stat-lbl">输出语言</div>
    </div>
    <div>
      <div class="hero-stat-num">4</div>
      <div class="hero-stat-lbl">PDF 文档类型</div>
    </div>
    <div>
      <div class="hero-stat-num">∞</div>
      <div class="hero-stat-lbl">自定义模型</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 平台概览指标
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">平台概览</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)

def _stat(col, icon, icon_bg, value, label):
    col.markdown(f"""
    <div class="stat-card">
      <div class="stat-icon" style="background:{icon_bg};">{icon}</div>
      <div>
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

_stat(c1, "🧩", "#eff6ff", "30+", "功能页面")
_stat(c2, "🌍", "#f0fdf4", "7 种",  "输出语言")
_stat(c3, "📄", "#fdf4ff", "4 类",  "PDF 文档")
_stat(c4, "🤖", "#fff7ed", "16+", "AI 场景")
_stat(c5, "📊", "#f0f9ff", "CRM", "客户管理")

# ══════════════════════════════════════════════════════════════
# 快捷入口 — 高频功能 Top 10
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">快捷入口</div>', unsafe_allow_html=True)

QUICK_ACCESS = [
    ("📧", "开发信",    "AI 撰写高转化冷邮件",   "pages/1_📧_开发信.py"),
    ("📩", "询盘回复",  "逐条回答 + 报价区间",   "pages/2_📩_询盘回复.py"),
    ("📄", "报价单",    "多 SKU 专业 PDF",        "pages/3_📄_报价单.py"),
    ("📬", "跟进邮件",  "5 阶段智能跟进",         "pages/5_📬_跟进邮件.py"),
    ("💰", "智能报价",  "AI 定价策略分析",        "pages/17_💰_智能报价.py"),
    ("🗣️", "谈判话术",  "6 场景应对脚本",         "pages/13_🗣️_谈判话术.py"),
    ("🔍", "意图识别",  "分析客户回复意图",       "pages/26_🔍_意图识别.py"),
    ("🏷️", "HS 编码",   "AI 建议 + 关税估算",     "pages/27_🏷️_HS编码.py"),
    ("👤", "客户画像",  "B2B 企业深度分析",       "pages/28_👤_客户画像.py"),
    ("🌐", "邮件润色",  "翻译 + 润色 + 对比",     "pages/15_🌐_邮件润色.py"),
]

cols = st.columns(5)
for i, (icon, title, desc, page) in enumerate(QUICK_ACCESS):
    with cols[i % 5]:
        # 卡片 HTML（纯展示）
        st.markdown(f"""
        <div class="feat-card">
          <span class="feat-icon">{icon}</span>
          <div class="feat-title">{title}</div>
          <div class="feat-desc">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
        # 跳转按钮
        if st.button("进入", key=f"qa_{i}", use_container_width=True):
            st.switch_page(page)

# ══════════════════════════════════════════════════════════════
# 全功能分类导航
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">全功能导航</div>', unsafe_allow_html=True)

tab_email, tab_doc, tab_crm, tab_tools, tab_platform = st.tabs([
    "📧 邮件 & 沟通", "📝 文案 & 内容", "👥 客户 & CRM", "🔧 贸易工具", "⚙️ 平台设置",
])

def _nav_rows(items):
    """渲染带进入按钮的导航行列表"""
    for icon, title, desc, page in items:
        left, right = st.columns([5, 1])
        with left:
            st.markdown(f"""
            <div class="cat-row">
              <span class="cat-row-icon">{icon}</span>
              <span class="cat-row-title">{title}</span>
              <span class="cat-row-desc">— {desc}</span>
            </div>
            """, unsafe_allow_html=True)
        with right:
            if st.button("→", key=f"nav_{title}", use_container_width=True):
                st.switch_page(page)

with tab_email:
    _nav_rows([
        ("📧", "开发信生成",    "AI 撰写高转化冷邮件 + Subject Line",     "pages/1_📧_开发信.py"),
        ("📩", "询盘回复",      "逐条回答客户问题，给出报价区间",         "pages/2_📩_询盘回复.py"),
        ("📬", "跟进邮件",      "5 阶段智能跟进，避免催单尴尬",           "pages/5_📬_跟进邮件.py"),
        ("📨", "批量开发信",    "CSV 上传，批量个性化一键发送",            "pages/12_📨_批量开发信.py"),
        ("🔁", "批量生成",      "同一产品多策略批量生成对比",              "pages/24_🔁_批量生成.py"),
        ("🗣️", "谈判话术",      "砍价/延账期/降MOQ/催货 6 场景",         "pages/13_🗣️_谈判话术.py"),
        ("🎄", "节日问候",      "文化适配的节日祝福邮件",                 "pages/14_🎄_节日问候.py"),
        ("🌐", "邮件润色",      "中英互译 + 专业润色 + 前后对比",         "pages/15_🌐_邮件润色.py"),
        ("😟", "投诉处理",      "质量/延期/短缺 专业客诉回复",            "pages/16_😟_投诉处理.py"),
        ("🔍", "意图识别",      "分析客户回复邮件的真实意图",             "pages/26_🔍_意图识别.py"),
    ])

with tab_doc:
    _nav_rows([
        ("📑", "多语种产品介绍", "英/西/法/德/日 5 语言产品文案",         "pages/4_📑_产品介绍.py"),
        ("🛒", "产品上架",       "Amazon / Shopify 完整 Listing",          "pages/6_🛒_产品上架.py"),
        ("💬", "社媒文案",       "LinkedIn / Instagram / Facebook",         "pages/8_💬_社媒文案.py"),
        ("💰", "智能报价",       "AI 定价策略 + 阶梯报价分析",             "pages/17_💰_智能报价.py"),
        ("🧪", "A/B 测试",       "邮件变体生成 + 效果对比优化",            "pages/21_▪_AB测试.py"),
        ("🔩", "竞品分析",       "差异化策略 + 销售话术 Battle Card",      "pages/32_🏆_竞品分析.py"),
        ("📝", "合同模板",       "销售合同/NDA/独家经销 等 6 类",          "pages/29_📝_合同模板.py"),
    ])

with tab_crm:
    _nav_rows([
        ("📇", "客户管理",      "CRM + 评分 + 标签 + 阶段管理",            "pages/7_📇_客户管理.py"),
        ("📅", "跟进日历",      "自动提醒 + 邮件推送，不漏单",             "pages/10_📅_跟进日历.py"),
        ("📊", "客户分析",      "转化漏斗 + 地区分布 + 行为评分",          "pages/20_🔍_客户分析.py"),
        ("👤", "客户画像",      "B2B 企业深度分析，决策链洞察",            "pages/28_👤_客户画像.py"),
        ("📈", "仪表盘",        "数据总览 + 核心指标可视化",               "pages/33_📊_仪表盘.py"),
        ("💱", "汇率计算",      "实时汇率 + 多币种报价换算",               "pages/31_💱_汇率计算.py"),
    ])

with tab_tools:
    _nav_rows([
        ("📄", "报价单 PDF",    "多 SKU 专业 PDF 报价单生成",              "pages/3_📄_报价单.py"),
        ("📜", "形式发票",      "Proforma Invoice PDF 导出",                "pages/25_📜_形式发票.py"),
        ("▪",  "装箱发票",      "Packing List + 商业发票",                  "pages/19_▪_装箱发票.py"),
        ("📦", "装箱计算",      "20GP/40GP/40HQ 装载率优化",               "pages/18_📦_装箱计算.py"),
        ("🏷️", "HS 编码查询",   "AI 建议 HS Code + 关税估算",              "pages/27_🏷️_HS编码.py"),
        ("🚢", "提单解读",      "B/L 字段提取 + 风险提示",                 "pages/30_🚢_提单解读.py"),
    ])

with tab_platform:
    _nav_rows([
        ("⚙️", "AI 偏好设置",   "公司信息预填 + 风格 + 自定义模型",        "pages/0_⚙️_AI偏好.py"),
        ("📋", "历史记录",      "所有 AI 生成结果归档查询",                "pages/9_📋_历史记录.py"),
        ("📈", "数据导出",      "JSON / CSV 数据备份 (Pro)",               "pages/22_📈_数据导出.py"),
        ("💳", "套餐升级",      "Free · Pro · Enterprise 方案对比",        "pages/23_💳_套餐升级.py"),
        ("👤", "账户管理",      "资料 · 密码 · 套餐 · 邮件通知",           "pages/11_👤_账户管理.py"),
    ])

# ══════════════════════════════════════════════════════════════
# 使用技巧
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">使用技巧</div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.columns(4)
_tips = [
    ("⚡", "流式实时输出",  "所有 AI 功能均支持逐字流式显示，无需等待即可预览内容。"),
    ("⚙️", "一次设置全用",  "在「AI 偏好」页填写公司信息，全站所有表单自动预填，节省时间。"),
    ("🔑", "接入任意模型",  "支持 SiliconFlow、Moonshot、Groq、Ollama 等自定义 Provider。"),
    ("📅", "跟进不漏单",    "跟进日历自动提醒 3天/1周/2周/1月，支持邮件推送到客户。"),
]
for col, (icon, title, desc) in zip([t1, t2, t3, t4], _tips):
    col.markdown(f"""
    <div class="tip-card-pro">
      <strong>{icon} {title}</strong><br>{desc}
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    '<div class="footer">'
    '💼 <strong>TradeAI Pro</strong> &nbsp;·&nbsp; '
    '外贸全流程 AI 助手 &nbsp;·&nbsp; '
    'Powered by NVIDIA NIM · OpenAI · DeepSeek'
    '</div>',
    unsafe_allow_html=True,
)
