"""
pages/17_💰_智能报价.py
AI 智能定价建议：基于产品、市场、数量、成本等因素给出报价策略。
"""
from __future__ import annotations

import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result, get_user_id

st.set_page_config(page_title="智能报价 | 外贸AI助手", page_icon="💰", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">💰 智能报价</h1>
    <p class="hero-subtitle">AI 分析市场、成本与竞争，给出科学定价策略与阶梯报价建议</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="form-title">📝 填写产品与市场信息</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    product = st.text_input("产品名称 *", placeholder="e.g. Stainless Steel Water Bottle 500ml")
    target_market = st.text_input("目标市场 *", placeholder="e.g. North America, Europe, Southeast Asia")
    order_quantity = st.number_input("预估订单数量", min_value=1, value=1000, step=100)
with col2:
    trade_term = st.selectbox("贸易术语", ["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"])
    production_cost = st.text_input("生产/采购成本（可选）", placeholder="e.g. $3.50/pc including packaging")
    competitor_info = st.text_input("竞争对手参考（可选）", placeholder="e.g. Competitor A sells at $6.99 on Amazon")

st.markdown('<div class="tip-card">💡 提供越详细的信息（成本、竞品价格），AI 的报价建议越精准。</div>', unsafe_allow_html=True)

generate_clicked = st.button("🚀 生成智能报价建议", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product.strip():
        st.warning("⚠️ 请填写产品名称")
    elif not target_market.strip():
        st.warning("⚠️ 请填写目标市场")
    else:
        from utils.ai_client import generate_smart_quote
        uid = get_user_id()
        result = generate_smart_quote(
            product=product,
            target_market=target_market,
            order_quantity=order_quantity,
            production_cost=production_cost,
            competitor_info=competitor_info,
            trade_term=trade_term,
            stream=True,
            user_id=uid,
        )
        show_result(
            result,
            result_key="smart_quote",
            label="💰 智能报价建议",
            file_name=f"smart_quote_{product[:20]}.txt",
            height=350,
            show_subject_line=False,
            history_feature="智能报价",
            history_title=f"{product} → {target_market}",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 智能报价</div>', unsafe_allow_html=True)
