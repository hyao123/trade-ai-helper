"""
pages/13_🗣️_谈判话术.py
AI 生成谈判话术：针对不同场景生成开场白、还价建议、备选方案和关键话术。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result, get_user_id, show_regenerate_buttons
from utils.ai_client import generate_negotiation

st.set_page_config(page_title="谈判话术 | 外贸AI助手", page_icon="🗣️", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🗣️ 谈判话术库</h1>
    <p class="hero-subtitle">AI 生成专业谈判话术，应对各类客户要求</p>
</div>
""", unsafe_allow_html=True)

# ── 侧栏输入 ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 谈判参数")
    scenario = st.selectbox(
        "谈判场景 *",
        ["客户砍价", "要求延长账期", "要求降低MOQ", "催货", "要求免费样品", "竞争对手比价"],
        key="nego_scenario",
    )
    product = st.text_input(
        "产品 *",
        placeholder="例如: LED Panel Light 600x600mm",
        value=st.session_state.get("nego_product_val", ""),
        key="nego_product",
    )
    current_offer = st.text_input(
        "当前报价/条件 *",
        placeholder="例如: USD 12.5/pc, MOQ 500pcs, 30% T/T in advance",
        value=st.session_state.get("nego_offer_val", ""),
        key="nego_offer",
    )
    bottom_line = st.text_input(
        "底线 *",
        placeholder="例如: USD 10.0/pc, 最低 MOQ 200pcs",
        value=st.session_state.get("nego_bottom_val", ""),
        key="nego_bottom",
    )
    stream_mode = st.toggle("⚡ 流式输出", value=True, key="nego_stream")

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 填写越具体（如具体报价数字和底线），AI 生成的话术越实用。</div>',
    unsafe_allow_html=True,
)

st.markdown(f"**当前场景:** {scenario}")
if product:
    st.markdown(f"**产品:** {product}")
if current_offer:
    st.markdown(f"**当前报价:** {current_offer}")
if bottom_line:
    st.markdown(f"**底线:** {bottom_line}")

generate_clicked = st.button("🚀 生成谈判话术", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("negotiation_regenerate", None)
if _regen_mode:
    generate_clicked = True
    product = st.session_state.get("nego_product_val", product)
    current_offer = st.session_state.get("nego_offer_val", current_offer)
    bottom_line = st.session_state.get("nego_bottom_val", bottom_line)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product:
        st.warning("⚠️ 请填写产品信息")
    elif not current_offer:
        st.warning("⚠️ 请填写当前报价/条件")
    elif not bottom_line:
        st.warning("⚠️ 请填写底线")
    else:
        st.session_state["nego_product_val"] = product
        st.session_state["nego_offer_val"] = current_offer
        st.session_state["nego_bottom_val"] = bottom_line
        st.session_state.results.pop("negotiation", None)

        fname = f"谈判话术_{scenario}.txt"
        if stream_mode:
            result = generate_negotiation(
                scenario, product, current_offer, bottom_line,
                stream=True, user_id=get_user_id(),
            )
            show_result(
                result, "negotiation",
                label="📝 谈判话术",
                file_name=fname,
                height=350,
                history_feature="谈判话术",
                history_title=f"{scenario} - {product[:20]}",
            )
        else:
            with st.spinner("🤖 AI 正在生成谈判话术..."):
                result = generate_negotiation(
                    scenario, product, current_offer, bottom_line,
                    stream=False, user_id=get_user_id(),
                )
            st.session_state.results["negotiation"] = result
            show_result(
                result, "negotiation",
                label="📝 谈判话术",
                file_name=fname,
                height=350,
                balloons=True,
                history_feature="谈判话术",
                history_title=f"{scenario} - {product[:20]}",
            )
        show_regenerate_buttons("negotiation", show_style_button=False)

elif st.session_state.results.get("negotiation"):
    show_result(
        st.session_state.results["negotiation"],
        "negotiation",
        label="📝 谈判话术（上次结果）",
        file_name="谈判话术.txt",
        height=350,
        balloons=False,
    )
    show_regenerate_buttons("negotiation", show_style_button=False)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 谈判话术库</div>', unsafe_allow_html=True)
