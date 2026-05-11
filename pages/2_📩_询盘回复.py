"""
pages/2_📩_询盘回复.py
粘贴客户询盘，AI 生成专业英文回复草稿，支持流式输出。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result
from utils.ai_client import reply_inquiry

st.set_page_config(page_title="询盘回复 | 外贸AI助手", page_icon="📩", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📩 询盘回复</h1>
    <p class="hero-subtitle">粘贴客户询盘，AI 生成专业回复草稿</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 粘贴完整询盘内容，AI 会逐条回答客户问题并提供报价区间。</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 2])
with col1:
    inquiry = st.text_area(
        "客户询盘内容 *",
        height=200,
        placeholder="粘贴客户发来的完整邮件内容...\n\nHi, I'm interested in your LED desk lamps...",
        value=st.session_state.get("inquiry_text_val", ""),
    )
with col2:
    customer_name = st.text_input("客户姓名（可选）", placeholder="例如: Mike Johnson",
                                   value=st.session_state.get("inquiry_customer_val", ""))
    your_name     = st.text_input("你的姓名（可选）", placeholder="签名用，例如: Tom",
                                   value=st.session_state.get("inquiry_your_name_val", ""))
    company_name  = st.text_input("公司名称（可选）", placeholder="您的公司名称，用于签名",
                                   value=st.session_state.get("inquiry_company_val", ""))
    stream_mode   = st.toggle("⚡ 流式输出（实时显示）", value=True)

generate_clicked = st.button("🚀 生成回复", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not inquiry.strip():
        st.warning("⚠️ 请粘贴客户询盘内容")
    else:
        # 保存表单值
        st.session_state["inquiry_text_val"]      = inquiry
        st.session_state["inquiry_customer_val"]  = customer_name
        st.session_state["inquiry_your_name_val"] = your_name
        st.session_state["inquiry_company_val"]   = company_name
        st.session_state.results.pop("inquiry", None)

        fname = f"询盘回复_{customer_name or '客户'}.txt"
        if stream_mode:
            result = reply_inquiry(inquiry, customer_name, your_name, company_name, stream=True)
            show_result(result, "inquiry", label="📝 回复草稿", file_name=fname)
        else:
            with st.spinner("🤖 AI 正在生成..."):
                result = reply_inquiry(inquiry, customer_name, your_name, company_name, stream=False)
            st.session_state.results["inquiry"] = result
            show_result(result, "inquiry", label="📝 回复草稿", file_name=fname, balloons=True)

elif st.session_state.results.get("inquiry"):
    show_result(
        st.session_state.results["inquiry"],
        "inquiry",
        label="📝 回复草稿（上次结果）",
        file_name="询盘回复.txt",
        balloons=False,
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 询盘回复</div>', unsafe_allow_html=True)
