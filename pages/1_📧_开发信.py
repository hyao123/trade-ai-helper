"""
pages/1_📧_开发信.py
生成外贸开发信（含邮件主题行），支持流式输出 + 模板保存/加载 + 多轮对话优化。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_client import generate_email
from utils.conversation import Conversation, stream_with_context
from utils.email_service import is_email_configured, send_ai_generated_email
from utils.templates import (
    delete_template,
    get_template_data,
    get_template_names,
    save_template,
)
from utils.ui_helpers import (
    check_auth,
    extract_subject,
    get_user_id,
    inject_css,
    show_regenerate_buttons,
    show_result,
)
from utils.user_prefs import get_pref

st.set_page_config(page_title="开发信生成 | 外贸AI助手", page_icon="📧", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📧 开发信生成</h1>
    <p class="hero-subtitle">AI 撰写高转化率开发信 + 邮件主题行 · 支持 7 种语言 · 多轮对话优化</p>
</div>
""", unsafe_allow_html=True)

# ── 模板加载 ──────────────────────────────────────────
template_names = get_template_names("email")
if template_names:
    with st.expander("📂 我的模板", expanded=False):
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            selected_tpl = st.selectbox(
                "选择模板", ["— 不使用模板 —"] + template_names, key="email_tpl_select"
            )
        with col_t2:
            st.markdown("<br>", unsafe_allow_html=True)
            if selected_tpl != "— 不使用模板 —":
                if st.button("📥 加载", key="email_tpl_load", use_container_width=True):
                    data = get_template_data("email", selected_tpl)
                    if data:
                        st.session_state["email_product_val"] = data.get("product", "")
                        st.session_state["email_customer_val"] = data.get("customer", "")
                        st.session_state["email_features_val"] = data.get("features", "")
                        st.success(f"✅ 已加载模板：{selected_tpl}")
                        st.rerun()
                if st.button("🗑️ 删除", key="email_tpl_del", use_container_width=True):
                    delete_template("email", selected_tpl)
                    st.success(f"已删除模板：{selected_tpl}")
                    st.rerun()

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 产品卖点建议写 3 条以上，内容越具体，开发信质量越高。'
    "常用信息在「<b>⚙️ AI偏好</b>」页面设置后将自动预填。</div>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    product = st.text_input(
        "产品名称 *",
        placeholder="例如: LED Desk Lamp",
        value=st.session_state.get("email_product_val", get_pref("default_product")),
    )
    customer = st.text_input(
        "目标客户 *",
        placeholder="例如: John Smith, ABC Lighting Co.",
        value=st.session_state.get("email_customer_val", ""),
    )
with col2:
    _tone_options = ["简洁专业 (50-80词)", "正式商务 (100-150词)", "亲切友好 (80-100词)"]
    _tone_map = {
        "简洁专业 (50-80词)": "简洁专业",
        "正式商务 (100-150词)": "正式商务",
        "亲切友好 (80-100词)": "亲切友好",
    }
    _default_tone = get_pref("default_tone")
    _default_tone_label = next(
        (k for k, v in _tone_map.items() if v == _default_tone),
        _tone_options[0],
    )
    tone_label = st.selectbox(
        "邮件风格",
        _tone_options,
        index=_tone_options.index(_default_tone_label),
    )
    tone = _tone_map[tone_label]

    _lang_options = ["英语", "西班牙语", "法语", "德语", "葡萄牙语", "阿拉伯语", "俄语"]
    _default_lang = get_pref("default_language")
    language = st.selectbox(
        "输出语言",
        _lang_options,
        index=_lang_options.index(_default_lang) if _default_lang in _lang_options else 0,
        help="选择目标市场的语言，AI 会用该语言撰写邮件",
    )
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

features_text = st.text_area(
    "产品卖点 *",
    placeholder="每行一条，例如：\n• 10年工厂经验\n• CE/RoHS/FCC 认证\n• 支持 OEM/ODM\n• 15天快速交货\n• 免费打样",
    height=130,
    value=st.session_state.get("email_features_val", ""),
)

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    generate_clicked = st.button(
        "🚀 生成开发信 + 主题行", type="primary", use_container_width=True
    )
with col_btn2:
    save_clicked = st.button("💾 保存为模板", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── 保存模板逻辑 ──────────────────────────────────────
if save_clicked:
    if not product:
        st.warning("⚠️ 请先填写产品名称")
    else:
        tpl_name = f"{product} - {customer[:15]}" if customer else product
        save_template("email", tpl_name, {
            "product": product,
            "customer": customer,
            "features": features_text,
        })
        st.success(f"✅ 模板已保存：{tpl_name}")

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("email_regenerate", None)
if _regen_mode:
    generate_clicked = True
    if _regen_mode == "style":
        _tones = ["简洁专业", "正式商务", "亲切友好"]
        _current = st.session_state.get("email_last_tone", tone)
        _idx = (_tones.index(_current) + 1) % len(_tones) if _current in _tones else 0
        tone = _tones[_idx]
    product = st.session_state.get("email_product_val", product)
    customer = st.session_state.get("email_customer_val", customer)
    features_text = st.session_state.get("email_features_val", features_text)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product or not customer:
        st.warning("⚠️ 请填写产品名称和目标客户")
    elif not features_text.strip():
        st.warning("⚠️ 请填写产品卖点，内容越详细生成效果越好")
    else:
        st.session_state["email_product_val"] = product
        st.session_state["email_customer_val"] = customer
        st.session_state["email_features_val"] = features_text
        st.session_state["email_last_tone"] = tone
        st.session_state.results.pop("email", None)
        # Reset conversation on new generation
        if "_conv_email_conv" in st.session_state:
            del st.session_state["_conv_email_conv"]

        if stream_mode:
            result = generate_email(
                product, customer, features_text, tone, language,
                stream=True, user_id=get_user_id(),
            )
            show_result(
                result, "email",
                label="📝 开发信正文",
                file_name=f"开发信_{product}.txt",
                show_subject_line=True,
                history_feature="开发信",
                history_title=f"{product} → {customer[:20]}",
            )
        else:
            with st.spinner("🤖 AI 正在生成..."):
                result = generate_email(
                    product, customer, features_text, tone, language,
                    stream=False, user_id=get_user_id(),
                )
            st.session_state.results["email"] = result
            show_result(
                result, "email",
                label="📝 开发信正文",
                file_name=f"开发信_{product}.txt",
                balloons=True,
                show_subject_line=True,
                history_feature="开发信",
                history_title=f"{product} → {customer[:20]}",
            )

        # Initialize conversation with the generated result
        full_text = st.session_state.results.get("email", "")
        if full_text and not full_text.startswith("⚠️"):
            conv = Conversation("email_conv")
            conv.clear()
            conv.add_user(
                f"Generate a {tone} cold email in {language} for product: {product}, "
                f"customer: {customer}, features: {features_text}"
            )
            conv.add_assistant(full_text)

        show_regenerate_buttons("email")

# ── 邮件直发（SMTP）────────────────────────────────────
last_email_result = st.session_state.results.get("email", "")
if last_email_result and not last_email_result.startswith("⚠️"):
    st.markdown("---")
    st.markdown("### 📨 直接发送邮件")
    if not is_email_configured():
        st.caption("💡 在 Secrets 中配置 SMTP_HOST / SMTP_USER / SMTP_PASSWORD 等参数后可直接发送邮件。")
    else:
        with st.expander("📨 发送此邮件给客户", expanded=False):
            from utils.ui_helpers import extract_subject
            subject_val, body_val = extract_subject(last_email_result)
            send_to = st.text_input(
                "收件人邮箱 *",
                key="direct_send_to",
                placeholder="customer@company.com",
            )
            send_subject = st.text_input(
                "邮件主题", value=subject_val, key="direct_send_subject"
            )
            send_body = st.text_area(
                "邮件正文", value=body_val, height=200, key="direct_send_body"
            )
            send_name = st.text_input(
                "发件人姓名", value=get_pref("contact_name"), key="direct_send_name"
            )
            if st.button("📨 发送", type="primary", use_container_width=True, key="direct_send_btn"):
                if not send_to.strip():
                    st.warning("⚠️ 请填写收件人邮箱")
                elif not send_subject.strip():
                    st.warning("⚠️ 请填写邮件主题")
                else:
                    with st.spinner("正在发送邮件..."):
                        ok, msg = send_ai_generated_email(
                            to_email=send_to.strip(),
                            subject=send_subject.strip(),
                            body=send_body.strip(),
                            from_name=send_name.strip(),
                        )
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ 发送失败: {msg}")

elif st.session_state.results.get("email"):
    show_result(
        st.session_state.results["email"],
        "email",
        label="📝 开发信正文（上次结果）",
        file_name=f"开发信_{st.session_state.get('email_product_val', '结果')}.txt",
        balloons=False,
        show_subject_line=True,
    )
    show_regenerate_buttons("email")

# ── 多轮对话优化区 ────────────────────────────────────
conv = Conversation("email_conv")
if not conv.is_empty():
    st.markdown("---")
    st.markdown("### 💬 继续优化（多轮对话）")
    st.markdown(
        '<div class="tip-card">💡 对生成结果不满意？直接告诉 AI 如何修改，支持多轮连续对话。</div>',
        unsafe_allow_html=True,
    )

    # Show conversation history (last few turns)
    if conv.turn_count() > 1:
        with st.expander(f"📜 对话历史（{conv.turn_count()} 轮）", expanded=False):
            conv.render_history(max_display=6)

    # Quick-fix buttons
    st.markdown("**快速指令：**")
    qc1, qc2, qc3, qc4 = st.columns(4)
    quick_followup = None
    with qc1:
        if st.button("✂️ 缩短一半", key="qf_shorter", use_container_width=True):
            quick_followup = "Please make the email significantly shorter — cut it roughly in half while keeping the core message."
    with qc2:
        if st.button("🔥 更有说服力", key="qf_persuasive", use_container_width=True):
            quick_followup = "Rewrite to be more persuasive and compelling. Add a stronger value proposition and urgency."
    with qc3:
        if st.button("😊 更友好亲切", key="qf_friendly", use_container_width=True):
            quick_followup = "Rewrite with a warmer, more personal and friendly tone while keeping professionalism."
    with qc4:
        if st.button("📊 加入数据/证明", key="qf_data", use_container_width=True):
            quick_followup = "Add specific numbers, statistics, or social proof to make the email more credible."

    # Free-text follow-up
    followup_text = st.text_input(
        "或自定义修改指令",
        placeholder="例如：换一个更有悬念的开头 / 主题行改短到40字以内 / 加上我们的ISO认证",
        key="email_followup_input",
    )
    followup_btn = st.button("🔄 应用修改", type="primary", use_container_width=True, key="email_followup_btn")

    effective_followup = quick_followup or (followup_text.strip() if followup_btn and followup_text.strip() else None)

    if effective_followup:
        result_gen = stream_with_context(conv, effective_followup, user_id=get_user_id())
        show_result(
            result_gen,
            result_key=f"email_followup_{conv.turn_count()}",
            label="📝 优化后的开发信",
            file_name=f"开发信_优化_{st.session_state.get('email_product_val', '')}.txt",
            show_subject_line=True,
            history_feature="开发信",
            history_title=f"[优化] {st.session_state.get('email_product_val', '')}",
        )
        # Save latest to main result slot
        latest = st.session_state.results.get(f"email_followup_{conv.turn_count()}", "")
        if latest:
            conv.add_assistant(latest)
            st.session_state.results["email"] = latest

    if st.button("🗑️ 清除对话历史，重新开始", key="email_clear_conv"):
        conv.clear()
        st.session_state.results.pop("email", None)
        st.rerun()

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 开发信生成</div>', unsafe_allow_html=True)
