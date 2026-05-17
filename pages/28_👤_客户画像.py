"""
pages/28_👤_客户画像.py
客户画像分析 — 输入公司名/网址，AI 分析背景、需求、决策者和沟通策略。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_client import analyze_customer_profile
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result

st.set_page_config(page_title="客户画像 | 外贸AI助手", page_icon="👤", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">👤 客户画像分析</h1>
    <p class="hero-subtitle">输入公司名称或网址，AI 深度分析客户背景、需求、决策链和最佳沟通策略</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 信息越详细，分析越精准。即使只有公司名也能获得有价值的行业洞察。</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("公司名称 *", placeholder="e.g. ABC Trading Inc.")
    website = st.text_input("公司网址（可选）", placeholder="e.g. www.abctrading.com")
with col2:
    industry = st.text_input("所属行业（可选）", placeholder="e.g. Home Appliances, LED Lighting")
    additional = st.text_area(
        "补充信息（可选）",
        height=80,
        placeholder="e.g. 从LinkedIn找到 / 展会名片 / 年采购额约$500K",
    )

analyze_clicked = st.button("🔍 生成客户画像", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if analyze_clicked:
    if not company_name.strip():
        st.warning("⚠️ 请填写公司名称")
    else:
        result = analyze_customer_profile(
            company_name=company_name,
            website=website,
            industry=industry,
            additional_info=additional,
            stream=True,
            user_id=get_user_id(),
        )
        show_result(
            result,
            result_key="customer_profile",
            label="👤 客户画像报告",
            file_name=f"customer_profile_{company_name[:20]}.txt",
            height=380,
            history_feature="客户画像",
            history_title=f"画像: {company_name[:25]}",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 客户画像分析</div>', unsafe_allow_html=True)
