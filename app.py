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
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
    
    * {
        font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif !important;
    }
    
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1200px;
    }
    
    h1, h2, h3 {
        font-weight: 700 !important;
    }
    
    /* 顶部横幅 */
    .hero-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
    }
    
    /* 功能卡片 */
    .feature-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        border-color: #667eea;
    }
    
    .feature-card.active {
        border: 2px solid #667eea;
        background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
    }
    
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .feature-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1e3a5f;
        margin-bottom: 0.25rem;
    }
    
    .feature-desc {
        font-size: 0.85rem;
        color: #666;
    }
    
    /* 按钮样式 */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
    }
    
    /* 输入框焦点 */
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
    }
    
    /* 标签页 */
    .stTabs [data-baseweb="tab-list"] button {
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: 500;
    }
    
    /* 提示框 */
    .tip-box {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    
    /* 统计数字 */
    .stat-box {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #666;
    }
    
    /* 成功动画 */
    .success-box {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    
    /* 阴影效果 */
    .card-shadow {
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0

st.markdown("""
<div class="hero-banner">
    <h1 style="margin: 0; font-size: 2rem;">💼 外贸AI助手</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
        AI赋能外贸 �� 让你更专注于业务增长
    </p>
</div>
""", unsafe_allow_html=True)

col_h1, col_h2, col_h3 = st.columns(3)
with col_h1:
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">4</div>
        <div class="stat-label">核心功能</div>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">5+</div>
        <div class="stat-label">语种支持</div>
    </div>
    """, unsafe_allow_html=True)
with col_h3:
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">1min</div>
        <div class="stat-label">快速生成</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

tabs = st.tabs([
    "📧 开发信生成", 
    "📩 询盘回复", 
    "📄 报价单", 
    "📑 产品介绍"
])

with tabs[0]:
    st.markdown("### 📧 开发信生成")
    st.markdown("*输入产品和客户信息，AI自动生成专业英文开发信*")
    
    st.markdown("""
    <div class="tip-box">
        💡 <b>提示：</b>填写越详细的信息，生成的开
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        product = st.text_input("产品名称 *", placeholder="例如: LED Desk Lamp, Wireless Earbuds",
                               key="email_product")
        customer = st.text_input("目标客户 *", placeholder="例如: John Smith, ABC Company",
                               key="email_customer")
    with col2:
        tone = st.selectbox("选择风格", ["简洁专业 (50-80词)", "正式商务 (100-150词)", "亲切友好 (80-100词)"],
                           key="email_tone")
        tone_map = {"简洁专业 (50-80词)": "简洁专业", "正式商务 (100-150词)": "正式商务", "亲切友好 (80-100词)": "亲切友好"}
        tone = tone_map[tone]
    
    features = st.text_area("产品卖点 *", placeholder="每行一条卖点，例如：\n• 10年工厂经验\n• CE/RoHS/FCC认证\n• 支持OEM/ODM\n• 快速交货",
                        height=5, key="email_features")
    
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    with col_btn1:
        generate_btn = st.button("🚀 生成开发信", type="primary", use_container_width=True)
    with col_btn2:
        if st.button("📋 示例", use_container_width=True):
            st.info("💡 **简洁专业风格示例：**\n\nDear John,\n\nI came across your company and believe we can be a reliable supplier for your LED lighting needs.\n\nWe're a 10-year manufacturer with CE/RoHS certifications...\n\nBest regards")
    with col_btn3:
        clear_btn = st.button("🗑️ 清空", use_container_width=True)
    
    if generate_btn:
        if not product or not customer:
            st.warning("⚠️ 请填写 * 号必填项")
        else:
            with st.spinner("🤖 AI正在生成专业开发信..."):
                result = generate_email(product, customer, features, tone)
            
            st.markdown("""
            <div class="success-box" style="margin-bottom: 1rem;">
                ✅ 开发信生成完成！可直接下载或复制使用
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
            
            st.text_area("📝 生成结果", result, height=250, key="email_result")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📥 下载开发信 (TXT)",
                    result,
                    file_name=f"开发信_{product}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with col_d2:
                st.text_input("复制链接", value=result, key="copy_link", type="default")

with tabs[1]:
    st.markdown("### 📩 询盘回复")
    st.markdown("*粘贴客户询盘邮件，AI生成专业回复草稿*")
    
    st.markdown("""
    <div class="tip-box">
        💡 <b>使用场景：</b>收到客户询盘后，快速生成专业回复，节省撰写时间
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        inquiry = st.text_area("客户询盘内容 *", height=6, 
                             placeholder="粘贴客户发来的完整邮件内容...",
                             key="inquiry_text")
        customer_name = st.text_input("客户名称 (可选)", placeholder="例如: Mike Johnson",
                                     key="inquiry_customer")
    with col2:
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
            
            st.success("✅ 回复草稿生成完成！")
            st.text_area("📝 回复草稿", result, height=250, key="reply_result")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📥 下载回复",
                    result,
                    file_name="回复.txt",
                    mime="text/plain",
                    use_container_width=True
                )

with tabs[2]:
    st.markdown("### 📄 报价单生成")
    st.markdown("*填写产品信息，生成专业PDF报价单*")
    
    with st.expander("💡 如何使用", expanded=False):
        st.markdown("""
        1. 填写产品基本信息（名称、价格、数量）
        2. 设置交易条款（付款方式、交货期等）
        3. 点击生成PDF
        4. 下载后发送给客户
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("产品名称 *", key="quote_product")
        model = st.text_input("型号/规格 (可选)", key="quote_model")
        price = st.number_input("单价 (USD) *", min_value=0.0, value=0.0, step=0.01, key="quote_price")
    with col2:
        quantity = st.number_input("数量 *", min_value=1, value=100, key="quote_qty")
        unit = st.selectbox("单位", ["PCS", "SETS", "BOX", "CARTON", "PALLET"], key="quote_unit")
    
    st.markdown("---")
    st.markdown("#### 📦 交易条款")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        payment = st.selectbox("付款方式", ["T/T 30%", "T/T 50%", "L/C at sight", "D/P", "PayPal", "Western Union"],
                           key="quote_payment")
    with col_t2:
        delivery = st.text_input("交货期", value="15-20 days", key="quote_delivery")
    with col_t3:
        validity = st.text_input("有效期", value="30 days", key="quote_validity")
    
    shipping = st.text_input("发货港口", placeholder="例如: Shanghai, China", key="quote_shipping")
    
    st.markdown("---")
    st.markdown("#### 🏢 公司信息 (用于报价单)")
    
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
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("💵 单价", f"${price:,.2f}")
            with col_stat2:
                st.metric("💰 总金额", f"${total_value:,.2f}")
            
            st.success("✅ 报价单生成完成！")
            st.download_button(
                "📥 下载报价单 (PDF)",
                pdf_data,
                file_name=f"报价单_{product_name}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

with tabs[3]:
    st.markdown("### 📑 产品介绍生成")
    st.markdown("*输入产品信息，生成多语种产品介绍文案*")
    
    st.markdown("""
    <div class="tip-box">
        💡 <b>适用场景：</b>制作产品画册、独立站产品描述、B2B平台产品介绍
    </div>
    """, unsafe_allow_html=True)
    
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
            
            st.success("✅ 产品介绍生成完成！")
            st.text_area("📝 产品介绍", result, height=300, key="intro_result")
            
            st.download_button(
                "📥 下载产品介绍",
                result,
                file_name=f"{product}_介绍.txt",
                mime="text/plain",
                use_container_width=True
            )

st.markdown("---")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <h4>📧 开发信</h4>
        <p style="color: #666; font-size: 14px;">专业英文开发信</p>
    </div>
    """, unsafe_allow_html=True)
with col_f2:
    st.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <h4>📩 询盘回复</h4>
        <p style="color: #666; font-size: 14px;">快速响应客户</p>
    </div>
    """, unsafe_allow_html=True)
with col_f3:
    st.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <h4>📄 报价单</h4>
        <p style="color: #666; font-size: 14px;">专业PDF报价</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; padding: 2rem; font-size: 14px;">
    <p>💡 外贸AI助手 | 让外贸更简单</p>
    <p>
        <a href="#" style="color: #999; margin: 0 10px;">使用条款</a> | 
        <a href="#" style="color: #999; margin: 0 10px;">隐私政策</a> | 
        <a href="#" style="color: #999; margin: 0 10px;">联系我们</a>
    </p>
</div>
""", unsafe_allow_html=True)