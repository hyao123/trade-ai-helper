"""
pages/8_💬_社媒文案.py
生成 LinkedIn / Instagram / Facebook 社媒营销文案，支持流式输出。
"""
import streamlit as st

from utils.ai_client import generate_social_post
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result

st.set_page_config(page_title="社媒文案 | 外贸AI助手", page_icon="💬", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">💬 社媒文案生成</h1>
    <p class="hero-subtitle">一键生成 LinkedIn / Instagram / Facebook 营销文案</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 社媒文案核心：产品 + 痛点 + 场景。填写越具体，文案转化率越高。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    product = st.text_input(
        "产品名称 *",
        placeholder="例如: Portable Solar LED Camping Light",
        value=st.session_state.get("social_product_val", ""),
    )
    features = st.text_area(
        "产品卖点 / 核心优势 *",
        height=130,
        placeholder="每行一条，例如：\n• 太阳能充电，户外无忧\n• IP65 防水\n• 3档亮度调节\n• 折叠设计，便携\n• 适合露营/徒步/钓鱼",
        value=st.session_state.get("social_features_val", ""),
    )
with col2:
    platform = st.selectbox(
        "输出平台",
        ["All Platforms", "LinkedIn", "Instagram", "Facebook Ad"],
        help="选择 All Platforms 会同时生成3个平台的文案",
    )
    audience = st.text_input(
        "目标受众（可选）",
        placeholder="例如: 户外运动爱好者 / 北美25-45岁男性",
        value=st.session_state.get("social_audience_val", ""),
    )
    promo = st.text_input(
        "促销活动（可选）",
        placeholder="例如: 新品上市8折 / 买2送1 / Free shipping",
        value=st.session_state.get("social_promo_val", ""),
    )
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

generate_clicked = st.button("🚀 生成社媒文案", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product:
        st.warning("⚠️ 请填写产品名称")
    elif not features.strip():
        st.warning("⚠️ 请填写产品卖点")
    else:
        st.session_state["social_product_val"]  = product
        st.session_state["social_features_val"] = features
        st.session_state["social_audience_val"] = audience
        st.session_state["social_promo_val"]    = promo
        st.session_state.results.pop("social", None)

        fname = f"社媒文案_{product[:15]}.txt"
        if stream_mode:
            result = generate_social_post(
                product, features, platform, audience, promo,
                stream=True, user_id=get_user_id(),
            )
            show_result(result, "social", label="📝 社媒文案", file_name=fname, height=350, history_feature="社媒文案", history_title=product[:25])
        else:
            with st.spinner("🤖 AI 正在生成文案..."):
                result = generate_social_post(
                    product, features, platform, audience, promo,
                    stream=False, user_id=get_user_id(),
                )
            st.session_state.results["social"] = result
            show_result(result, "social", label="📝 社媒文案", file_name=fname, height=350, balloons=True, history_feature="社媒文案", history_title=product[:25])

elif st.session_state.results.get("social"):
    show_result(
        st.session_state.results["social"],
        "social",
        label="📝 社媒文案（上次结果）",
        file_name="社媒文案.txt",
        height=350,
        balloons=False,
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 社媒文案生成</div>', unsafe_allow_html=True)
