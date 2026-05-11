"""
pages/1_📧_开发信.py
生成外贸开发信，支持流式输出。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result
from utils.ai_client import generate_email

st.set_page_config(page_title="开发信生成 | 外贸AI助手", page_icon="📧", layout="wide")
inject_css()
check_auth()

# 初始化 session
if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📧 开发信生成</h1>
    <p class="hero-subtitle">AI 撰写高转化率英文开发信，10 秒完成</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 填写越详细，生成效果越好。产品卖点建议写 3 条以上。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    product  = st.text_input("产品名称 *", placeholder="例如: LED Desk Lamp")
    customer = st.text_input("目标客户 *", placeholder="例如: John Smith, ABC Lighting Co.")
with col2:
    tone_label = st.selectbox(
        "邮件风格",
        ["简洁专业 (50-80词)", "正式商务 (100-150词)", "亲切友好 (80-100词)"]
    )
    tone_map = {
        "简洁专业 (50-80词)": "简洁专业",
        "正式商务 (100-150词)": "正式商务",
        "亲切友好 (80-100词)": "亲切友好",
    }
    tone = tone_map[tone_label]
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

features_text = st.text_area(
    "产品卖点 *",
    placeholder="每行一条，例如：\n• 10年工厂经验\n• CE/RoHS/FCC 认证\n• 支持 OEM/ODM\n• 15天快速交货",
    height=130,
)

generate_clicked = st.button("🚀 生成开发信", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product or not customer:
        st.warning("⚠️ 请填写产品名称和目标客户")
    else:
        if stream_mode:
            result = generate_email(product, customer, features_text, tone, stream=True)
            show_result(result, "email", label="📝 开发信", file_name=f"开发信_{product}.txt")
        else:
            with st.spinner("🤖 AI 正在生成..."):
                result = generate_email(product, customer, features_text, tone, stream=False)
            st.session_state.results["email"] = result

# ── 展示已有结果（非流式 or 切回页面） ────────────────
if not generate_clicked and st.session_state.results.get("email"):
    show_result(
        st.session_state.results["email"],
        "email",
        label="📝 开发信",
        file_name=f"开发信_上次结果.txt",
        balloons=False,
    )

# ── Footer ────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 开发信生成</div>', unsafe_allow_html=True)
