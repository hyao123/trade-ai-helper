"""
pages/17_💰_智能报价.py
AI 智能定价建议：基于产品、市场、数量、成本等因素给出报价策略。
"""
from __future__ import annotations

import streamlit as st

from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result

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

# ── 成本计算 ──────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="form-title">🧮 成本计算</div>', unsafe_allow_html=True)

cc1, cc2, cc3 = st.columns(3)
with cc1:
    unit_production_cost = st.number_input("单位生产成本 (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    packaging_cost = st.number_input("包装成本/件 (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
with cc2:
    logistics_cost = st.number_input("物流运费/件 (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    inspection_cost = st.number_input("检验/质检费用/件 (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
with cc3:
    other_cost = st.number_input("其他费用/件 (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    profit_margin = st.number_input("目标利润率 %", min_value=0.0, max_value=99.9, value=20.0, step=1.0, format="%.1f")

total_cost = unit_production_cost + packaging_cost + logistics_cost + inspection_cost + other_cost
suggested_price = total_cost / (1 - profit_margin / 100) if profit_margin < 100 else 0.0
profit_per_unit = suggested_price - total_cost

mc1, mc2, mc3 = st.columns(3)
mc1.metric("总成本/件", f"${total_cost:.2f}")
mc2.metric("建议售价", f"${suggested_price:.2f}")
mc3.metric("利润/件", f"${profit_per_unit:.2f}")

st.markdown("</div>", unsafe_allow_html=True)

# ── AI 报价表单 ──────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="form-title">📝 填写产品与市场信息</div>', unsafe_allow_html=True)

cost_str = f"${total_cost:.2f}/pc" if total_cost > 0 else ""

col1, col2 = st.columns(2)
with col1:
    product = st.text_input("产品名称 *", placeholder="e.g. Stainless Steel Water Bottle 500ml")
    target_market = st.text_input("目标市场 *", placeholder="e.g. North America, Europe, Southeast Asia")
    order_quantity = st.number_input("预估订单数量", min_value=1, value=1000, step=100)
with col2:
    trade_term = st.selectbox("贸易术语", ["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"])
    production_cost = st.text_input("生产/采购成本（可选）", value=cost_str, placeholder="e.g. $3.50/pc including packaging")
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
