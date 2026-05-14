"""
pages/16_😟_投诉处理.py
AI 生成客诉回复邮件：根据投诉类型和严重程度生成专业回复。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result, get_user_id, show_regenerate_buttons
from utils.ai_client import generate_complaint_response

st.set_page_config(page_title="投诉处理 | 外贸AI助手", page_icon="😟", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">😟 投诉处理邮件</h1>
    <p class="hero-subtitle">AI 生成专业客诉回复，化解矛盾维护关系</p>
</div>
""", unsafe_allow_html=True)

# ── 侧栏输入 ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 投诉参数")
    complaint_type = st.selectbox(
        "投诉类型 *",
        ["质量问题", "交期延误", "数量短缺", "包装破损", "规格不符"],
        key="complaint_type_select",
    )
    severity = st.selectbox(
        "严重程度 *",
        ["轻微", "中等", "严重"],
        key="complaint_severity",
    )
    relationship = st.selectbox(
        "客户关系 *",
        ["新客户", "老客户", "大客户"],
        key="complaint_relationship",
    )
    proposed_solution = st.selectbox(
        "拟定解决方案 *",
        ["换货", "补发", "折扣补偿", "退款"],
        key="complaint_solution",
    )
    stream_mode = st.toggle("⚡ 流式输出", value=True, key="complaint_stream")

# ── 主内容区 ──────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 粘贴客户的投诉原文可让 AI 生成更有针对性的回复。不填则生成通用模板。</div>',
    unsafe_allow_html=True,
)

st.markdown(f"**投诉类型:** {complaint_type}  |  **严重程度:** {severity}  |  **关系:** {relationship}  |  **方案:** {proposed_solution}")

customer_complaint = st.text_area(
    "客户投诉原文（可选）",
    height=180,
    placeholder="在此粘贴客户的投诉邮件内容...\n\n例如:\nDear supplier,\nWe received the goods yesterday but found that 20% of the items have scratches on the surface...",
    value=st.session_state.get("complaint_content_val", ""),
    key="complaint_content_input",
)

generate_clicked = st.button("🚀 生成投诉回复", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("complaint_regenerate", None)
if _regen_mode:
    generate_clicked = True
    customer_complaint = st.session_state.get("complaint_content_val", customer_complaint)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    st.session_state["complaint_content_val"] = customer_complaint
    st.session_state.results.pop("complaint", None)

    fname = f"投诉回复_{complaint_type}.txt"
    if stream_mode:
        result = generate_complaint_response(
            complaint_type, severity, relationship, proposed_solution,
            customer_complaint=customer_complaint,
            stream=True, user_id=get_user_id(),
        )
        show_result(
            result, "complaint",
            label="📝 投诉回复邮件",
            file_name=fname,
            height=320,
            show_subject_line=True,
            history_feature="投诉处理",
            history_title=f"{complaint_type} - {severity}",
        )
    else:
        with st.spinner("🤖 AI 正在生成投诉回复..."):
            result = generate_complaint_response(
                complaint_type, severity, relationship, proposed_solution,
                customer_complaint=customer_complaint,
                stream=False, user_id=get_user_id(),
            )
        st.session_state.results["complaint"] = result
        show_result(
            result, "complaint",
            label="📝 投诉回复邮件",
            file_name=fname,
            height=320,
            balloons=True,
            show_subject_line=True,
            history_feature="投诉处理",
            history_title=f"{complaint_type} - {severity}",
        )
    show_regenerate_buttons("complaint", show_style_button=False)

elif st.session_state.results.get("complaint"):
    show_result(
        st.session_state.results["complaint"],
        "complaint",
        label="📝 投诉回复邮件（上次结果）",
        file_name="投诉回复.txt",
        height=320,
        balloons=False,
        show_subject_line=True,
    )
    show_regenerate_buttons("complaint", show_style_button=False)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 投诉处理邮件</div>', unsafe_allow_html=True)
