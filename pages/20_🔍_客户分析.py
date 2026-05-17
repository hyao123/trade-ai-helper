"""
pages/20_🔍_客户分析.py
AI 智能客户画像分析：深度洞察客户需求与合作潜力。
"""
from __future__ import annotations

import streamlit as st

from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result

st.set_page_config(page_title="客户分析 | 外贸AI助手", page_icon="🔍", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🔍 客户分析</h1>
    <p class="hero-subtitle">AI 智能客户画像分析，深度洞察客户需求与合作潜力</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="form-title">📝 输入客户信息</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("公司名称 *", placeholder="e.g. ABC Trading Inc.")
    website = st.text_input("公司网站（可选）", placeholder="e.g. https://www.example.com")
with col2:
    industry = st.text_input("所属行业（可选）", placeholder="e.g. Electronics, Home & Garden")

additional_info = st.text_area(
    "补充信息（已知的公司背景、采购历史等）",
    placeholder="e.g. Annual purchase volume around $500K, previously sourced from Vietnam...",
    height=120,
)

st.markdown('<div class="tip-card">💡 提供越详细的公司信息（网站、行业、采购历史），AI 画像分析越精准。</div>', unsafe_allow_html=True)

generate_clicked = st.button("🚀 生成客户画像分析", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not company_name.strip():
        st.warning("⚠️ 请填写公司名称")
    else:
        from utils.ai_client import analyze_customer_profile
        uid = get_user_id()
        result = analyze_customer_profile(
            company_name=company_name,
            website=website,
            industry=industry,
            additional_info=additional_info,
            stream=True,
            user_id=uid,
        )
        show_result(
            result,
            result_key="customer_analysis_20",
            label="🔍 客户画像分析",
            file_name=f"customer_analysis_{company_name[:20]}.txt",
            height=350,
            show_subject_line=False,
            history_feature="客户分析",
            history_title=f"{company_name}",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 客户分析</div>', unsafe_allow_html=True)
