"""
pages/29_📝_合同模板.py
外贸合同模板生成 — AI 生成销售合同/代理协议/NDA 等专业英文合同。
"""
from __future__ import annotations

import streamlit as st

from config.prompts import CONTRACT_TYPES
from utils.ai_client import generate_contract_template
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result
from utils.user_prefs import get_pref

st.set_page_config(page_title="合同模板 | 外贸AI助手", page_icon="📝", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📝 外贸合同模板</h1>
    <p class="hero-subtitle">AI 生成专业英文合同模板 · 销售合同 · 代理协议 · NDA · 独家经销</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 生成的合同为模板参考，正式签署前请咨询法律顾问。支持 INCOTERMS 2020 和 CISG。</div>',
    unsafe_allow_html=True,
)

contract_type = st.selectbox("合同类型 *", CONTRACT_TYPES)

col1, col2 = st.columns(2)
with col1:
    seller_info = st.text_input(
        "卖方信息",
        value=get_pref("company_name") or "",
        placeholder="Your Company Ltd., Shanghai, China",
    )
    product = st.text_input("产品/服务", value=get_pref("default_product"), placeholder="LED Street Light 100W")
with col2:
    buyer_info = st.text_input("买方信息", placeholder="ABC Trading Inc., New York, USA")
    terms = st.text_area(
        "特殊条款（可选）",
        height=80,
        placeholder="e.g. MOQ 500pcs, T/T 30% deposit, delivery 30 days",
    )

generate_clicked = st.button("📝 生成合同模板", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if generate_clicked:
    if not seller_info.strip() or not buyer_info.strip():
        st.warning("⚠️ 请填写买卖双方信息")
    elif not product.strip():
        st.warning("⚠️ 请填写产品/服务名称")
    else:
        result = generate_contract_template(
            contract_type=contract_type,
            seller_info=seller_info,
            buyer_info=buyer_info,
            product=product,
            terms=terms,
            stream=True,
            user_id=get_user_id(),
        )
        show_result(
            result,
            result_key="contract_template",
            label="📝 合同模板",
            file_name=f"contract_{contract_type[:10]}.txt",
            height=450,
            history_feature="合同模板",
            history_title=f"{contract_type[:15]}",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 合同模板生成</div>', unsafe_allow_html=True)
