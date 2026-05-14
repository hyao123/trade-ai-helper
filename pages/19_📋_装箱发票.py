"""
pages/19_📋_装箱发票.py
装箱单 & 商业发票 PDF 生成。
"""
from __future__ import annotations

import uuid
import streamlit as st
from utils.ui_helpers import inject_css, check_auth
from utils.packing_invoice_pdf import generate_packing_list_pdf, generate_commercial_invoice_pdf

st.set_page_config(page_title="装箱发票 | 外贸AI助手", page_icon="📋", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📋 装箱单 & 商业发票</h1>
    <p class="hero-subtitle">一键生成专业的 Packing List 和 Commercial Invoice PDF</p>
</div>
""", unsafe_allow_html=True)

# ── 文档类型选择 ──────────────────────────────────────
doc_type = st.radio(
    "选择文档类型",
    ["📦 装箱单 (Packing List)", "🧾 商业发票 (Commercial Invoice)"],
    horizontal=True,
)

# ── 通用信息 ──────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)

# 发货人/卖方信息
st.markdown("#### 🏢 发货人/卖方信息")
sc1, sc2 = st.columns(2)
with sc1:
    seller_company = st.text_input("公司名称", value="Your Company Ltd.", key="seller_co")
    seller_address = st.text_input("地址", value="Shanghai, China", key="seller_addr")
with sc2:
    seller_phone = st.text_input("电话", value="+86-XXX-XXXXXXX", key="seller_phone")
    seller_bank = st.text_input("银行信息（发票用）", placeholder="Bank Name, Account No.", key="seller_bank")

# 收货人/买方信息
st.markdown("#### 👤 收货人/买方信息")
bc1, bc2 = st.columns(2)
with bc1:
    buyer_company = st.text_input("公司名称", placeholder="ABC Trading Inc.", key="buyer_co")
    buyer_address = st.text_input("地址", placeholder="New York, USA", key="buyer_addr")
with bc2:
    buyer_contact = st.text_input("联系人", placeholder="John Smith", key="buyer_contact")

# 运输/贸易信息
st.markdown("#### 🚢 运输/贸易信息")
tc1, tc2, tc3 = st.columns(3)
with tc1:
    invoice_no = st.text_input("单据编号", value="PL-2026-001", key="inv_no")
    port_of_loading = st.text_input("装货港", value="Shanghai", key="pol")
with tc2:
    inv_date = st.text_input("日期", value="2026-05-14", key="inv_date")
    port_of_discharge = st.text_input("卸货港", placeholder="Los Angeles", key="pod")
with tc3:
    vessel = st.text_input("船名/航次", placeholder="EVER GIVEN V.025E", key="vessel")
    marks = st.text_input("唛头", value="N/M", key="marks")

if doc_type.startswith("🧾"):
    tc4, tc5 = st.columns(2)
    with tc4:
        payment_terms = st.selectbox("付款方式", ["T/T 30%", "T/T 50%", "L/C at sight", "D/P"])
        trade_term = st.selectbox("贸易术语", ["FOB", "CIF", "EXW", "DDP", "CFR"])
    with tc5:
        currency = st.selectbox("币种", ["USD", "EUR", "GBP", "CNY"])

# ── 产品明细 ──────────────────────────────────────────
st.markdown("#### 📦 产品明细")

if "packing_items" not in st.session_state:
    st.session_state.packing_items = [{"id": str(uuid.uuid4())[:6]}]


def add_packing_item():
    st.session_state.packing_items.append({"id": str(uuid.uuid4())[:6]})


def remove_packing_item(idx: int):
    if len(st.session_state.packing_items) > 1:
        st.session_state.packing_items.pop(idx)


items_data = []
for i, item in enumerate(st.session_state.packing_items):
    sid = item["id"]
    if doc_type.startswith("📦"):
        # Packing List columns
        cols = st.columns([2.5, 1.5, 1, 1, 1.2, 1.2, 1.5, 1, 0.5])
        with cols[0]:
            product = st.text_input("产品" if i == 0 else " ", key=f"pk_prod_{sid}",
                                    placeholder="Product Name",
                                    label_visibility="visible" if i == 0 else "hidden")
        with cols[1]:
            model = st.text_input("型号" if i == 0 else " ", key=f"pk_model_{sid}",
                                  placeholder="Model",
                                  label_visibility="visible" if i == 0 else "hidden")
        with cols[2]:
            quantity = st.number_input("数量" if i == 0 else " ", min_value=0, value=1000,
                                       key=f"pk_qty_{sid}",
                                       label_visibility="visible" if i == 0 else "hidden")
        with cols[3]:
            cartons = st.number_input("箱数" if i == 0 else " ", min_value=0, value=50,
                                      key=f"pk_ctns_{sid}",
                                      label_visibility="visible" if i == 0 else "hidden")
        with cols[4]:
            nw = st.number_input("净重kg" if i == 0 else " ", min_value=0.0, value=400.0,
                                 step=10.0, format="%.1f", key=f"pk_nw_{sid}",
                                 label_visibility="visible" if i == 0 else "hidden")
        with cols[5]:
            gw = st.number_input("毛重kg" if i == 0 else " ", min_value=0.0, value=450.0,
                                 step=10.0, format="%.1f", key=f"pk_gw_{sid}",
                                 label_visibility="visible" if i == 0 else "hidden")
        with cols[6]:
            dims = st.text_input("尺寸cm" if i == 0 else " ", key=f"pk_dims_{sid}",
                                 placeholder="60x40x35",
                                 label_visibility="visible" if i == 0 else "hidden")
        with cols[7]:
            cbm = st.number_input("CBM/箱" if i == 0 else " ", min_value=0.0, value=0.084,
                                  step=0.01, format="%.3f", key=f"pk_cbm_{sid}",
                                  label_visibility="visible" if i == 0 else "hidden")
        with cols[8]:
            if i == 0:
                st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"pk_del_{sid}", disabled=(len(st.session_state.packing_items) == 1)):
                remove_packing_item(i)
                st.rerun()

        items_data.append({
            "product": product, "model": model, "quantity": quantity,
            "cartons": cartons, "net_weight_kg": nw, "gross_weight_kg": gw,
            "carton_dims": dims, "cbm_per_carton": cbm,
        })
    else:
        # Commercial Invoice columns
        cols = st.columns([2.5, 1.5, 1, 1, 1.5, 1.5, 1, 0.5])
        with cols[0]:
            product = st.text_input("产品" if i == 0 else " ", key=f"ci_prod_{sid}",
                                    placeholder="Product Name",
                                    label_visibility="visible" if i == 0 else "hidden")
        with cols[1]:
            hs_code = st.text_input("HS编码" if i == 0 else " ", key=f"ci_hs_{sid}",
                                    placeholder="8516.10",
                                    label_visibility="visible" if i == 0 else "hidden")
        with cols[2]:
            quantity = st.number_input("数量" if i == 0 else " ", min_value=0, value=1000,
                                       key=f"ci_qty_{sid}",
                                       label_visibility="visible" if i == 0 else "hidden")
        with cols[3]:
            unit = st.selectbox("单位" if i == 0 else " ",
                                ["PCS", "SETS", "KG", "MT", "CARTON"],
                                key=f"ci_unit_{sid}",
                                label_visibility="visible" if i == 0 else "hidden")
        with cols[4]:
            unit_price = st.number_input("单价" if i == 0 else " ", min_value=0.0,
                                         value=5.0, step=0.01, format="%.2f",
                                         key=f"ci_price_{sid}",
                                         label_visibility="visible" if i == 0 else "hidden")
        with cols[5]:
            amount = quantity * unit_price
            st.text_input("金额" if i == 0 else " ", value=f"{amount:,.2f}",
                         key=f"ci_amt_{sid}", disabled=True,
                         label_visibility="visible" if i == 0 else "hidden")
        with cols[6]:
            origin = st.text_input("原产地" if i == 0 else " ", value="China",
                                   key=f"ci_origin_{sid}",
                                   label_visibility="visible" if i == 0 else "hidden")
        with cols[7]:
            if i == 0:
                st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"ci_del_{sid}", disabled=(len(st.session_state.packing_items) == 1)):
                remove_packing_item(i)
                st.rerun()

        items_data.append({
            "product": product, "hs_code": hs_code, "quantity": quantity,
            "unit": unit, "unit_price": unit_price,
            "amount": amount, "origin": origin,
        })

if st.button("➕ 添加产品行", use_container_width=True):
    add_packing_item()
    st.rerun()

generate_clicked = st.button("🚀 生成 PDF", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    valid_items = [item for item in items_data if item.get("product", "").strip()]
    if not valid_items:
        st.warning("⚠️ 请填写至少一个产品")
    else:
        shipper = {
            "company": seller_company,
            "address": seller_address,
            "phone": seller_phone,
        }
        consignee = {
            "company": buyer_company,
            "address": buyer_address,
            "contact": buyer_contact,
        }

        if doc_type.startswith("📦"):
            shipping_info = {
                "invoice_no": invoice_no,
                "date": inv_date,
                "port_of_loading": port_of_loading,
                "port_of_discharge": port_of_discharge,
                "vessel": vessel,
                "marks": marks,
            }
            with st.spinner("📄 正在生成装箱单 PDF..."):
                pdf_bytes = generate_packing_list_pdf(
                    items=valid_items,
                    shipper=shipper,
                    consignee=consignee,
                    shipping_info=shipping_info,
                )
            st.session_state.results["packing_pdf"] = pdf_bytes
            st.session_state.results["packing_doc_type"] = "packing_list"
        else:
            seller = {**shipper, "bank_info": seller_bank}
            buyer = consignee
            trade_terms_data = {
                "invoice_no": invoice_no,
                "date": inv_date,
                "payment_terms": payment_terms,
                "trade_term": trade_term,
                "currency": currency,
                "port": port_of_loading,
            }
            with st.spinner("📄 正在生成商业发票 PDF..."):
                pdf_bytes = generate_commercial_invoice_pdf(
                    items=valid_items,
                    seller=seller,
                    buyer=buyer,
                    trade_terms=trade_terms_data,
                )
            st.session_state.results["packing_pdf"] = pdf_bytes
            st.session_state.results["packing_doc_type"] = "commercial_invoice"

        st.balloons()

# ── 展示已生成的 PDF ──────────────────────────────────
if st.session_state.results.get("packing_pdf"):
    st.markdown(
        '<div class="success-box">'
        '<div style="font-size:1.5rem;">✅</div>'
        '<div class="success-title">PDF 生成完成！</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    doc_label = "装箱单" if st.session_state.results.get("packing_doc_type") == "packing_list" else "商业发票"
    file_prefix = "packing_list" if st.session_state.results.get("packing_doc_type") == "packing_list" else "commercial_invoice"
    st.download_button(
        f"📥 下载{doc_label} PDF",
        st.session_state.results["packing_pdf"],
        file_name=f"{file_prefix}_{invoice_no}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 装箱发票</div>', unsafe_allow_html=True)
