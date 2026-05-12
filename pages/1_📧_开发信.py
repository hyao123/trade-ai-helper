"""
pages/1_📧_开发信.py
生成外贸开发信（含邮件主题行），支持流式输出 + 模板保存/加载。
"""
import streamlit as st

from utils.ai_client import generate_email
from utils.templates import (
    delete_template,
    get_template_data,
    get_template_names,
    save_template,
)
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result

st.set_page_config(page_title="开发信生成 | 外贸AI助手", page_icon="📧", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📧 开发信生成</h1>
    <p class="hero-subtitle">AI 撰写高转化率开发信 + 邮件主题行，支持 7 种语言</p>
</div>
""", unsafe_allow_html=True)

# ── 模板加载 ──────────────────────────────────────────
template_names = get_template_names("email")
if template_names:
    with st.expander("📂 我的模板", expanded=False):
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            selected_tpl = st.selectbox("选择模板", ["— 不使用模板 —"] + template_names, key="email_tpl_select")
        with col_t2:
            st.markdown("<br>", unsafe_allow_html=True)
            if selected_tpl != "— 不使用模板 —":
                if st.button("📥 加载", key="email_tpl_load", use_container_width=True):
                    data = get_template_data("email", selected_tpl)
                    if data:
                        st.session_state["email_product_val"]  = data.get("product", "")
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

# 生成 + 保存按钮
col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    generate_clicked = st.button("🚀 生成开发信 + 主题行", type="primary", use_container_width=True)
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

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product or not customer:
        st.warning("⚠️ 请填写产品名称和目标客户")
    elif not features_text.strip():
        st.warning("⚠️ 请填写产品卖点，内容越详细生成效果越好")
    else:
        st.session_state["email_product_val"]  = product
        st.session_state["email_customer_val"] = customer
        st.session_state["email_features_val"] = features_text
        st.session_state.results.pop("email", None)

        if stream_mode:
            result = generate_email(product, customer, features_text, tone, language, stream=True, user_id=get_user_id())
            show_result(result, "email", label="📝 开发信正文", file_name=f"开发信_{product}.txt", show_subject_line=True, history_feature="开发信", history_title=f"{product} → {customer[:20]}")
        else:
            with st.spinner("🤖 AI 正在生成..."):
                result = generate_email(product, customer, features_text, tone, language, stream=False, user_id=get_user_id())
            st.session_state.results["email"] = result
            show_result(result, "email", label="📝 开发信正文", file_name=f"开发信_{product}.txt", balloons=True, show_subject_line=True, history_feature="开发信", history_title=f"{product} → {customer[:20]}")

elif st.session_state.results.get("email"):
    show_result(
        st.session_state.results["email"], "email",
        label="📝 开发信正文（上次结果）",
        file_name=f"开发信_{st.session_state.get('email_product_val', '结果')}.txt",
        balloons=False, show_subject_line=True,
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 开发信生成</div>', unsafe_allow_html=True)
