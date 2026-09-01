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
.payment-return-banner { background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%); border: 1px solid #bbf7d0; border-left: 5px solid #22c55e; border-radius: 16px; padding: 1rem 1.1rem; margin: 0.2rem 0 1.2rem; color: #14532d; box-shadow: 0 8px 24px rgba(34,197,94,0.10); }
.payment-return-title { font-weight: 850; font-size: 1rem; color: #166534; margin-bottom: 0.25rem; }
.payment-return-copy { font-size: 0.88rem; line-height: 1.65; color: #14532d; }
.payment-return-error { background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%); border-color: #fed7aa; border-left-color: #f97316; color: #7c2d12; }
.payment-return-error .payment-return-title { color: #9a3412; }
.payment-return-error .payment-return-copy { color: #7c2d12; }
.onboarding-banner { background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%); border: 1px solid #c7d2fe; border-left: 5px solid #6366f1; border-radius: 16px; padding: 1rem 1.1rem; margin: 0.2rem 0 1.2rem; color: #312e81; box-shadow: 0 8px 24px rgba(99,102,241,0.10); }
.onboarding-title { font-weight: 850; font-size: 1rem; color: #312e81; margin-bottom: 0.25rem; }
.onboarding-copy { font-size: 0.88rem; line-height: 1.65; color: #4338ca; }
.onboarding-progress { margin-top: 0.6rem; font-size: 0.78rem; color: #4f46e5; font-weight: 700; }
</style>
"""


QUICK_ACCESS = [
    ("🚀", "快速设置", "2分钟初始化资料", "pages/34_🚀_快速设置.py"),
    ("🏭", "智能寻源", "货源匹配+化工定制", "pages/38_🏭_智能寻源.py"),
    ("📧", "开发信", "AI 高转化冷邮件", "pages/1_📧_开发信.py"),
    ("📩", "询盘回复", "逐条回答+报价", "pages/2_📩_询盘回复.py"),
    ("📥", "AI收件箱", "智能邮件分类回复", "pages/35_📥_AI收件箱.py"),
    ("🚀", "自动推送", "批量营销+自动跟进", "pages/36_🚀_自动推送.py"),
    ("📄", "报价单", "多SKU专业PDF", "pages/3_📄_报价单.py"),
    ("📬", "跟进邮件", "5阶段智能跟进", "pages/5_📬_跟进邮件.py"),
    ("💰", "智能报价", "AI定价策略", "pages/17_💰_智能报价.py"),
    ("🗣️", "谈判话术", "6场景应对脚本", "pages/13_🗣️_谈判话术.py"),
    ("🔍", "意图识别", "分析回复意图", "pages/26_🔍_意图识别.py"),
    ("🏷️", "HS编码", "AI建议+关税", "pages/27_🏷️_HS编码.py"),
]


NAV_SECTIONS = {
    "🔍 1. 获客拓客与寻源": [
        ("🏭", "智能寻源", "产业带匹配+化工CAS+退税", "pages/38_🏭_智能寻源.py"),
        ("📧", "开发信", "AI 高转化冷邮件 + Subject", "pages/1_📧_开发信.py"),
        ("📨", "批量开发信", "CSV批量个性化发送", "pages/12_📨_批量开发信.py"),
        ("🚀", "自动推送", "自动化营销与行业拓客", "pages/36_🚀_自动推送.py"),
        ("🛒", "产品上架", "Amazon/Shopify Listing", "pages/6_🛒_产品上架.py"),
        ("💬", "社媒文案", "LinkedIn/IG/FB 营销", "pages/8_💬_社媒文案.py"),
        ("🔁", "批量生成", "多策略变体批量对比", "pages/24_🔁_批量生成.py"),
    ],
    "💰 2. 商机转化与谈判": [
        ("📩", "询盘回复", "逐条回答 + 报价区间", "pages/2_📩_询盘回复.py"),
        ("💰", "智能报价", "AI 定价策略与溢价分析", "pages/17_💰_智能报价.py"),
        ("🗣️", "谈判话术", "6 大实战谈判应对脚本", "pages/13_🗣️_谈判话术.py"),
        ("🔍", "意图识别", "分析买家邮件真实意图", "pages/26_🔍_意图识别.py"),
        ("🌐", "邮件润色", "专业翻译+本土化润色", "pages/15_🌐_邮件润色.py"),
        ("🏆", "竞品分析", "Battle Card 对抗话术", "pages/32_🏆_竞品分析.py"),
        ("🧪", "AB测试", "邮件转化变体对比", "pages/21_▪_AB测试.py"),
    ],
    "📦 3. 履约出货与单证": [
        ("📄", "报价单PDF", "多SKU专业外贸PDF", "pages/3_📄_报价单.py"),
        ("📜", "形式发票", "Proforma Invoice (PI)", "pages/25_📜_形式发票.py"),
        ("▪", "装箱发票", "Packing List + 商业发票", "pages/19_▪_装箱发票.py"),
        ("📦", "装箱计算", "20/40GP 集装箱装载优化", "pages/18_📦_装箱计算.py"),
        ("🏷️", "HS编码", "AI 建议 + 关税税率", "pages/27_🏷️_HS编码.py"),
        ("🚢", "提单解读", "B/L 提单字段+风险提示", "pages/30_🚢_提单解读.py"),
        ("📝", "合同模板", "6 类国际贸易合同框架", "pages/29_📝_合同模板.py"),
        ("💱", "汇率计算", "实时多币种精准折算", "pages/31_💱_汇率计算.py"),
    ],
    "🔄 4. 客户沉淀与复购": [
        ("📇", "客户管理", "CRM + 评分 + 标签体系", "pages/7_📇_客户管理.py"),
        ("📅", "跟进日历", "自动提醒 + 邮件推送", "pages/10_📅_跟进日历.py"),
        ("📥", "AI收件箱", "Gmail/Outlook 智能分类直回", "pages/35_📥_AI收件箱.py"),
        ("📥", "入站邮件", "导入客户邮件生成草稿", "pages/37_📥_入站邮件.py"),
        ("📬", "跟进邮件", "5 阶段智能催单跟进", "pages/5_📬_跟进邮件.py"),
        ("😟", "投诉处理", "客诉危机化解与方案", "pages/16_😟_投诉处理.py"),
        ("🎄", "节日问候", "全球文化适配祝福", "pages/14_🎄_节日问候.py"),
        ("📊", "客户分析", "转化漏斗 + 地区分布", "pages/20_🔍_客户分析.py"),
        ("👤", "客户画像", "B2B 买家企业深度分析", "pages/28_👤_客户画像.py"),
        ("📈", "仪表盘", "核心业务指标可视化", "pages/33_📊_仪表盘.py"),
    ],
    "⚙️ 系统与设置": [
        ("🚀", "快速设置", "2 分钟初始化公司资料", "pages/34_🚀_快速设置.py"),
        ("⚙️", "AI偏好", "预填 + 风格 + 自定义模型", "pages/0_⚙️_AI偏好.py"),
        ("📋", "历史记录", "生成结果归档与复用", "pages/9_📋_历史记录.py"),
        ("📈", "数据导出", "JSON / CSV 安全备份", "pages/22_📈_数据导出.py"),
        ("💳", "套餐升级", "Free / Pro / Enterprise", "pages/23_💳_套餐升级.py"),
        ("👤", "账户管理", "资料 + 密码 + 套餐", "pages/11_👤_账户管理.py"),
    ],
}


def _render_email_verification_banner(st) -> None:
    """Show a clear home-page reminder when the current user's email is unverified."""
    import html
    
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

    # No mail provider configured means verification emails cannot be delivered.
    # The feature gate is relaxed in that case (see utils.email_gate), so the
    # home banner must not nag users about a verification they cannot complete.
    from utils.email_service import has_email_provider_configured
    if not has_email_provider_configured():
        return

    email = latest_user.get("email") or current_user.get("email") or "你的邮箱"
    safe_username = html.escape(username)
    safe_email = html.escape(email)
    st.markdown(
        f"""
        <div class="email-verify-banner">
          <div class="email-verify-title">📮 请先验证邮箱，解锁 AI 生成与套餐升级</div>
          <div class="email-verify-copy">
            我们已为账号 <strong>{safe_username}</strong> 绑定邮箱 <strong>{safe_email}</strong>。
            为确保密码找回和账户通知可用，AI 生成、付费升级和高级功能需要先完成邮箱验证。
            请进入「账户管理」输入验证码，或重新发送验证邮件。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("去账户管理验证邮箱", key="home_verify_email_btn", type="primary"):
        st.switch_page("pages/11_👤_账户管理.py")


def _render_payment_return_banner(st) -> None:
    """Complete Stripe upgrades when Checkout redirects back to the home page."""
    from utils.payment import complete_upgrade_from_query
    from utils.repositories import load_user
    from utils.user_auth import get_current_user

    current_user = get_current_user()
    if not current_user or current_user.get("username") in (None, "admin"):
        return

    handled, success, message = complete_upgrade_from_query(current_user["username"], st.query_params)
    if not handled:
        return

    st.query_params.clear()
    if success:
        latest_user = load_user(current_user["username"]) or current_user
        st.session_state["current_user"].update(
            {
                "tier": latest_user.get("tier", current_user.get("tier", "free")),
                "email_verified": latest_user.get("email_verified", current_user.get("email_verified", False)),
            }
        )
        st.markdown(
            f"""
            <div class="payment-return-banner">
              <div class="payment-return-title">💳 套餐升级已生效</div>
              <div class="payment-return-copy">{message}。你现在可以继续使用对应套餐额度和高级功能。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="payment-return-banner payment-return-error">
          <div class="payment-return-title">💳 支付返回已收到，但套餐未自动激活</div>
          <div class="payment-return-copy">原因：{message}。请进入「套餐升级」页面重试验证，或联系管理员处理。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_onboarding_banner(st) -> None:
    """Guide new users to complete quick setup when business context is missing."""
    from utils.user_auth import get_current_user
    from utils.user_prefs import (
        get_prefs,
        is_onboarding_complete,
        onboarding_completion_counts,
    )

    current_user = get_current_user()
    if not current_user or current_user.get("username") in (None, "admin"):
        return

    prefs = get_prefs()
    completed, total = onboarding_completion_counts(prefs)
    if is_onboarding_complete(prefs):
        return

    st.markdown(
        f"""
        <div class="onboarding-banner">
          <div class="onboarding-title">🚀 完成快速设置，让 AI 更懂你的业务</div>
          <div class="onboarding-copy">
            先填写公司名称、主营产品、目标市场和写作风格，后续开发信、询盘回复、报价和客户跟进会自动带入这些信息，减少重复输入。
          </div>
          <div class="onboarding-progress">当前资料完成度：{completed}/{total}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("开始 2 分钟快速设置", key="home_onboarding_btn", type="primary"):
        st.switch_page("pages/34_🚀_快速设置.py")


def _render_home(st) -> None:
    """Render the home page. ``st`` is injected to keep imports out of module scope."""
    st.markdown(HOME_CSS, unsafe_allow_html=True)
    _render_payment_return_banner(st)
    _render_email_verification_banner(st)
    _render_onboarding_banner(st)

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

    # ── 零基础新手 3 步开单向导 ──
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 1.5px solid #cbd5e1; border-radius: 16px; padding: 1.2rem 1.4rem; margin-bottom: 1.5rem;">
            <div style="font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-bottom: 0.4rem;">
                🌟 零基础外贸人 · 3 步开单极速指引
            </div>
            <div style="font-size: 0.85rem; color: #475569; margin-bottom: 0.8rem;">
                无需任何电脑复杂设置，跟着以下 3 步，3 分钟即可完成全套外贸展业闭环：
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px;">
                    <div style="font-weight: 700; color: #4f46e5; font-size: 0.88rem; margin-bottom: 4px;">① 预填公司资料</div>
                    <div style="font-size: 0.78rem; color: #64748b; line-height: 1.4;">设置一次公司名和主营产品，全站所有页面自动带入签名。</div>
                </div>
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px;">
                    <div style="font-weight: 700; color: #0284c7; font-size: 0.88rem; margin-bottom: 4px;">② 找货源 / 拓客 / 写信</div>
                    <div style="font-size: 0.78rem; color: #64748b; line-height: 1.4;">智能匹配全国产业带与化工基地，AI 一键生成高转化开发信。</div>
                </div>
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px;">
                    <div style="font-weight: 700; color: #16a34a; font-size: 0.88rem; margin-bottom: 4px;">③ 测算退税 & 出报价单</div>
                    <div style="font-size: 0.78rem; color: #64748b; line-height: 1.4;">输入采购价秒算 13% 退税与 FOB 保本价，一键导出专业 PDF。</div>
                </div>
            </div>
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

    st.markdown('<div class="section-label">⚡ 30秒高频极速工具箱 (即时测算与速写)</div>', unsafe_allow_html=True)
    with st.container():
        col_box1, col_box2 = st.columns(2)
        with col_box1:
            st.markdown(
                """
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;">
                    <div style="font-weight: 700; color: #0f172a; margin-bottom: 8px; font-size: 0.92rem;">
                        💱 快速汇率折算 (实时参考)
                    </div>
                """,
                unsafe_allow_html=True,
            )
            q_col1, q_col2, q_col3 = st.columns(3)
            with q_col1:
                usd_input = st.number_input("金额 (USD $)", min_value=0.0, value=1000.0, step=100.0, key="home_usd_in")
            with q_col2:
                fx_input = st.number_input("汇率 (USD/CNY)", min_value=1.0, value=7.20, step=0.01, key="home_fx_in")
            with q_col3:
                cny_res = usd_input * fx_input
                st.metric("折合人民币", f"¥{cny_res:,.2f}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_box2:
            st.markdown(
                """
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;">
                    <div style="font-weight: 700; color: #0f172a; margin-bottom: 8px; font-size: 0.92rem;">
                        💰 出口退税与 FOB 保本速算
                    </div>
                """,
                unsafe_allow_html=True,
            )
            r_col1, r_col2, r_col3 = st.columns(3)
            with r_col1:
                p_cny = st.number_input("采购价 (CNY含税)", min_value=0.0, value=100.0, step=10.0, key="home_p_cny")
            with r_col2:
                r_pct = st.number_input("退税率 (%)", min_value=0.0, max_value=30.0, value=13.0, step=1.0, key="home_r_pct")
            with r_col3:
                tax_free = p_cny / (1.0 + 0.13)
                rebate_amt = tax_free * (r_pct / 100.0)
                net_cost = p_cny - rebate_amt
                breakeven_usd = net_cost / fx_input
                st.metric("FOB 保本价", f"${breakeven_usd:.2f}", delta=f"退税 +¥{rebate_amt:.2f}")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">全功能成单效益导航 (4 大业务阶段)</div>', unsafe_allow_html=True)
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
