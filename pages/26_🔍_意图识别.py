"""
pages/26_🔍_意图识别.py
邮件回复意图识别 — 粘贴客户回复，AI 判断意图并给出下一步建议。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_client import recognize_email_intent
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result

st.set_page_config(page_title="意图识别 | 外贸AI助手", page_icon="🔍", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🔍 邮件回复意图识别</h1>
    <p class="hero-subtitle">粘贴客户回复邮件，AI 秒判意图 · 给出优先级 · 建议回复模板</p>
</div>
""", unsafe_allow_html=True)

# ── 快速示例 ──────────────────────────────────────────
with st.expander("📖 支持识别的意图类型", expanded=False):
    intent_map = {
        "感兴趣 ✅": "客户表达兴趣，询问更多信息或报价",
        "婉拒 ❌": "礼貌拒绝或暂时无需求",
        "需要信息 📋": "需要规格、价格、样品、认证等详细资料",
        "价格谈判 💰": "想要议价或调整付款条件",
        "样品请求 📦": "想要订购或收到样品",
        "下单意向 🎯": "有明确购买意向，询问PI/合同",
        "投诉/问题 😟": "提出投诉或问题",
    }
    for intent, desc in intent_map.items():
        st.markdown(f"- **{intent}**：{desc}")

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 粘贴完整的客户回复邮件，AI 将分析意图、情感倾向、紧迫程度，并给出具体的下一步行动建议。</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([3, 2])
with col1:
    email_content = st.text_area(
        "客户回复邮件内容 *",
        height=220,
        placeholder=(
            "粘贴客户的完整回复邮件...\n\n"
            "例如:\nHi Tom,\n\nThank you for your email. "
            "We are interested in your LED street lights.\n"
            "Could you please send us your latest price list and MOQ?\n\nBest regards,\nMike"
        ),
        key="intent_email",
    )
with col2:
    context = st.text_area(
        "背景信息（可选）",
        height=100,
        placeholder="例如：这是第一次回复 / 已发过样品 / 之前报价 $12/pc",
        key="intent_context",
    )
    st.markdown("**快速分析示例：**")
    if st.button("📋 填入示例邮件", key="intent_example", use_container_width=True):
        st.session_state["intent_email"] = (
            "Hi Tom,\n\nThank you for sending us the samples last week. "
            "We have tested them and are quite satisfied with the quality. "
            "However, we feel the price is a bit high compared to our current supplier. "
            "Could you offer a better price if we order 2000 pcs? "
            "Also, what is your lead time for this quantity?\n\n"
            "Best regards,\nMike Johnson\nABC Trading Co."
        )
        st.rerun()

    stream_mode = st.toggle("⚡ 流式输出", value=True, key="intent_stream")

analyze_clicked = st.button("🔍 分析邮件意图", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if analyze_clicked:
    if not email_content.strip():
        st.warning("⚠️ 请粘贴客户回复邮件内容")
    else:
        uid = get_user_id()
        result = recognize_email_intent(
            email_content=email_content,
            context=context,
            stream=stream_mode,
            user_id=uid,
        )
        show_result(
            result,
            result_key="intent_result",
            label="🔍 意图分析报告",
            file_name="intent_analysis.txt",
            height=320,
            show_subject_line=False,
            history_feature="意图识别",
            history_title="邮件意图分析",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 邮件意图识别</div>', unsafe_allow_html=True)
