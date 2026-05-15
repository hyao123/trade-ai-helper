"""
pages/5_📬_跟进邮件.py
根据跟进阶段生成专业英文跟进邮件，支持流式输出。
"""
import streamlit as st

from config.prompts import FOLLOWUP_STAGES
from utils.ai_client import generate_followup
from utils.ui_helpers import (
    check_auth,
    get_user_id,
    inject_css,
    show_regenerate_buttons,
    show_result,
)

st.set_page_config(page_title="跟进邮件 | 外贸AI助手", page_icon="📬", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📬 跟进邮件生成</h1>
    <p class="hero-subtitle">根据跟进阶段智能生成专业英文跟进邮件，不再烦恼怎么开口</p>
</div>
""", unsafe_allow_html=True)

# ── 阶段说明 ──────────────────────────────────────────
with st.expander("📖 各跟进阶段说明", expanded=False):
    for stage, desc in FOLLOWUP_STAGES.items():
        st.markdown(f"- **{stage}**：{desc}")

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 选择正确的跟进阶段是关键，不同阶段语气和内容差异很大。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    customer = st.text_input(
        "客户姓名 *",
        placeholder="例如: John Smith / ABC Trading Co.",
        value=st.session_state.get("followup_customer_val", ""),
    )
    product = st.text_input(
        "产品名称（可选）",
        placeholder="例如: LED Street Light，留空则不提及产品",
        value=st.session_state.get("followup_product_val", ""),
    )
with col2:
    stage = st.selectbox(
        "跟进阶段 *",
        list(FOLLOWUP_STAGES.keys()),
        help="选择当前与该客户所处的阶段",
    )
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

st.info(f"**当前阶段说明：** {FOLLOWUP_STAGES.get(stage, '')}")

generate_clicked = st.button("🚀 生成跟进邮件", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("followup_regenerate", None)
if _regen_mode:
    generate_clicked = True
    # Restore saved form values for regeneration
    customer = st.session_state.get("followup_customer_val", customer)
    product = st.session_state.get("followup_product_val", product)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not customer.strip():
        st.warning("⚠️ 请填写客户姓名或公司名")
    else:
        st.session_state["followup_customer_val"] = customer
        st.session_state["followup_product_val"]  = product
        st.session_state.results.pop("followup", None)

        fname = f"跟进邮件_{customer}_{stage}.txt"
        if stream_mode:
            result = generate_followup(customer, stage, product, stream=True, user_id=get_user_id())
            show_result(result, "followup", label="📝 跟进邮件", file_name=fname, history_feature="跟进邮件", history_title=f"{customer[:15]} · {stage}")
        else:
            with st.spinner("🤖 AI 正在生成..."):
                result = generate_followup(customer, stage, product, stream=False, user_id=get_user_id())
            st.session_state.results["followup"] = result
            show_result(result, "followup", label="📝 跟进邮件", file_name=fname, balloons=True, history_feature="跟进邮件", history_title=f"{customer[:15]} · {stage}")
        show_regenerate_buttons("followup", show_style_button=False)

elif st.session_state.results.get("followup"):
    show_result(
        st.session_state.results["followup"],
        "followup",
        label="📝 跟进邮件（上次结果）",
        file_name="跟进邮件.txt",
        balloons=False,
    )
    show_regenerate_buttons("followup", show_style_button=False)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 跟进邮件生成</div>', unsafe_allow_html=True)
