"""
pages/3_📄_报价单.py
支持多产品（多行 SKU）填写，生成专业 PDF 报价单。
"""
from __future__ import annotations

import os
import streamlit as st
from utils.ui_helpers import inject_css, check_auth
from utils.pdf_gen import generate_quote_pdf
from utils.pricing import check_feature_access
from utils.user_auth import get_current_user

st.set_page_config(page_title="报价单 | 外贸AI助手", page_icon="📄", layout="wide")
inject_css()
check_auth()

# Single-tenant: one logo per deployment (shared across all sessions)
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "company_logo.png")

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📄 报价单生成</h1>
    <p class="hero-subtitle">支持多产品 SKU，一键生成专业 PDF 报价单</p>
</div>
""", unsafe_allow_html=True)

# ── SKU 列表管理 ──────────────────────────────────────
if "sku_list" not in st.session_state:
    import uuid
    st.session_state.sku_list = [
        {"id": str(uuid.uuid4())[:6], "product": "", "model": "", "price": 0.0, "quantity": 100, "unit": "PCS"}
    ]


def add_sku():
    import uuid
    st.session_state.sku_list.append(
        {"id": str(uuid.uuid4())[:6], "product": "", "model": "", "price": 0.0, "quantity": 100, "unit": "PCS"}
    )


def remove_sku(idx: int):
    if len(st.session_state.sku_list) > 1:
        st.session_state.sku_list.pop(idx)


# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)

# --- 产品列表 ---
st.markdown("#### 🛒 产品明细")

UNITS = ["PCS", "SETS", "BOX", "CARTON", "PALLET", "KG", "MT"]

sku_list = st.session_state.sku_list
subtotal = 0.0

for i, sku in enumerate(sku_list):
    # Ensure each SKU has a stable ID for widget keys
    if "id" not in sku:
        import uuid
        sku["id"] = str(uuid.uuid4())[:6]
    sid = sku["id"]
    cols = st.columns([3, 2, 1.5, 1.5, 1.5, 0.7])
    with cols[0]:
        sku["product"] = st.text_input(
            "产品名称 *" if i == 0 else " ",
            value=sku["product"],
            placeholder="Product Name",
            key=f"sku_product_{sid}",
            label_visibility="visible" if i == 0 else "hidden",
        )
    with cols[1]:
        sku["model"] = st.text_input(
            "型号/规格" if i == 0 else " ",
            value=sku["model"],
            placeholder="Model/Spec",
            key=f"sku_model_{sid}",
            label_visibility="visible" if i == 0 else "hidden",
        )
    with cols[2]:
        sku["price"] = st.number_input(
            "单价 (USD)" if i == 0 else " ",
            min_value=0.0, value=float(sku["price"]),
            step=0.01, format="%.2f",
            key=f"sku_price_{sid}",
            label_visibility="visible" if i == 0 else "hidden",
        )
    with cols[3]:
        sku["quantity"] = st.number_input(
            "数量" if i == 0 else " ",
            min_value=1, value=int(sku["quantity"]),
            key=f"sku_qty_{sid}",
            label_visibility="visible" if i == 0 else "hidden",
        )
    with cols[4]:
        sku["unit"] = st.selectbox(
            "单位" if i == 0 else " ",
            UNITS,
            index=UNITS.index(sku["unit"]) if sku["unit"] in UNITS else 0,
            key=f"sku_unit_{sid}",
            label_visibility="visible" if i == 0 else "hidden",
        )
    with cols[5]:
        if i == 0:
            st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️", key=f"del_sku_{sid}", help="删除此行",
                     disabled=(len(sku_list) == 1)):
            remove_sku(i)
            st.rerun()

    subtotal += sku["price"] * sku["quantity"]

col_add, col_total = st.columns([2, 3])
with col_add:
    if st.button("➕ 添加产品行", use_container_width=True):
        add_sku()
        st.rerun()
with col_total:
    if subtotal > 0:
        st.metric("💰 报价总额", f"${subtotal:,.2f}")

st.markdown('<hr style="margin:1.2rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)

# --- 客户信息（Buyer / 收单方）---
st.markdown("#### 👤 客户信息（收单方）")

col_b1, col_b2 = st.columns(2)
with col_b1:
    buyer_company = st.text_input("客户公司", placeholder="ABC Trading Co.", value=st.session_state.get("quote_buyer_company", ""))
    buyer_contact = st.text_input("客户联系人", placeholder="John Smith", value=st.session_state.get("quote_buyer_contact", ""))
with col_b2:
    buyer_email = st.text_input("客户邮箱", placeholder="john@abctrading.com", value=st.session_state.get("quote_buyer_email", ""))
    st.markdown('<div class="tip-card">💡 填写客户信息会在 PDF 抬头显示"Buyer"栏，更专业。</div>', unsafe_allow_html=True)

st.markdown('<hr style="margin:1.2rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)

# --- 交易条款 ---
st.markdown("#### 📦 交易条款")

col_t1, col_t2, col_t3, col_t4 = st.columns(4)
with col_t1:
    payment  = st.selectbox("付款方式", ["T/T 30%", "T/T 50%", "L/C at sight", "D/P", "PayPal", "Western Union"])
with col_t2:
    currency = st.selectbox("币种", ["USD", "EUR", "GBP", "CNY", "AUD", "CAD"], help="选择报价币种")
with col_t3:
    delivery = st.text_input("交货期", value="15-20 days")
with col_t4:
    validity = st.text_input("报价有效期", value="30 days")

col_t5, col_t6 = st.columns(2)
with col_t5:
    shipping = st.text_input("发货港口", placeholder="Shanghai, China")
with col_t6:
    quote_notes = st.text_input("备注（可选）", placeholder="MOQ 500pcs, 包装: 独立彩盒")

st.markdown('<hr style="margin:1.2rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)

# --- 公司信息 ---
st.markdown("#### 🏢 公司信息")

col_c1, col_c2 = st.columns(2)
with col_c1:
    company_name = st.text_input("公司名称", value=st.session_state.get("quote_company_saved", "Your Company Name"))
    contact_name = st.text_input("联系人姓名", value=st.session_state.get("quote_contact_saved", "Your Name"))
with col_c2:
    email = st.text_input("联系邮箱", value=st.session_state.get("quote_email_saved", "sales@yourcompany.com"))
    phone = st.text_input("联系电话", value=st.session_state.get("quote_phone_saved", "+86-XXX-XXXXXXX"))

# --- 公司Logo（可选）---
st.markdown("#### 🖼️ 公司Logo（可选）")

# Feature gating: logo upload requires Pro tier
_current_user = get_current_user()
_logo_access = True
if _current_user and _current_user.get("username") not in (None, "admin"):
    _logo_access = check_feature_access(_current_user["username"], "logo_upload")

if not _logo_access:
    st.info("🔒 Logo 上传功能需要 Pro 套餐，请升级以解锁")
else:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150, caption="当前Logo")
        if st.button("🗑️ 删除Logo", key="remove_logo"):
            os.remove(LOGO_PATH)
            st.success("Logo已删除")
            st.rerun()

    uploaded_logo = st.file_uploader(
        "上传公司Logo",
        type=["png", "jpg", "jpeg"],
        help="支持 PNG/JPG 格式，建议尺寸不超过 500x200px",
        key="logo_uploader",
    )
    if uploaded_logo:
        os.makedirs(os.path.dirname(LOGO_PATH), exist_ok=True)
        with open(LOGO_PATH, "wb") as f:
            f.write(uploaded_logo.getvalue())
        st.success("✅ Logo已保存")
        st.rerun()

generate_clicked = st.button("🚀 生成报价单 (PDF)", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    valid_skus = [s for s in sku_list if s["product"].strip()]
    if not valid_skus:
        st.warning("⚠️ 请填写至少一个产品名称")
    elif all(s["price"] <= 0 for s in valid_skus):
        st.warning("⚠️ 请为至少一个产品填写单价")
    else:
        # 保存公司信息
        st.session_state["quote_company_saved"] = company_name
        st.session_state["quote_contact_saved"] = contact_name
        st.session_state["quote_email_saved"]   = email
        st.session_state["quote_phone_saved"]   = phone
        st.session_state["quote_buyer_company"] = buyer_company
        st.session_state["quote_buyer_contact"] = buyer_contact
        st.session_state["quote_buyer_email"]   = buyer_email

        # 报价单编号自增
        if "quote_number" not in st.session_state:
            st.session_state["quote_number"] = 0
        st.session_state["quote_number"] += 1
        quote_no = f"Q-2026-{st.session_state['quote_number']:03d}"

        with st.spinner("📄 正在生成 PDF..."):
            logo_path_arg = LOGO_PATH if os.path.exists(LOGO_PATH) else None
            pdf_bytes = generate_quote_pdf(
                skus=valid_skus,
                payment=payment,
                delivery=delivery,
                validity=validity,
                shipping=shipping,
                company_name=company_name,
                contact_name=contact_name,
                email=email,
                phone=phone,
                buyer_company=buyer_company,
                buyer_contact=buyer_contact,
                buyer_email=buyer_email,
                logo_path=logo_path_arg,
            )

        st.session_state.results["quote_pdf"]      = pdf_bytes
        st.session_state.results["quote_subtotal"] = sum(s["price"] * s["quantity"] for s in valid_skus)
        st.session_state.results["quote_sku_count"]= len(valid_skus)
        st.session_state.results["quote_just_gen"] = True
        st.session_state.results["quote_number"]   = quote_no
        st.session_state.results["quote_currency"] = currency
        st.session_state.results["quote_notes"]    = quote_notes

# ── 展示已生成的 PDF ──────────────────────────────────
if st.session_state.results.get("quote_pdf"):
    # 气球只在刚生成时触发一次
    if st.session_state.results.pop("quote_just_gen", False):
        st.balloons()

    subtotal_saved   = st.session_state.results.get("quote_subtotal", 0.0)
    sku_count_saved  = st.session_state.results.get("quote_sku_count", 1)
    quote_no_saved   = st.session_state.results.get("quote_number", "Q-2026-001")
    currency_saved   = st.session_state.results.get("quote_currency", "USD")

    c1, c2, c3 = st.columns(3)
    c1.metric("📋 报价单号", quote_no_saved)
    c2.metric("📦 产品种数", f"{sku_count_saved} 种")
    c3.metric("💰 报价总额", f"{currency_saved} {subtotal_saved:,.2f}")

    st.markdown(
        '<div class="success-box">'
        '<div style="font-size:1.5rem;">✅</div>'
        '<div class="success-title">报价单生成完成！</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    first_product = (sku_list[0]["product"] or "报价单") if sku_list else "报价单"
    st.download_button(
        "📥 下载报价单 PDF",
        st.session_state.results["quote_pdf"],
        file_name=f"报价单_{first_product}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 报价单生成</div>', unsafe_allow_html=True)
