import streamlit as st
import os
from utils.ai_client import generate_email, reply_inquiry, generate_product_intro
from utils.pdf_gen import generate_quote_pdf

st.set_page_config(
    page_title="外贸AI助手 | TradeAI Pro",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif !important;
    }
    
    .block-container {
        padding: 2rem 3rem !important;
        max-width: 1400px !important;
    }
    
    h1, h2, h3 { font-weight: 600 !important; }
    
    .hero-section {
        background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 50%, #8b5cf6 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    .hero-subtitle { font-size: 1rem; opacity: 0.9; }
    
    .price-tag {
        background: rgba(255,255,255,0.2);
        padding: 0.4rem 1rem;
        border-radius: 20px;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.75rem;
        font-size: 0.9rem;
    }
    
    .stat-card {
        background: white;
        border-radius: 14px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #e5e7eb;
    }
    .stat-value { font-size: 1.6rem; font-weight: 700; color: #1e3a5f; }
    .stat-label { font-size: 0.8rem; color: #666; margin-top: 0.25rem; }
    
    .feature-nav {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }
    .feature-btn {
        flex: 1;
        padding: 1rem;
        border-radius: 12px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .main-form {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        border: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
    }
    .form-title {
        color: #1e3a5f;
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 1.25rem;
    }
    
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1.5px solid #e5e7eb;
        padding: 0.6rem 0.85rem;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.25rem;
    }
    
    .tip-card {
        background: #fef9c3;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        border-left: 3px solid #f59e0b;
        margin-bottom: 1rem;
        font-size: 0.85rem;
    }
    
    .success-box {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        border: 2px solid #22c55e;
        margin: 1rem 0;
    }
    .success-title { font-size: 1.1rem; font-weight: 600; color: #166534; }
    
    .result-area {
        background: #f8fafc;
        border-radius: 10px;
        padding: 1.25rem;
        border: 1px solid #e2e8f0;
        margin-top: 1rem;
    }
    
    .section-divider { margin: 1.5rem 0; border-top: 1px dashed #e5e7eb; }
    
    .footer {
        text-align: center;
        padding: 1.5rem;
        color: #9ca3af;
        font-size: 0.8rem;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #0f172a 100%);
    }
    
    @media (max-width: 768px) {
        .block-container { padding: 0.75rem !important; }
        .feature-nav { flex-direction: column; }
    }
</style>
""", unsafe_allow_html=True)

if 'current_feature' not in st.session_state:
    st.session_state.current_feature = "开发信"

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">💼 外贸AI助手</h1>
    <p class="hero-subtitle">AI赋能外贸 · 让业务增长更简单</p>
    <div class="price-tag">
        <span>🎁 首单特惠</span>
        <span style="font-weight:700;font-size:1.1rem;">¥29</span>
        <span>/年</span>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown('<div class="stat-card"><div class="stat-value">4</div><div class="stat-label">核心功能</div></div>', unsafe_allow_html=True)
with col2: st.markdown('<div class="stat-card"><div class="stat-value">5+</div><div class="stat-label">语种支持</div></div>', unsafe_allow_html=True)
with col3: st.markdown('<div class="stat-card"><div class="stat-value">10s</div><div class="stat-label">快速生成</div></div>', unsafe_allow_html=True)
with col4: st.markdown('<div class="stat-card"><div class="stat-value">PDF</div><div class="stat-label">专业输出</div></div>', unsafe_allow_html=True)

st.markdown("---")

features = [
    ("📧", "开发信生成", "开发信"),
    ("📩", "询盘回复", "询盘回复"),
    ("📄", "报价单", "报价单"),
    ("📑", "产品介绍", "产品介绍")
]

cols = st.columns(4)
for i, (icon, text, key) in enumerate(features):
    with cols[i]:
        btn_type = "primary" if st.session_state.current_feature == key else "secondary"
        if st.button(f"{icon} {text}", key=f"nav_{key}", use_container_width=True, type=btn_type):
            st.session_state.current_feature = key
            st.rerun()

current = st.session_state.current_feature

if current == "开发信":
    st.markdown('<div class="main-form"><div class="form-title">📧 开发信生成</div>', unsafe_allow_html=True)
    st.markdown('<div class="tip-card">💡 填写详细的产品信息和卖点，生成更精准的开发信。</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        product = st.text_input("产品名称 *", placeholder="例如: LED Desk Lamp", key="email_product")
        customer = st.text_input("目标客户 *", placeholder="例如: John Smith, ABC Company", key="email_customer")
    with col2:
        tone = st.selectbox("选择风格", ["简洁专业 (50-80词)", "正式商务 (100-150词)", "亲切友好 (80-100词)"], key="email_tone")
        tone_map = {"简洁专业 (50-80词)": "简洁专业", "正式商务 (100-150词)": "正式商务", "亲切友好 (80-100词)": "亲切友好"}
        tone = tone_map[tone]
        company_name = st.text_input("公司名称 (可选)", placeholder="您的公司名称", key="email_company")
    
    features_text = st.text_area("产品卖点 *", placeholder="每行一条卖点，例如：\n• 10年工厂经验\n• CE/RoHS/FCC认证\n• 支持OEM/ODM\n• 快速交货\n• 免费样品", height=150, key="email_features")
    
    generate_btn = st.button("🚀 生成开发信", type="primary", use_container_width=True)
    
    if generate_btn:
        if not product or not customer:
            st.warning("⚠️ 请填写产品名称和目标客户")
        else:
            with st.spinner("🤖 AI正在生成..."):
                result = generate_email(product, customer, features_text, tone)
            
            st.markdown('<div class="success-box"><div style="font-size:1.5rem;">✅</div><div class="success-title">开发信生成完成！</div></div>', unsafe_allow_html=True)
            st.balloons()
            
            st.markdown('<div class="result-area">', unsafe_allow_html=True)
            st.text_area("📝 生成结果", result, height=200, key="email_result")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button("📥 下载", result, file_name=f"开发信_{product}.txt", mime="text/plain", use_container_width=True)
            with col_d2:
                st.button("📋 复制", use_container_width=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif current == "询盘回复":
    st.markdown('<div class="main-form"><div class="form-title">📩 询盘回复</div>', unsafe_allow_html=True)
    st.markdown('<div class="tip-card">💡 粘贴客户询盘邮件，AI生成专业回复草稿。</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        inquiry = st.text_area("客户询盘内容 *", height=150, placeholder="粘贴客户发来的完整邮件内容...", key="inquiry_text")
    with col2:
        customer_name = st.text_input("客户名称 (可选)", placeholder="例如: Mike Johnson", key="inquiry_customer")
        your_name = st.text_input("你的名称 (可选)", placeholder="您的名字", key="inquiry_yourname")
        your_company = st.text_input("公司名称", placeholder="您的公司", key="inquiry_company")
    
    reply_btn = st.button("🚀 生成回复", type="primary", use_container_width=True)
    
    if reply_btn:
        if not inquiry:
            st.warning("⚠️ 请粘贴客户询盘内容")
        else:
            with st.spinner("🤖 AI正在生成..."):
                result = reply_inquiry(inquiry, customer_name, your_name)
            
            st.markdown('<div class="success-box"><div style="font-size:1.5rem;">✅</div><div class="success-title">回复草稿生成完成！</div></div>', unsafe_allow_html=True)
            
            st.markdown('<div class="result-area">', unsafe_allow_html=True)
            st.text_area("📝 回复草稿", result, height=200, key="reply_result")
            st.download_button("📥 下载", result, file_name="回复.txt", mime="text/plain", use_container_width=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif current == "报价单":
    st.markdown('<div class="main-form"><div class="form-title">📄 报价单生成</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("产品名称 *", key="quote_product")
        model = st.text_input("型号/规格", key="quote_model")
        price = st.number_input("单价 (USD) *", min_value=0.0, value=0.0, step=0.01, key="quote_price")
    with col2:
        quantity = st.number_input("数量 *", min_value=1, value=100, key="quote_qty")
        unit = st.selectbox("单位", ["PCS", "SETS", "BOX", "CARTON", "PALLET"], key="quote_unit")
    
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 📦 交易条款")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        payment = st.selectbox("付款方式", ["T/T 30%", "T/T 50%", "L/C", "D/P", "PayPal"], key="quote_payment")
    with col_t2:
        delivery = st.text_input("交货期", value="15-20 days", key="quote_delivery")
    with col_t3:
        validity = st.text_input("有效期", value="30 days", key="quote_validity")
    
    shipping = st.text_input("发货港口", placeholder="例如: Shanghai, China", key="quote_shipping")
    
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 🏢 公司信息")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        company_name = st.text_input("公司名称", value="Your Company", key="quote_company")
        contact_name = st.text_input("联系人", value="Your Name", key="quote_contact")
    with col_c2:
        email = st.text_input("邮箱", value="sales@company.com", key="quote_email")
        phone = st.text_input("电话", value="+86-XXX-XXXXXXX", key="quote_phone")
    
    quote_btn = st.button("🚀 生成报价单 (PDF)", type="primary", use_container_width=True)
    
    if quote_btn:
        if not product_name or price <= 0:
            st.warning("⚠️ 请填写产品名称和单价")
        else:
            with st.spinner("📄 生成中..."):
                pdf_data = generate_quote_pdf(product_name, model, price, quantity, unit, payment, delivery, validity, shipping, company_name, contact_name, email, phone)
            
            st.balloons()
            total = price * quantity
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1: st.metric("💵 单价", f"${price:,.2f}")
            with col_s2: st.metric("📦 数量", f"{quantity}")
            with col_s3: st.metric("💰 总金额", f"${total:,.2f}")
            
            st.markdown('<div class="success-box"><div style="font-size:1.5rem;">✅</div><div class="success-title">报价单生成完成！</div></div>', unsafe_allow_html=True)
            st.download_button("📥 下载报价单 (PDF)", pdf_data, file_name=f"报价单_{product_name}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif current == "产品介绍":
    st.markdown('<div class="main-form"><div class="form-title">📑 产品介绍生成</div>', unsafe_allow_html=True)
    st.markdown('<div class="tip-card">💡 输入产品信息，生成多语种产品介绍文案。</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        product = st.text_input("产品名称 *", key="intro_product")
        features = st.text_area("产品特点 *", height=150, placeholder="每行一条特点，例如：\n• 节能90%\n• 5年质保\n• 欧盟认证\n• 环保材料", key="intro_features")
    with col2:
        target = st.selectbox("目标市场", ["美国", "欧洲", "南美", "东南亚", "全球"], key="intro_target")
        lang = st.multiselect("输出语言", ["英语", "西班牙语", "法语", "德语", "日语"], default=["英语"], key="intro_lang")
    
    lang_list = lang if lang else ["英语"]
    intro_btn = st.button("🚀 生成介绍", type="primary", use_container_width=True)
    
    if intro_btn:
        if not product or not features:
            st.warning("⚠️ 请填写产品名称和特点")
        else:
            with st.spinner("🤖 AI生成中..."):
                result = generate_product_intro(product, features, target, lang_list)
            
            st.markdown('<div class="success-box"><div style="font-size:1.5rem;">✅</div><div class="success-title">产品介绍生成完成！</div></div>', unsafe_allow_html=True)
            
            st.markdown('<div class="result-area">', unsafe_allow_html=True)
            st.text_area("📝 产品介绍", result, height=250, key="intro_result")
            st.download_button("📥 下载", result, file_name=f"{product}_介绍.txt", mime="text/plain", use_container_width=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div class="footer"><p>💡 外贸AI助手 | 让外贸更简单</p></div>', unsafe_allow_html=True)