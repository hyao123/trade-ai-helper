"""
pages/34_🚀_快速设置.py
----------------------
新用户快速设置向导：2 分钟完成公司资料、主营产品、目标市场和 AI 风格偏好。
保存到现有 user_prefs，供全站表单预填和 Prompt 风格复用。
"""
from __future__ import annotations

import streamlit as st

from utils.ui_helpers import check_auth, inject_css
from utils.user_auth import get_current_user
from utils.user_prefs import get_prefs, update_prefs

st.set_page_config(page_title="快速设置 | 外贸AI助手", page_icon="🚀", layout="wide")
inject_css()
check_auth()

current_user = get_current_user()
if not current_user:
    st.warning("请先登录")
    st.stop()

prefs = get_prefs()

st.markdown(
    """
    <div class="hero-section">
        <h1 class="hero-title">🚀 快速设置</h1>
        <p class="hero-subtitle">2 分钟完成公司资料初始化，让开发信、询盘回复、报价和客户跟进自动带入你的业务背景。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

required_keys = ["company_name", "contact_name", "default_product", "main_products", "company_description"]
completed = sum(1 for key in required_keys if prefs.get(key, "").strip())
progress = completed / len(required_keys)

st.markdown("### 设置进度")
st.progress(progress)
st.caption(f"已完成 {completed}/{len(required_keys)} 项。资料越完整，AI 输出越贴近你的真实业务。")

st.markdown("---")

with st.form("onboarding_quick_setup"):
    st.markdown("### 1. 基础身份")
    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input(
            "公司名称 *",
            value=prefs.get("company_name", ""),
            placeholder="例如：Shenzhen LED Technology Co., Ltd.",
        )
        contact_name = st.text_input(
            "联系人 / 签名姓名 *",
            value=prefs.get("contact_name", "") or prefs.get("signature_name", ""),
            placeholder="例如：Tom Chen",
        )
    with col2:
        email_addr = st.text_input(
            "业务联系邮箱",
            value=prefs.get("email", "") or current_user.get("email", ""),
            placeholder="sales@yourcompany.com",
        )
        phone = st.text_input(
            "联系电话",
            value=prefs.get("phone", ""),
            placeholder="+86-755-XXXXXXXX",
        )

    st.markdown("### 2. 产品与市场")
    col3, col4 = st.columns(2)
    with col3:
        default_product = st.text_input(
            "默认产品 *",
            value=prefs.get("default_product", ""),
            placeholder="例如：LED Street Light",
            help="常用产品会自动预填到开发信、产品文案和报价类页面。",
        )
        target_markets = st.text_input(
            "主要目标市场",
            value=prefs.get("target_markets", ""),
            placeholder="例如：Europe, Middle East, Southeast Asia",
        )
    with col4:
        default_trade_term = st.selectbox(
            "默认贸易术语",
            ["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"],
            index=["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"].index(prefs.get("default_trade_term", "FOB"))
            if prefs.get("default_trade_term", "FOB") in ["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"] else 0,
        )
        default_language = st.selectbox(
            "默认输出语言",
            ["英语", "西班牙语", "法语", "德语", "葡萄牙语", "阿拉伯语", "俄语"],
            index=["英语", "西班牙语", "法语", "德语", "葡萄牙语", "阿拉伯语", "俄语"].index(prefs.get("default_language", "英语"))
            if prefs.get("default_language", "英语") in ["英语", "西班牙语", "法语", "德语", "葡萄牙语", "阿拉伯语", "俄语"] else 0,
        )

    main_products = st.text_area(
        "主营产品线 *",
        value=prefs.get("main_products", ""),
        placeholder="例如：LED路灯、工矿灯、泛光灯、太阳能路灯；功率范围30W-500W；支持OEM/ODM。",
        height=90,
    )
    company_description = st.text_area(
        "公司简介 / 核心优势 *",
        value=prefs.get("company_description", ""),
        placeholder="例如：成立于2010年，专注LED照明研发与出口，服务全球80+国家，拥有ISO认证和12条生产线。",
        height=110,
    )

    st.markdown("### 3. AI 写作风格")
    col5, col6 = st.columns(2)
    with col5:
        default_tone = st.selectbox(
            "默认邮件风格",
            ["简洁专业", "正式商务", "亲切友好"],
            index=["简洁专业", "正式商务", "亲切友好"].index(prefs.get("default_tone", "简洁专业"))
            if prefs.get("default_tone", "简洁专业") in ["简洁专业", "正式商务", "亲切友好"] else 0,
        )
        ai_style_tone = st.radio(
            "AI 语气",
            ["专业", "友好", "正式", "简洁"],
            index=["专业", "友好", "正式", "简洁"].index(prefs.get("ai_style_tone", "专业"))
            if prefs.get("ai_style_tone", "专业") in ["专业", "友好", "正式", "简洁"] else 0,
            horizontal=True,
        )
    with col6:
        ai_response_length = st.radio(
            "默认回复长度",
            ["简短", "中等", "详细"],
            index=["简短", "中等", "详细"].index(prefs.get("ai_response_length", "中等"))
            if prefs.get("ai_response_length", "中等") in ["简短", "中等", "详细"] else 1,
            horizontal=True,
        )
        st.info("资料保存成功后会自动标记快速设置完成，首页将继续推荐开发信、客户建档和跟进节奏。")

    submitted = st.form_submit_button("保存并完成快速设置", type="primary", use_container_width=True)

if submitted:
    missing = []
    if not company_name.strip():
        missing.append("公司名称")
    if not contact_name.strip():
        missing.append("联系人 / 签名姓名")
    if not default_product.strip():
        missing.append("默认产品")
    if not main_products.strip():
        missing.append("主营产品线")
    if not company_description.strip():
        missing.append("公司简介 / 核心优势")

    if missing:
        st.error("请先补充必填项：" + "、".join(missing))
    else:
        update_prefs({
            "company_name": company_name.strip(),
            "contact_name": contact_name.strip(),
            "signature_name": contact_name.strip(),
            "email": email_addr.strip(),
            "phone": phone.strip(),
            "default_product": default_product.strip(),
            "main_products": main_products.strip(),
            "target_markets": target_markets.strip(),
            "company_description": company_description.strip(),
            "default_trade_term": default_trade_term,
            "default_language": default_language,
            "default_tone": default_tone,
            "ai_style_tone": ai_style_tone,
            "ai_response_length": ai_response_length,
            "onboarding_completed": "true",
        })
        st.success("✅ 快速设置已保存！后续开发信、询盘回复、报价和客户跟进会自动复用这些资料。")
        st.balloons()

        col_next1, col_next2 = st.columns(2)
        with col_next1:
            if st.button("去生成第一封开发信", use_container_width=True, type="primary"):
                st.switch_page("pages/1_📧_开发信.py")
        with col_next2:
            if st.button("继续完善 AI 偏好", use_container_width=True):
                st.switch_page("pages/0_⚙️_AI偏好.py")

st.markdown("---")
st.markdown(
    """
    <div class="tip-card">
    💡 这些信息会保存到你的个人偏好中。你可以随时到「AI偏好」页面继续修改公司资料、AI 风格、自定义模型和高级 Prompt 指令。
    </div>
    """,
    unsafe_allow_html=True,
)
