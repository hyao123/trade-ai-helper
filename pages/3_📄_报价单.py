"""
pages/3_📄_报价单.py
填写产品与交易条款，生成专业 PDF 报价单。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth
from utils.pdf_gen import generate_quote_pdf

st.set_page_config(page_title="报价单 | 外贸AI助手", page_icon="📄", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📄 报价单生成</h1>
    <p class="hero-subtitle">填写产品信息，一键生成专业 PDF 报价单</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)

st.markdown("#### 🛒 产品信息")
col1, col2, col3 = st.columns(3)
with col1:
    product_name = st.text_input("产品名称 *", placeholder="LED Desk Lamp")
    model        = st.text_input("型号 / 规格", placeholder="Model XR-200")
with col2:
    price    = st.number_input("单价 (USD) *", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    quantity = st.number_input("数量 *", min_value=1, value=100, step=1)
with col3:
    unit    = st.selectbox("单位", ["PCS", "SETS", "BOX", "CARTON", "PALLET"])
    st.markdown("<br>", unsafe_allow_html=True)
    if price > 0 and quantity > 0:
        st.metric("💰 预计总额", f"${price * quantity:,.2f} USD")

st.markdown('<hr style="margin:1.2rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)
st.markdown("#### 📦 交易条款")

col_t1, col_t2, col_t3, col_t4 = st.columns(4)
with col_t1:
    payment  = st.selectbox("付款方式", ["T/T 30%", "T/T 50%", "L/C at sight", "D/P", "PayPal"])
with col_t2:
    delivery = st.text_input("交货期", value="15-20 days")
with col_t3:
    validity = st.text_input("报价有效期", value="30 days")
with col_t4:
    shipping = st.text_input("发货港口", placeholder="Shanghai, China")

st.markdown('<hr style="margin:1.2rem 0;border-top:1px dashed #e5e7eb;">', unsafe_allow_html=True)
st.markdown("#### 🏢 公司信息")

col_c1, col_c2 = st.columns(2)
with col_c1:
    company_name = st.text_input("公司名称", value="Your Company Name")
    contact_name = st.text_input("联系人姓名", value="Your Name")
with col_c2:
    email = st.text_input("联系邮箱", value="sales@yourcompany.com")
    phone = st.text_input("联系电话", value="+86-XXX-XXXXXXX")

generate_clicked = st.button("🚀 生成报价单 (PDF)", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product_name or price <= 0:
        st.warning("⚠️ 请填写产品名称和单价")
    else:
        with st.spinner("📄 正在生成 PDF..."):
            pdf_bytes = generate_quote_pdf(
                product_name, model, price, quantity, unit,
                payment, delivery, validity, shipping,
                company_name, contact_name, email, phone,
            )
        st.session_state.results["quote_pdf"]     = pdf_bytes
        st.session_state.results["quote_product"] = product_name
        st.session_state.results["quote_price"]   = price
        st.session_state.results["quote_qty"]     = quantity

# ── 展示已生成的 PDF ──────────────────────────────────
if st.session_state.results.get("quote_pdf"):
    pdf_bytes = st.session_state.results["quote_pdf"]
    q_product = st.session_state.results.get("quote_product", "product")
    q_price   = st.session_state.results.get("quote_price", 0.0)
    q_qty     = st.session_state.results.get("quote_qty", 0)

    st.balloons()
    c1, c2, c3 = st.columns(3)
    c1.metric("💵 单价",   f"${q_price:,.2f}")
    c2.metric("📦 数量",   f"{q_qty}")
    c3.metric("💰 总金额", f"${q_price * q_qty:,.2f}")

    st.markdown(
        '<div class="success-box">'
        '<div style="font-size:1.5rem;">✅</div>'
        '<div class="success-title">报价单生成完成！</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        "📥 下载报价单 PDF",
        pdf_bytes,
        file_name=f"报价单_{q_product}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 报价单生成</div>', unsafe_allow_html=True)
