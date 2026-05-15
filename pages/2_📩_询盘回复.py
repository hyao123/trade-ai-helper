"""
pages/2_📩_询盘回复.py
粘贴客户询盘，AI 生成专业英文回复草稿，支持流式输出 + 多轮对话优化。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_client import reply_inquiry
from utils.conversation import Conversation, stream_with_context
from utils.ui_helpers import (
    check_auth,
    get_user_id,
    inject_css,
    show_regenerate_buttons,
    show_result,
)
from utils.user_prefs import get_pref

st.set_page_config(page_title="询盘回复 | 外贸AI助手", page_icon="📩", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📩 询盘回复</h1>
    <p class="hero-subtitle">粘贴客户询盘，AI 生成专业回复草稿 · 支持多轮对话优化</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 粘贴完整询盘内容，AI 会逐条回答客户问题并提供报价区间。'
    "签名信息在「<b>⚙️ AI偏好</b>」页面设置后将自动预填。</div>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns([3, 2])
with col1:
    inquiry = st.text_area(
        "客户询盘内容 *",
        height=200,
        placeholder="粘贴客户发来的完整邮件内容...\n\nHi, I'm interested in your LED desk lamps...",
        value=st.session_state.get("inquiry_text_val", ""),
    )
with col2:
    customer_name = st.text_input(
        "客户姓名（可选）",
        placeholder="例如: Mike Johnson",
        value=st.session_state.get("inquiry_customer_val", ""),
    )
    your_name = st.text_input(
        "你的姓名（可选）",
        placeholder="签名用，例如: Tom",
        value=st.session_state.get("inquiry_your_name_val", get_pref("contact_name")),
    )
    company_name = st.text_input(
        "公司名称（可选）",
        placeholder="您的公司名称，用于签名",
        value=st.session_state.get("inquiry_company_val", get_pref("company_name")),
    )
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

generate_clicked = st.button("🚀 生成回复", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("inquiry_regenerate", None)
if _regen_mode:
    generate_clicked = True
    inquiry = st.session_state.get("inquiry_text_val", inquiry)
    customer_name = st.session_state.get("inquiry_customer_val", customer_name)
    your_name = st.session_state.get("inquiry_your_name_val", your_name)
    company_name = st.session_state.get("inquiry_company_val", company_name)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not inquiry.strip():
        st.warning("⚠️ 请粘贴客户询盘内容")
    else:
        st.session_state["inquiry_text_val"] = inquiry
        st.session_state["inquiry_customer_val"] = customer_name
        st.session_state["inquiry_your_name_val"] = your_name
        st.session_state["inquiry_company_val"] = company_name
        st.session_state.results.pop("inquiry", None)
        # Reset conversation
        if "_conv_inquiry_conv" in st.session_state:
            del st.session_state["_conv_inquiry_conv"]

        fname = f"询盘回复_{customer_name or '客户'}.txt"
        if stream_mode:
            result = reply_inquiry(
                inquiry, customer_name, your_name, company_name,
                stream=True, user_id=get_user_id(),
            )
            show_result(
                result, "inquiry",
                label="📝 回复草稿",
                file_name=fname,
                history_feature="询盘回复",
                history_title=f"回复 {customer_name or '客户'}",
            )
        else:
            with st.spinner("🤖 AI 正在生成..."):
                result = reply_inquiry(
                    inquiry, customer_name, your_name, company_name,
                    stream=False, user_id=get_user_id(),
                )
            st.session_state.results["inquiry"] = result
            show_result(
                result, "inquiry",
                label="📝 回复草稿",
                file_name=fname,
                balloons=True,
                history_feature="询盘回复",
                history_title=f"回复 {customer_name or '客户'}",
            )

        # Seed conversation
        full_text = st.session_state.results.get("inquiry", "")
        if full_text and not full_text.startswith("⚠️"):
            conv = Conversation("inquiry_conv")
            conv.clear()
            conv.add_user(
                f"Reply to this customer inquiry from {customer_name or 'customer'}:\n{inquiry}"
            )
            conv.add_assistant(full_text)

        show_regenerate_buttons("inquiry", show_style_button=False)

elif st.session_state.results.get("inquiry"):
    show_result(
        st.session_state.results["inquiry"],
        "inquiry",
        label="📝 回复草稿（上次结果）",
        file_name="询盘回复.txt",
        balloons=False,
    )
    show_regenerate_buttons("inquiry", show_style_button=False)

# ── 多轮对话优化区 ────────────────────────────────────
conv = Conversation("inquiry_conv")
if not conv.is_empty():
    st.markdown("---")
    st.markdown("### 💬 继续优化（多轮对话）")
    st.markdown(
        '<div class="tip-card">💡 可以让 AI 补充价格、修改语气、添加技术参数等。</div>',
        unsafe_allow_html=True,
    )

    if conv.turn_count() > 1:
        with st.expander(f"📜 对话历史（{conv.turn_count()} 轮）", expanded=False):
            conv.render_history(max_display=6)

    # Quick-fix buttons
    qc1, qc2, qc3, qc4 = st.columns(4)
    quick_followup = None
    with qc1:
        if st.button("💰 加入报价区间", key="iq_price", use_container_width=True):
            quick_followup = "Add a specific price range or pricing structure to the reply. Be concrete with numbers."
    with qc2:
        if st.button("📋 逐条更详细", key="iq_detail", use_container_width=True):
            quick_followup = "Address each question from the customer's inquiry more thoroughly with specific details."
    with qc3:
        if st.button("✂️ 简化版本", key="iq_shorter", use_container_width=True):
            quick_followup = "Rewrite as a more concise reply. Cut it to the essential points only."
    with qc4:
        if st.button("🤝 加强合作邀约", key="iq_cta", use_container_width=True):
            quick_followup = "Strengthen the call-to-action. Invite the customer to schedule a video call or request samples."

    followup_text = st.text_input(
        "或自定义修改指令",
        placeholder="例如：把回复改成西班牙语 / 加上我们的MOQ是500件 / 语气更专业一些",
        key="inquiry_followup_input",
    )
    followup_btn = st.button(
        "🔄 应用修改", type="primary", use_container_width=True, key="inquiry_followup_btn"
    )

    effective_followup = quick_followup or (
        followup_text.strip() if followup_btn and followup_text.strip() else None
    )

    if effective_followup:
        result_gen = stream_with_context(conv, effective_followup, user_id=get_user_id())
        show_result(
            result_gen,
            result_key=f"inquiry_followup_{conv.turn_count()}",
            label="📝 优化后的回复",
            file_name=f"询盘回复_优化_{customer_name or '客户'}.txt",
            history_feature="询盘回复",
            history_title=f"[优化] 回复 {customer_name or '客户'}",
        )
        latest = st.session_state.results.get(f"inquiry_followup_{conv.turn_count()}", "")
        if latest:
            conv.add_assistant(latest)
            st.session_state.results["inquiry"] = latest

    if st.button("🗑️ 清除对话历史，重新开始", key="inquiry_clear_conv"):
        conv.clear()
        st.session_state.results.pop("inquiry", None)
        st.rerun()

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 询盘回复</div>', unsafe_allow_html=True)
