"""
pages/1_📧_开发信.py
生成外贸开发信（含邮件主题行），支持流式输出。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result, get_user_id
from utils.ai_client import generate_email

st.set_page_config(page_title="开发信生成 | 外贸AI助手", page_icon="📧", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📧 开发信生成</h1>
    <p class="hero-subtitle">AI 撰写高转化率英文开发信 + 邮件主题行，10 秒完成</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 产品卖点建议写 3 条以上，内容越具体，开发信质量越高。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    product  = st.text_input("产品名称 *", placeholder="例如: LED Desk Lamp",
                              value=st.session_state.get("email_product_val", ""))
    customer = st.text_input("目标客户 *", placeholder="例如: John Smith, ABC Lighting Co.",
                              value=st.session_state.get("email_customer_val", ""))
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
    language = st.selectbox(
        "输出语言",
        ["英语", "西班牙语", "法语", "德语", "葡萄牙语", "阿拉伯语", "俄语"],
        help="选择目标市场的语言，AI 会用该语言撰写邮件",
    )
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

features_text = st.text_area(
    "产品卖点 *",
    placeholder="每行一条，例如：\n• 10年工厂经验\n• CE/RoHS/FCC 认证\n• 支持 OEM/ODM\n• 15天快速交货\n• 免费打样",
    height=130,
    value=st.session_state.get("email_features_val", ""),
)

generate_clicked = st.button("🚀 生成开发信 + 主题行", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product or not customer:
        st.warning("⚠️ 请填写产品名称和目标客户")
    elif not features_text.strip():
        st.warning("⚠️ 请填写产品卖点，内容越详细生成效果越好")
    else:
        # 保存表单值，避免生成后重渲染丢失输入
        st.session_state["email_product_val"]  = product
        st.session_state["email_customer_val"] = customer
        st.session_state["email_features_val"] = features_text
        # 清除上次结果，避免新旧结果同时显示
        st.session_state.results.pop("email", None)

        if stream_mode:
            result = generate_email(product, customer, features_text, tone, language, stream=True, user_id=get_user_id())
            show_result(
                result, "email",
                label="📝 开发信正文",
                file_name=f"开发信_{product}.txt",
                show_subject_line=True,
            )
        else:
            with st.spinner("🤖 AI 正在生成..."):
                result = generate_email(product, customer, features_text, tone, language, stream=False, user_id=get_user_id())
            st.session_state.results["email"] = result
            show_result(
                result, "email",
                label="📝 开发信正文",
                file_name=f"开发信_{product}.txt",
                balloons=True,
                show_subject_line=True,
            )

# ── 展示上次结果（切回页面时） ────────────────────────
elif st.session_state.results.get("email"):
    show_result(
        st.session_state.results["email"],
        "email",
        label="📝 开发信正文（上次结果）",
        file_name=f"开发信_{st.session_state.get('email_product_val', '结果')}.txt",
        balloons=False,
        show_subject_line=True,
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 开发信生成</div>', unsafe_allow_html=True)
