"""
pages/31_💱_汇率计算.py
汇率计算器 — 多币种换算 + 报价金额批量转换。
"""
from __future__ import annotations

import streamlit as st

from utils.ui_helpers import check_auth, inject_css, page_setup

page_setup("汇率计算", "💱", "💱 汇率计算器", "多币种快速换算 · 报价金额批量转换 · 支持自定义汇率")

# 参考汇率（1 USD = X）
RATES: dict[str, float] = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "CNY": 7.24,
    "JPY": 156.5, "AUD": 1.53, "CAD": 1.37, "AED": 3.67,
    "INR": 83.5, "BRL": 5.05, "MXN": 17.1, "SAR": 3.75,
    "KRW": 1340.0, "RUB": 89.5, "ZAR": 18.8,
}
NAMES = {
    "USD": "美元", "EUR": "欧元", "GBP": "英镑", "CNY": "人民币",
    "JPY": "日元", "AUD": "澳元", "CAD": "加元", "AED": "迪拉姆",
    "INR": "卢比", "BRL": "雷亚尔", "MXN": "比索", "SAR": "里亚尔",
    "KRW": "韩元", "RUB": "卢布", "ZAR": "兰特",
}

st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown("### 🔄 快速换算")

col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    from_cur = st.selectbox("从", list(RATES.keys()), format_func=lambda x: f"{NAMES[x]} ({x})")
    amount = st.number_input("金额", min_value=0.0, value=1000.0, step=100.0, format="%.2f")
with col2:
    st.markdown("<br><br><div style='text-align:center;font-size:2rem;'>→</div>", unsafe_allow_html=True)
with col3:
    to_cur = st.selectbox("到", list(RATES.keys()), format_func=lambda x: f"{NAMES[x]} ({x})", index=3)
    converted = amount / RATES[from_cur] * RATES[to_cur]
    rate = RATES[to_cur] / RATES[from_cur]
    st.metric(f"= {NAMES[to_cur]} ({to_cur})", f"{converted:,.2f}", delta=f"1 {from_cur} = {rate:.4f} {to_cur}")

st.markdown('<hr style="margin:1.5rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)
st.markdown("### 📊 批量报价转换（USD → 各币种）")

batch = st.number_input("报价金额 (USD)", min_value=0.0, value=5000.0, step=100.0, key="batch")
if batch > 0:
    targets = ["EUR", "GBP", "CNY", "JPY", "AUD", "AED", "INR", "BRL", "SAR"]
    cols = st.columns(3)
    for i, c in enumerate(targets):
        with cols[i % 3]:
            st.metric(f"{NAMES[c]} ({c})", f"{batch * RATES[c]:,.2f}")

st.markdown("</div>", unsafe_allow_html=True)
st.caption("⚠️ 汇率为参考值，实际结汇请以银行牌价为准。建议报价时预留 2-3% 汇率波动空间。")
st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 汇率计算器</div>', unsafe_allow_html=True)
