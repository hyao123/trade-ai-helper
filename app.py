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
    
    /* 全局 */
    .block-container {
        padding: 2rem 3rem !important;
        max-width: 1400px !important;
    }
    
    /* 标题 */
    h1, h2, h3 {
        font-weight: 600 !important;
    }
    
    /* 顶部Hero */
    .hero-section {
        background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 50%, #8b5cf6 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    }
    .hero-title {
        font-size: 2rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* 价格标签 */
    .price-tag {
        background: rgba(255,255,255,0.2);
        padding: 0.5rem 1rem;
        border-radius: 30px;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    .price-tag .price {
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    /* 统计卡片 */
    .stat-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    .stat-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a5f;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.25rem;
    }
    
    /* 功能卡片导航 */
    .feature-nav {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    .feature-nav-item {
        background: white;
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex: 1;
        min-width: 200px;
        justify-content: center;
    }
    .feature-nav-item:hover {
        border-color: #3b82f6;
        background: #f8fafc;
    }
    .feature-nav-item.active {
        border-color: #3b82f6;
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        color: #1e40af;
    }
    .feature-nav-item .icon {
        font-size: 1.5rem;
    }
    .feature-nav-item .text {
        font-weight: 500;
    }
    
    /* 表单区域 */
    .form-section {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        border: 1px solid #f0f0f0;
        margin-bottom: 1.5rem;
    }
    .form-section-title {
        color: #1e3a5f;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* 输入框样式优化 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        border-radius: 10px;
        border: 1.5px solid #e5e7eb;
        padding: 0.75rem 1rem;
        transition: all 0.2s;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }
    
    /* 按钮 */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* 标签页 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        border-radius: 10px 10px 0 0;
        font-weight: 500;
    }
    
    /* 成功提示 */
    .success-section {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        border: 2px solid #22c55e;
        margin: 1rem 0;
    }
    .success-section .icon {
        font-size: 2.5rem;
    }
    .success-section .title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #166534;
        margin-top: 0.5rem;
    }
    
    /* 结果展示 */
    .result-box {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
    }
    .result-box textarea {
        background: white;
        border-radius: 8px;
    }
    
    /* 提示卡片 */
    .tip-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #f59e0b;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    
    /* 分隔线 */
    .section-divider {
        margin: 2rem 0;
        border: none;
        border-top: 1px dashed #e5e7eb;
    }
    
    /* 底部 */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #9ca3af;
        font-size: 0.85rem;
    }
    .footer a {
        color: #6b7280;
        text-decoration: none;
        margin: 0 0.5rem;
    }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #0f172a 100%);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p {
        color: white !important;
    }
    
    /* 响应式 */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem !important;
        }
        .feature-nav {
            flex-direction: column;
        }
        .feature-nav-item {
            min-width: auto;
        }
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
        <span>🎁</span>
        <span>首单特惠</span>
        <span class="price">¥29</span>
        <span>/年</span>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">📧</div>
        <div class="stat-value">4</div>
        <div class="stat-label">核心功能</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">🌍</div>
        <div class="stat-value">5+</div>
        <div class="stat-label">语种支持</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">⚡</div>
        <div class="stat-value">10s</div>
        <div class="stat-label">快速生成</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">📄</div>
        <div class="stat-value">PDF</div>
        <div class="stat-label">专业输出</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

features = [
    ("📧", "开发信", "开发信生成"),
    ("📩", "询盘回复", "询盘回复"),
    ("📄", "报价单", "报价单"),
    ("📑", "产品介绍", "产品介绍")
]

st.markdown('<div class="feature-nav">', unsafe_allow_html=True)
cols = st.columns(4)
for i, (icon, text, key) in enumerate(features):
    with cols[i]:
        if st.button(f"{icon} {text}", key=f"nav_{key}", 
                    use_container_width=True,
                    type="primary" if st.session_state.current_feature == key else "secondary"):
            st.session_state.current_feature = key
st.markdown('</div>', unsafe_allow_html=True)

current = st.session_state.current_feature

if current == "开发信":
    st.markdown("""
    <div class="form-section">
        <div class="form-section-title">📧 开发信生成</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="tip-card">💡 <b>使用提示：</b>填写详细的产品信息和卖点，生成更精准的开发信。建议包含产品认证、工厂资质等优势。</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        product = st.text_input("产品名称 *", placeholder="例如: LED Desk Lamp",
                               key="email_product")
        customer = st.text_input("目标客户 *", placeholder="例如: John Smith, ABC Company",
                               key="email_customer")
    with col2:
        tone = st.selectbox("选择风格", ["简洁专业 (50-80词)", "正式商务 (100-150词)", "亲切友好 (80-100词)"],
                           key="email_tone")
        tone_map = {"简洁专业 (50-80词)": "简洁专业", "正式商务 (100-150词)": "正式商务", "亲切友好 (80-100词)": "亲切友好"}
        tone = tone_map[tone]
        company_name = st.text_input("公司名称 (可选)", placeholder="您的公司名称",
                                     key="email_company")
    
    features_text = st.text_area("产品卖点 *", placeholder="每行一条卖点，例如：\n• 10年工厂经验\n• CE/RoHS/FCC认证\n• 支持OEM/ODM\n• 快速交货",
                                height=5, key="email_features")
    
    col_btn, col_sample = st.columns([3, 1])
    with col_btn:
        generate_btn = st.button("🚀 生成开发信", type="primary", use_container_width=True)
    with col_sample:
        st.button("📋 查看示例", use_container_width=True)
    
    if generate_btn:
        if not product or not customer:
            st.warning("⚠️ 请填写产品名称和目标客户")
        else:
            with st.spinner("🤖 AI正在生成专业开发信..."):
                result = generate_email(product, customer, features_text, tone)
            
            st.markdown("""
            <div class="success-section">
                <div class="icon">✅</div>
                <div class="title">开发信生成完成！</div>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
            
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.text_area("📝 生成结果", result, height=220, key="email_result")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📥 下载开发信",
                    result,
                    file_name=f"开发信_{product}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with col_d2:
                st.button("📋 一键复制", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif current == "询盘回复":
    st.markdown("""
    <div class="form-section">
        <div class="form-section-title">📩 询盘回复</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="tip-card">💡 <b>使用场景：</b>收到客户询盘后，快速生成专业回复，节省撰写时间。支持中英文回复。</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        inquiry = st.text_area("客户询盘内容 *", height=6, 
                             placeholder="粘贴客户发来的完整邮件内容...",
                             key="inquiry_text")
    with col2:
        customer_name = st.text_input("客户名称 (可选)", placeholder="例如: Mike Johnson",
                                     key="inquiry_customer")
        your_name = st.text_input("你的名称 (可选)", placeholder="您的名字",
                                 key="inquiry_yourname")
        your_company = st.text_input("公司名称", placeholder="您的公司",
                                    key="inquiry_company")
    
    reply_btn = st.button("🚀 生成回复", type="primary", use_container_width=True)
    
    if reply_btn:
        if not inquiry:
            st.warning("⚠️ 请粘贴客户询盘内容")
        else:
            with st.spinner("🤖 AI正在生成回复..."):
                result = reply_inquiry(inquiry, customer_name, your_name)
            
            st.markdown("""
            <div class="success-section">
                <div class="icon">✅</div>
                <div class="title">回复草稿生成完成！</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.text_area("📝 回复草稿", result, height=220, key="reply_result")
            st.download_button(
                "📥 下载回复",
                result,
                file_name="回复.txt",
                mime="text/plain",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

elif current == "报价单":
    st.markdown("""
    <div class="form-section">
        <div class="form-section-title">📄 报价单生成</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("产品名称 *", key="quote_product")
        model = st.text_input("型号/规格 (可选)", key="quote_model")
        price = st.number_input("单价 (USD) *", min_value=0.0, value=0.0, step=0.01, key="quote_price")
    with col2:
        quantity = st.number_input("数量 *", min_value=1, value=100, key="quote_qty")
        unit = st.selectbox("单位", ["PCS", "SETS", "BOX", "CARTON", "PALLET"], key="quote_unit")
    
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 📦 交易条款")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        payment = st.selectbox("付款方式", ["T/T 30%", "T/T 50%", "L/C at sight", "D/P", "PayPal", "Western Union"],
                           key="quote_payment")
    with col_t2:
        delivery = st.text_input("交货期", value="15-20 days", key="quote_delivery")
    with col_t3:
        validity = st.text_input("有效期", value="30 days", key="quote_validity")
    
    shipping = st.text_input("发货港口", placeholder="例如: Shanghai, China", key="quote_shipping")
    
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 🏢 公司信息")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        company_name = st.text_input("公司名称", value="Your Company Name", key="quote_company")
        contact_name = st.text_input("联系人", value="Your Name", key="quote_contact")
    with col_c2:
        email = st.text_input("邮箱", value="sales@company.com", key="quote_email")
        phone = st.text_input("电话", value="+86-XXX-XXXXXXX", key="quote_phone")
    
    quote_btn = st.button("🚀 生成报价单 (PDF)", type="primary", use_container_width=True)
    
    if quote_btn:
        if not product_name or price <= 0:
            st.warning("⚠️ 请填写产品名称和单价")
        else:
            with st.spinner("📄 正在生成PDF..."):
                pdf_data = generate_quote_pdf(
                    product_name, model, price, quantity, unit,
                    payment, delivery, validity, shipping,
                    company_name, contact_name, email, phone
                )
            
            st.balloons()
            total_value = price * quantity
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("💵 单价", f"${price:,.2f}")
            with col_stat2:
                st.metric("📦 数量", f"{quantity} {unit}")
            with col_stat3:
                st.metric("💰 总金额", f"${total_value:,.2f}")
            
            st.markdown("""
            <div class="success-section">
                <div class="icon">✅</div>
                <div class="title">报价单生成完成！</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.download_button(
                "📥 下载报价单 (PDF)",
                pdf_data,
                file_name=f"报价单_{product_name}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

elif current == "产品介绍":
    st.markdown("""
    <div class="form-section">
        <div class="form-section-title">📑 产品介绍生成</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="tip-card">💡 <b>适用场景：</b>制作产品画册、独立站产品描述、B2B平台产品介绍。支持多语种输出。</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        product = st.text_input("产品名称 *", key="intro_product")
        features = st.text_area("产品特点 *", height=5, 
                            placeholder="每行一条特点，例如：\n• 节能90%\n• 5年质保\n• 欧盟认证",
                            key="intro_features")
    with col2:
        target = st.selectbox("目标市场", ["美国", "欧洲", "南美", "东南亚", "全球"],
                          key="intro_target")
        lang = st.multiselect("输出语言", 
                          ["英语 English", "西班牙语 Spanish", "法语 French", "德语 German", "日语 Japanese"],
                          default=["英语 English"], key="intro_lang")
    
    lang_list = [l.split()[0] for l in lang]
    
    intro_btn = st.button("🚀 生成介绍", type="primary", use_container_width=True)
    
    if intro_btn:
        if not product or not features:
            st.warning("⚠️ 请填写产品名称和特点")
        else:
            with st.spinner("🤖 AI正在生成多语种介绍文案..."):
                result = generate_product_intro(product, features, target, lang_list)
            
            st.markdown("""
            <div class="success-section">
                <div class="icon">✅</div>
                <div class="title">产品介绍生成完成！</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.text_area("📝 产品介绍", result, height=280, key="intro_result")
            st.download_button(
                "📥 下载产品介绍",
                result,
                file_name=f"{product}_介绍.txt",
                mime="text/plain",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div class="footer">
    <p>💡 外贸AI助手 | 让外贸更简单</p>
    <p>
        <a href="#">使用条款</a> | 
        <a href="#">隐私政策</a> | 
        <a href="#">联系我们</a>
    </p>
</div>
""", unsafe_allow_html=True)