"""
pages/14_🎄_节日问候.py
AI 生成节日祝福邮件：根据节日和客户关系生成文化得体的问候邮件。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result, get_user_id, show_regenerate_buttons
from utils.ai_client import generate_holiday_greeting

st.set_page_config(page_title="节日问候 | 外贸AI助手", page_icon="🎄", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🎄 节日问候邮件</h1>
    <p class="hero-subtitle">AI 生成文化得体的节日祝福邮件，维护客户关系</p>
</div>
""", unsafe_allow_html=True)

# ── 侧栏输入 ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 节日参数")
    holiday = st.selectbox(
        "节日 *",
        ["Christmas", "New Year", "Eid", "Diwali", "Chinese New Year",
         "Thanksgiving", "Easter", "Ramadan"],
        key="holiday_select",
    )
    customer_name = st.text_input(
        "客户姓名 *",
        placeholder="例如: John Smith",
        value=st.session_state.get("holiday_customer_val", ""),
        key="holiday_customer",
    )
    company = st.text_input(
        "客户公司 *",
        placeholder="例如: ABC Trading Co.",
        value=st.session_state.get("holiday_company_val", ""),
        key="holiday_company",
    )
    relationship_level = st.selectbox(
        "客户关系",
        ["新客户", "老客户", "VIP"],
        key="holiday_relationship",
    )
    product_mention = st.text_input(
        "顺带提及产品（可选）",
        placeholder="例如: our new LED series launching in Q1",
        value=st.session_state.get("holiday_product_val", ""),
        key="holiday_product",
    )
    stream_mode = st.toggle("⚡ 流式输出", value=True, key="holiday_stream")

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 节日问候邮件重在真诚。AI 会根据节日特点和客户关系自动调整语气和内容。</div>',
    unsafe_allow_html=True,
)

st.markdown(f"**节日:** {holiday}  |  **关系:** {relationship_level}")
if customer_name:
    st.markdown(f"**客户:** {customer_name} ({company})")

generate_clicked = st.button("🚀 生成节日问候邮件", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("holiday_regenerate", None)
if _regen_mode:
    generate_clicked = True
    customer_name = st.session_state.get("holiday_customer_val", customer_name)
    company = st.session_state.get("holiday_company_val", company)
    product_mention = st.session_state.get("holiday_product_val", product_mention)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not customer_name:
        st.warning("⚠️ 请填写客户姓名")
    elif not company:
        st.warning("⚠️ 请填写客户公司")
    else:
        st.session_state["holiday_customer_val"] = customer_name
        st.session_state["holiday_company_val"] = company
        st.session_state["holiday_product_val"] = product_mention
        st.session_state.results.pop("holiday", None)

        fname = f"节日问候_{holiday}_{customer_name[:10]}.txt"
        if stream_mode:
            result = generate_holiday_greeting(
                holiday, customer_name, company, relationship_level,
                product_mention=product_mention,
                stream=True, user_id=get_user_id(),
            )
            show_result(
                result, "holiday",
                label="📝 节日问候邮件",
                file_name=fname,
                height=280,
                show_subject_line=True,
                history_feature="节日问候",
                history_title=f"{holiday} - {customer_name[:15]}",
            )
        else:
            with st.spinner("🤖 AI 正在生成节日问候..."):
                result = generate_holiday_greeting(
                    holiday, customer_name, company, relationship_level,
                    product_mention=product_mention,
                    stream=False, user_id=get_user_id(),
                )
            st.session_state.results["holiday"] = result
            show_result(
                result, "holiday",
                label="📝 节日问候邮件",
                file_name=fname,
                height=280,
                balloons=True,
                show_subject_line=True,
                history_feature="节日问候",
                history_title=f"{holiday} - {customer_name[:15]}",
            )
        show_regenerate_buttons("holiday", show_style_button=False)

elif st.session_state.results.get("holiday"):
    show_result(
        st.session_state.results["holiday"],
        "holiday",
        label="📝 节日问候邮件（上次结果）",
        file_name="节日问候.txt",
        height=280,
        balloons=False,
        show_subject_line=True,
    )
    show_regenerate_buttons("holiday", show_style_button=False)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 节日问候邮件</div>', unsafe_allow_html=True)
