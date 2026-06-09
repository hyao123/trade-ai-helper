"""Probe-safe Streamlit entrypoint for AI-Trade Pro.

The module intentionally avoids importing Streamlit at import time so generic
platform probes can import ``app.py`` and find lightweight WSGI/serverless
fallbacks. The actual Streamlit UI is rendered only from ``main()``.
"""

from __future__ import annotations

PROBE_BODY = "AI-Trade Pro Streamlit app. Start with: streamlit run app.py"


def application(environ, start_response):
    """Minimal WSGI fallback for deployment probes."""
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [PROBE_BODY.encode("utf-8")]


def handler(event=None, context=None):
    """Minimal serverless-style fallback for app export probes."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
        "body": PROBE_BODY,
    }


app = application


HOME_CSS = """
<style>
.stat-bar { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 0.5rem 0 1.6rem; }
@media (max-width: 768px) { .stat-bar { grid-template-columns: repeat(3, 1fr); } }
.stat-pill { background: #ffffff; border: 1px solid #e8ecf0; border-radius: 12px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; transition: border-color .2s, box-shadow .2s; }
.stat-pill:hover { border-color: #a5b4fc; box-shadow: 0 2px 10px rgba(99,102,241,0.08); }
.stat-pill-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; flex-shrink: 0; }
.stat-pill-val { font-size: 1.3rem; font-weight: 800; line-height: 1; color: #1e293b; }
.stat-pill-lbl { font-size: 0.72rem; margin-top: 2px; color: #64748b; font-weight: 500; }
.qa-section .stButton > button { background: #ffffff !important; border: 1.5px solid #e2e8f0 !important; border-radius: 14px !important; padding: 18px 8px 14px !important; min-height: 100px !important; white-space: pre-line !important; line-height: 1.5 !important; font-size: 0.78rem !important; color: #475569 !important; font-weight: 500 !important; transition: all .2s ease !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important; }
.qa-section .stButton > button:hover { border-color: #6366f1 !important; box-shadow: 0 4px 16px rgba(99,102,241,0.12) !important; transform: translateY(-2px) !important; color: #312e81 !important; background: linear-gradient(180deg, #ffffff 0%, #f5f3ff 100%) !important; }
.qa-section .stButton > button:active { transform: translateY(0px) !important; box-shadow: 0 1px 4px rgba(99,102,241,0.1) !important; }
.nav-section .stButton > button { background: #f8f8fa !important; color: #1d1d1f !important; border: none !important; border-radius: 12px !important; font-weight: 500 !important; font-size: 0.92rem !important; padding: 14px 20px !important; text-align: left !important; box-shadow: none !important; transition: all .2s cubic-bezier(.4,0,.2,1) !important; margin-bottom: 6px !important; letter-spacing: -0.01em !important; -webkit-font-smoothing: antialiased !important; }
.nav-section .stButton > button:hover { background: #f0eef5 !important; color: #1d1d1f !important; box-shadow: none !important; transform: scale(0.985) !important; }
.nav-section .stButton > button:active { background: #e8e6ef !important; transform: scale(0.975) !important; transition: all .08s !important; }
.tips-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 0.6rem 0 1rem; }
@media (max-width: 768px) { .tips-grid { grid-template-columns: repeat(2, 1fr); } }
.tip-pill { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 18px; font-size: 0.88rem; line-height: 1.55; color: #64748b; border-top: 3px solid #6366f1; }
.tip-pill strong { color: #1e293b; display: block; margin-bottom: 5px; font-size: 0.92rem; }
.hero-section { background: linear-gradient(135deg, #1e1b4b 0%, #312e81 30%, #4338ca 65%, #6366f1 100%) !important; padding: 2.4rem 2.2rem 2rem !important; margin-bottom: 1.4rem !important; border-radius: 20px !important; }
.hero-badge { background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: #e0e7ff !important; }
.hero-title { font-size: 2.1rem !important; color: #ffffff !important; }
.hero-title span { color: #a5b4fc !important; }
.hero-subtitle { font-size: 0.92rem !important; color: #c7d2fe !important; opacity: 1 !important; }
.hero-tags { margin-top: 1rem !important; gap: 6px !important; }
.hero-tag { font-size: 0.72rem !important; padding: 4px 11px !important; background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.15) !important; color: #e0e7ff !important; }
.email-verify-banner { background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%); border: 1px solid #fed7aa; border-left: 5px solid #f97316; border-radius: 16px; padding: 1rem 1.1rem; margin: 0.2rem 0 1.2rem; color: #7c2d12; box-shadow: 0 8px 24px rgba(249,115,22,0.10); }
.email-verify-title { font-weight: 850; font-size: 1rem; color: #9a3412; margin-bottom: 0.25rem; }
.email-verify-copy { font-size: 0.88rem; line-height: 1.65; color: #7c2d12; }
.onboarding-banner { background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%); border: 1px solid #c7d2fe; border-left: 5px solid #6366f1; border-radius: 16px; padding: 1rem 1.1rem; margin: 0.2rem 0 1.2rem; color: #312e81; box-shadow: 0 8px 24px rgba(99,102,241,0.10); }
.onboarding-title { font-weight: 850; font-size: 1rem; color: #312e81; margin-bottom: 0.25rem; }
.onboarding-copy { font-size: 0.88rem; line-height: 1.65; color: #4338ca; }
.onboarding-progress { margin-top: 0.6rem; font-size: 0.78rem; color: #4f46e5; font-weight: 700; }
.next-action-band { margin: 0.1rem 0 1.4rem; }
.next-action-title { font-size: 0.82rem; color: #475569; font-weight: 850; margin-bottom: 0.55rem; }
.next-action-band .stButton > button { min-height: 76px !important; border-radius: 12px !important; border: 1px solid #dbe3ef !important; background: #ffffff !important; color: #1e293b !important; white-space: pre-line !important; line-height: 1.35 !important; font-size: 0.82rem !important; font-weight: 700 !important; box-shadow: 0 1px 3px rgba(15,23,42,0.05) !important; }
.next-action-band .stButton > button:hover { border-color: #6366f1 !important; box-shadow: 0 6px 18px rgba(99,102,241,0.12) !important; transform: translateY(-1px) !important; }
</style>
"""


QUICK_ACCESS = [
    ("🚀", "快速设置", "2分钟初始化资料", "pages/34_🚀_快速设置.py"),
    ("📧", "开发信", "AI 高转化冷邮件", "pages/1_📧_开发信.py"),
    ("📩", "询盘回复", "逐条回答+报价", "pages/2_📩_询盘回复.py"),
    ("📄", "报价单", "多SKU专业PDF", "pages/3_📄_报价单.py"),
    ("📬", "跟进邮件", "5阶段智能跟进", "pages/5_📬_跟进邮件.py"),
    ("💰", "智能报价", "AI定价策略", "pages/17_💰_智能报价.py"),
    ("🗣️", "谈判话术", "6场景应对脚本", "pages/13_🗣️_谈判话术.py"),
    ("🔍", "意图识别", "分析回复意图", "pages/26_🔍_意图识别.py"),
    ("🏷️", "HS编码", "AI建议+关税", "pages/27_🏷️_HS编码.py"),
    ("👤", "客户画像", "B2B企业分析", "pages/28_👤_客户画像.py"),
    ("🌐", "邮件润色", "翻译+润色+对比", "pages/15_🌐_邮件润色.py"),
]


NAV_SECTIONS = {
    "📧 邮件": [
        ("📧", "开发信", "AI 高转化冷邮件 + Subject", "pages/1_📧_开发信.py"),
        ("📩", "询盘回复", "逐条回答 + 报价区间", "pages/2_📩_询盘回复.py"),
        ("📬", "跟进邮件", "5阶段智能跟进", "pages/5_📬_跟进邮件.py"),
        ("📨", "批量开发信", "CSV批量个性化发送", "pages/12_📨_批量开发信.py"),
        ("🗣️", "谈判话术", "6场景谈判应对", "pages/13_🗣️_谈判话术.py"),
        ("🎄", "节日问候", "文化适配祝福邮件", "pages/14_🎄_节日问候.py"),
        ("🌐", "邮件润色", "翻译+润色+对比", "pages/15_🌐_邮件润色.py"),
        ("😟", "投诉处理", "专业客诉回复", "pages/16_😟_投诉处理.py"),
        ("🔍", "意图识别", "分析邮件真实意图", "pages/26_🔍_意图识别.py"),
        ("🔁", "批量生成", "多策略批量对比", "pages/24_🔁_批量生成.py"),
    ],
    "📝 文案": [
        ("📑", "产品介绍", "5语言产品文案", "pages/4_📑_产品介绍.py"),
        ("🛒", "产品上架", "Amazon/Shopify Listing", "pages/6_🛒_产品上架.py"),
        ("💬", "社媒文案", "LinkedIn/IG/FB", "pages/8_💬_社媒文案.py"),
        ("💰", "智能报价", "AI定价策略分析", "pages/17_💰_智能报价.py"),
        ("🧪", "AB测试", "邮件变体对比", "pages/21_▪_AB测试.py"),
        ("🏆", "竞品分析", "Battle Card + 话术", "pages/32_🏆_竞品分析.py"),
        ("📝", "合同模板", "6类国际贸易合同", "pages/29_📝_合同模板.py"),
    ],
    "👥 CRM": [
        ("📇", "客户管理", "CRM+评分+标签", "pages/7_📇_客户管理.py"),
        ("📅", "跟进日历", "自动提醒+邮件推送", "pages/10_📅_跟进日历.py"),
        ("📊", "客户分析", "转化漏斗+地区分布", "pages/20_🔍_客户分析.py"),
        ("👤", "客户画像", "B2B企业深度分析", "pages/28_👤_客户画像.py"),
        ("📈", "仪表盘", "核心指标可视化", "pages/33_📊_仪表盘.py"),
    ],
    "🔧 工具": [
        ("📄", "报价单PDF", "多SKU专业PDF", "pages/3_📄_报价单.py"),
        ("📜", "形式发票", "Proforma Invoice", "pages/25_📜_形式发票.py"),
        ("▪", "装箱发票", "Packing List+商业发票", "pages/19_▪_装箱发票.py"),
        ("📦", "装箱计算", "20/40GP装载优化", "pages/18_📦_装箱计算.py"),
        ("🏷️", "HS编码", "AI建议+关税", "pages/27_🏷️_HS编码.py"),
        ("🚢", "提单解读", "B/L字段+风险提示", "pages/30_🚢_提单解读.py"),
        ("💱", "汇率计算", "实时多币种换算", "pages/31_💱_汇率计算.py"),
    ],
    "⚙️ 设置": [
        ("🚀", "快速设置", "2分钟初始化公司资料", "pages/34_🚀_快速设置.py"),
        ("⚙️", "AI偏好", "预填+风格+自定义模型", "pages/0_⚙️_AI偏好.py"),
        ("📋", "历史记录", "生成结果归档", "pages/9_📋_历史记录.py"),
        ("📈", "数据导出", "JSON/CSV备份", "pages/22_📈_数据导出.py"),
        ("💳", "套餐升级", "Free/Pro/Enterprise", "pages/23_💳_套餐升级.py"),
        ("👤", "账户管理", "资料+密码+套餐", "pages/11_👤_账户管理.py"),
    ],
}


def _render_email_verification_banner(st) -> None:
    """Show a clear home-page reminder when the current user's email is unverified."""
    from utils.repositories import load_user
    from utils.user_auth import get_current_user

    current_user = get_current_user()
    if not current_user or current_user.get("username") in (None, "admin"):
        return

    username = current_user.get("username", "")
    latest_user = load_user(username) or current_user
    if latest_user.get("email_verified") is True:
        st.session_state["current_user"].update(
            {
                "email_verified": True,
                "email": latest_user.get("email", current_user.get("email", "")),
            }
        )
        return

    email = latest_user.get("email") or current_user.get("email") or "你的邮箱"
    st.markdown(
        f"""
        <div class="email-verify-banner">
          <div class="email-verify-title">📮 请先验证邮箱，解锁 AI 生成与套餐升级</div>
          <div class="email-verify-copy">
            我们已为账号 <strong>{username}</strong> 绑定邮箱 <strong>{email}</strong>。
            为确保密码找回和账户通知可用，AI 生成、付费升级和高级功能需要先完成邮箱验证。
            请进入「账户管理」输入验证码，或重新发送验证邮件。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("去账户管理验证邮箱", key="home_verify_email_btn", type="primary"):
        st.switch_page("pages/11_👤_账户管理.py")


def _render_onboarding_banner(st) -> None:
    """Guide new users to complete quick setup when business context is missing."""
    from utils.onboarding import profile_completion
    from utils.user_auth import get_current_user
    from utils.user_prefs import get_prefs

    current_user = get_current_user()
    if not current_user or current_user.get("username") in (None, "admin"):
        return

    prefs = get_prefs()
    completion = profile_completion(prefs)
    if prefs.get("onboarding_completed") == "true" and completion["complete"]:
        return

    st.markdown(
        f"""
        <div class="onboarding-banner">
          <div class="onboarding-title">🚀 完成快速设置，让 AI 更懂你的业务</div>
          <div class="onboarding-copy">
            先填写公司名称、主营产品、目标市场和写作风格，后续开发信、询盘回复、报价和客户跟进会自动带入这些信息，减少重复输入。
          </div>
          <div class="onboarding-progress">当前资料完成度：{completion['completed']}/{completion['total']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("开始 2 分钟快速设置", key="home_onboarding_btn", type="primary"):
        st.switch_page("pages/34_🚀_快速设置.py")


def _render_next_actions(st) -> None:
    """Render prioritized actions for the current user's setup state."""
    from utils.customers import get_customers
    from utils.onboarding import build_home_next_actions
    from utils.user_auth import get_current_user
    from utils.user_prefs import get_prefs

    current_user = get_current_user()
    if not current_user or current_user.get("username") in (None, "admin"):
        return

    try:
        customer_count = len(get_customers())
    except Exception:
        customer_count = 0

    actions = build_home_next_actions(
        user=current_user,
        prefs=get_prefs(),
        customer_count=customer_count,
    )
    if not actions:
        return

    st.markdown('<div class="next-action-band"><div class="next-action-title">下一步建议</div>', unsafe_allow_html=True)
    cols = st.columns(len(actions))
    for col, action in zip(cols, actions):
        with col:
            button_type = "primary" if action.get("priority") == "primary" else "secondary"
            if st.button(
                f"{action['label']}\n{action['detail']}",
                key=f"next_action_{action['id']}",
                type=button_type,
                use_container_width=True,
            ):
                st.switch_page(action["page"])
    st.markdown("</div>", unsafe_allow_html=True)


def _render_home(st) -> None:
    """Render the home page. ``st`` is injected to keep imports out of module scope."""
    st.markdown(HOME_CSS, unsafe_allow_html=True)
    _render_email_verification_banner(st)
    _render_onboarding_banner(st)
    _render_next_actions(st)

    st.markdown(
        """
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
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="stat-bar">
          <div class="stat-pill"><div class="stat-pill-icon" style="background:#eef2ff;">🧩</div><div><div class="stat-pill-val">30+</div><div class="stat-pill-lbl">功能页面</div></div></div>
          <div class="stat-pill"><div class="stat-pill-icon" style="background:#ecfdf5;">🌍</div><div><div class="stat-pill-val">7</div><div class="stat-pill-lbl">输出语言</div></div></div>
          <div class="stat-pill"><div class="stat-pill-icon" style="background:#faf5ff;">📄</div><div><div class="stat-pill-val">4</div><div class="stat-pill-lbl">PDF 文档</div></div></div>
          <div class="stat-pill"><div class="stat-pill-icon" style="background:#fffbeb;">🤖</div><div><div class="stat-pill-val">16+</div><div class="stat-pill-lbl">AI 场景</div></div></div>
          <div class="stat-pill"><div class="stat-pill-icon" style="background:#f0f9ff;">📊</div><div><div class="stat-pill-val">CRM</div><div class="stat-pill-lbl">客户管理</div></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">快捷入口</div>', unsafe_allow_html=True)
    st.markdown('<div class="qa-section">', unsafe_allow_html=True)
    for row_start in range(0, len(QUICK_ACCESS), 5):
        row_items = QUICK_ACCESS[row_start:row_start + 5]
        cols = st.columns(len(row_items))
        for col, (icon, title, desc, page) in zip(cols, row_items):
            with col:
                if st.button(f"{icon}\n{title}\n{desc}", key=f"qa_{row_start}_{title}", use_container_width=True):
                    st.switch_page(page)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">全功能导航</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-section">', unsafe_allow_html=True)
    tabs = st.tabs(list(NAV_SECTIONS.keys()))
    for tab, items in zip(tabs, NAV_SECTIONS.values()):
        with tab:
            for icon, title, desc, page in items:
                if st.button(f"{icon}  {title}  —  {desc}", key=f"nav_{icon}_{title}", use_container_width=True):
                    st.switch_page(page)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-label">使用技巧</div>
        <div class="tips-grid">
          <div class="tip-pill"><strong>⚡ 流式实时输出</strong>所有 AI 功能逐字流式显示，无需等待即可预览。</div>
          <div class="tip-pill"><strong>⚙️ 一次设置全用</strong>「AI 偏好」页设置公司信息，全站自动预填。</div>
          <div class="tip-pill"><strong>🔑 接入任意模型</strong>SiliconFlow / Moonshot / Groq / Ollama 等。</div>
          <div class="tip-pill"><strong>📅 跟进不漏单</strong>自动提醒 3天/1周/2周/1月 + 邮件推送。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        '<div class="footer">'
        '💼 <strong>AI-Trade Pro</strong> &nbsp;·&nbsp; '
        '外贸全流程 AI 助手 &nbsp;·&nbsp; '
        'Powered by NVIDIA NIM · OpenAI · DeepSeek'
        '</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    """Render the Streamlit application when launched by Streamlit."""
    import streamlit as st

    from utils.logger import configure_logging
    from utils.ui_helpers import check_auth, inject_css

    configure_logging()
    st.set_page_config(
        page_title="外贸AI助手 | AI-Trade Pro",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    check_auth()
    _render_home(st)


if __name__ == "__main__":
    main()
