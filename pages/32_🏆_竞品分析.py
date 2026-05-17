"""
pages/32_🏆_竞品分析.py
竞品分析 — 输入竞品信息，AI 生成差异化卖点和销售话术。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_client import analyze_competitor
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result
from utils.user_prefs import get_pref

st.set_page_config(page_title="竞品分析 | 外贸AI助手", page_icon="🏆", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🏆 竞品分析</h1>
    <p class="hero-subtitle">输入竞品信息，AI 生成差异化策略 · Battle Card · 销售话术 · 异议处理</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 提供越多竞品信息（价格、产品链接、客户反馈），分析越精准。</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    your_product = st.text_input("你的产品 *", value=get_pref("default_product"), placeholder="e.g. LED Street Light 100W")
    your_advantages = st.text_area("你的已知优势（可选）", height=80, placeholder="e.g. 5年保修 / 自有工厂 / CE+UL")
with col2:
    competitor_info = st.text_area(
        "竞品信息 *", height=120,
        placeholder="公司名/价格/链接/客户评价等任何信息",
    )
    target_market = st.text_input("目标市场（可选）", placeholder="e.g. Middle East")

analyze_clicked = st.button("🏆 生成竞品分析", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if analyze_clicked:
    if not your_product.strip():
        st.warning("⚠️ 请填写你的产品名称")
    elif not competitor_info.strip():
        st.warning("⚠️ 请填写竞品信息")
    else:
        result = analyze_competitor(
            your_product=your_product,
            competitor_info=competitor_info,
            your_advantages=your_advantages,
            target_market=target_market,
            stream=True,
            user_id=get_user_id(),
        )
        show_result(
            result,
            result_key="competitor_analysis",
            label="🏆 竞品分析报告",
            file_name=f"competitor_{your_product[:15]}.txt",
            height=400,
            history_feature="竞品分析",
            history_title=f"竞品: {your_product[:20]}",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 竞品分析</div>', unsafe_allow_html=True)
