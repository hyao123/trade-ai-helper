"""
pages/25_📜_形式发票.py
形式发票 (Proforma Invoice) PDF 生成 — 用于价格确认、L/C 申请、海关预清关。
"""
from __future__ import annotations

import uuid

import streamlit as st

from utils.packing_invoice_pdf import generate_proforma_invoice_pdf
from utils.ui_helpers import check_auth, inject_css
from utils.user_prefs import get_pref, save_seller_identity

st.set_page_config(page_title="形式发票 | 外贸AI助手", page_icon="📜", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📜 形式发票生成</h1>
    <p class="hero-subtitle">Proforma Invoice — 价格确认 · L/C 申请 · 海关预清关 · 一键 PDF</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="tip-card">
💡 <b>形式发票</b>是正式商业发票之前的价格确认文件，常用于：申请信用证(L/C)、进口商预清关报价、
客户内部采购审批。填写信息比商业发票更简单，不含 HS 编码。
</div>
""", unsafe_allow_html=True)

# ── 产品明细 ──────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)

if "pi_items" not in st.session_state:
    st.session_state.pi_items = [{"id": str(uuid.uuid4())[:6]}]


def _add_pi_item():
    st.session_state.pi_items.append({"id": str(uuid.uuid4())[:6]})


def _del_pi_item(idx: int):
    if len(st.session_state.pi_items) > 1:
        st.session_state.pi_items.pop(idx)


st.markdown("#### 🛒 产品明细")
items_data = []
currency_options = ["USD", "EUR", "GBP", "CNY", "AUD"]
currency = st.selectbox("币种", currency_options, key="pi_currency")

for i, item in enumerate(st.session_state.pi_items):
    sid = item["id"]
    cols = st.columns([3, 1.2, 1.2, 1.5, 1.8, 0.5])
    with cols[0]:
        product = st.text_input("产品名称" if i == 0 else " ", key=f"pi_prod_{sid}",
                                placeholder="e.g. LED Street Light 100W",
                                label_visibility="visible" if i == 0 else "hidden")
    with cols[1]:
        qty = st.number_input("数量" if i == 0 else " ", min_value=1, value=100,
                              key=f"pi_qty_{sid}",
                              label_visibility="visible" if i == 0 else "hidden")
    with cols[2]:
        unit = st.selectbox("单位" if i == 0 else " ",
                            ["PCS", "SETS", "KG", "MT", "CBM"],
                            key=f"pi_unit_{sid}",
                            label_visibility="visible" if i == 0 else "hidden")
    with cols[3]:
        unit_price = st.number_input("单价" if i == 0 else " ", min_value=0.0,
                                     value=10.0, step=0.1, format="%.2f",
                                     key=f"pi_price_{sid}",
                                     label_visibility="visible" if i == 0 else "hidden")
    with cols[4]:
        description = st.text_input("备注/规格" if i == 0 else " ", key=f"pi_desc_{sid}",
                                    placeholder="e.g. IP66, 4000K",
                                    label_visibility="visible" if i == 0 else "hidden")
    with cols[5]:
        if i == 0:
            st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️", key=f"pi_del_{sid}",
                     disabled=(len(st.session_state.pi_items) == 1)):
            _del_pi_item(i)
            st.rerun()

    amount = qty * unit_price
    items_data.append({
        "product": product, "quantity": qty, "unit": unit,
        "unit_price": unit_price, "amount": amount, "description": description,
    })

col_add, col_total = st.columns([2, 3])
with col_add:
    if st.button("➕ 添加产品行", use_container_width=True):
        _add_pi_item()
        st.rerun()
with col_total:
    total = sum(i["amount"] for i in items_data)
    if total > 0:
        st.metric("💰 总金额", f"{currency} {total:,.2f}")

st.markdown('<hr style="margin:1.2rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)

# ── 买卖双方信息 ──────────────────────────────────────
st.markdown("#### 👥 买卖双方信息")
col_s, col_b = st.columns(2)
with col_s:
    st.markdown("**卖方（Seller）**")
    seller_co = st.text_input("公司名称", value=get_pref("company_name") or "Your Company Ltd.", key="pi_sel_co")
    seller_addr = st.text_input("地址", value="", key="pi_sel_addr", placeholder="Shanghai, China")
    seller_phone = st.text_input("电话", value=get_pref("phone") or "", key="pi_sel_phone")
    seller_bank = st.text_area("银行信息（可选）", height=80, key="pi_sel_bank",
                               placeholder="Bank: XXX Bank\nSwift: XXXXXXXX\nAccount: XXXX")
with col_b:
    st.markdown("**买方（Buyer）**")
    buyer_co = st.text_input("公司名称", key="pi_buy_co", placeholder="ABC Trading Inc.")
    buyer_addr = st.text_input("地址", key="pi_buy_addr", placeholder="New York, USA")
    buyer_contact = st.text_input("联系人", key="pi_buy_contact", placeholder="John Smith")

st.markdown('<hr style="margin:1.2rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)

# ── 贸易条款 ──────────────────────────────────────────
st.markdown("#### 📦 贸易条款")
tc1, tc2, tc3 = st.columns(3)
with tc1:
    pi_no = st.text_input("发票编号", value="PI-2026-001", key="pi_no")
    payment_terms = st.selectbox("付款方式", ["T/T 30%", "T/T 50%", "L/C at sight",
                                              "D/P", "T/T in advance", "Western Union"])
with tc2:
    trade_term = st.selectbox("贸易术语", ["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"])
    port = st.text_input("发货港", value="Shanghai, China", key="pi_port")
with tc3:
    validity = st.text_input("报价有效期", value="30 days", key="pi_validity")
    delivery_time = st.text_input("交货期", value="15-20 days", key="pi_delivery")

generate_clicked = st.button("🚀 生成形式发票 PDF", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    valid_items = [it for it in items_data if it.get("product", "").strip()]
    if not valid_items:
        st.warning("⚠️ 请填写至少一个产品名称")
    else:
        if seller_co:
            save_seller_identity(seller_co, get_pref("contact_name"), get_pref("email"), seller_phone)

        seller = {"company": seller_co, "address": seller_addr,
                  "phone": seller_phone, "bank_info": seller_bank}
        buyer = {"company": buyer_co, "address": buyer_addr, "contact": buyer_contact}
        trade_terms_data = {
            "proforma_no": pi_no, "date": "",
            "payment_terms": payment_terms, "trade_term": trade_term,
            "currency": currency, "port": port,
            "validity": validity, "delivery_time": delivery_time,
        }

        with st.spinner("📄 正在生成形式发票 PDF..."):
            pdf_bytes = generate_proforma_invoice_pdf(
                items=valid_items, seller=seller,
                buyer=buyer, trade_terms=trade_terms_data,
            )
        st.session_state.results["pi_pdf"] = pdf_bytes
        st.session_state.results["pi_just_gen"] = True
        st.balloons()

if st.session_state.results.get("pi_pdf"):
    if st.session_state.results.pop("pi_just_gen", False):
        pass  # balloons already triggered
    st.markdown(
        '<div class="success-box"><div style="font-size:1.5rem;">✅</div>'
        '<div class="success-title">形式发票生成完成！</div></div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        "📥 下载形式发票 PDF",
        st.session_state.results["pi_pdf"],
        file_name=f"Proforma_Invoice_{pi_no}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 形式发票</div>', unsafe_allow_html=True)
