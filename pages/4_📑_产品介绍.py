"""
pages/4_📑_产品介绍.py
生成多语种产品介绍文案，支持流式输出。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result, get_user_id, show_regenerate_buttons
from utils.ai_client import generate_product_intro

st.set_page_config(page_title="产品介绍 | 外贸AI助手", page_icon="📑", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📑 产品介绍生成</h1>
    <p class="hero-subtitle">一次输入，多语种专业文案同步输出</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 产品特点越具体（如认证、数据、应用场景），文案质量越高。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    product  = st.text_input("产品名称 *", placeholder="例如: Solar LED Street Light",
                              value=st.session_state.get("intro_product_val", ""))
    features = st.text_area(
        "产品特点 *",
        height=160,
        placeholder="每行一条，例如：\n• 200W 高功率，适合大型路段\n• IP67 防水等级\n• 5年质保\n• CE / RoHS 认证\n• 太阳能供电，零电费",
        value=st.session_state.get("intro_features_val", ""),
    )
with col2:
    target    = st.selectbox("目标市场", ["美国", "欧洲", "南美", "东南亚", "中东", "非洲", "全球"])
    languages = st.multiselect(
        "输出语言（可多选）",
        ["英语", "西班牙语", "法语", "德语", "日语"],
        default=["英语"],
    )
    if not languages:
        st.warning("⚠️ 请至少选择一种输出语言，将自动使用英语")
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

generate_clicked = st.button("🚀 生成产品介绍", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("intro_regenerate", None)
if _regen_mode:
    generate_clicked = True
    # Restore saved form values for regeneration
    product = st.session_state.get("intro_product_val", product)
    features = st.session_state.get("intro_features_val", features)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product or not features.strip():
        st.warning("⚠️ 请填写产品名称和产品特点")
    else:
        lang_list = languages if languages else ["英语"]
        st.session_state["intro_product_val"]  = product
        st.session_state["intro_features_val"] = features
        st.session_state.results.pop("intro", None)

        fname = f"{product}_产品介绍.txt"
        if stream_mode:
            result = generate_product_intro(product, features, target, lang_list, stream=True, user_id=get_user_id())
            show_result(result, "intro", label="📝 产品介绍文案", file_name=fname, height=300, history_feature="产品介绍", history_title=product[:25])
        else:
            with st.spinner("🤖 AI 生成中..."):
                result = generate_product_intro(product, features, target, lang_list, stream=False, user_id=get_user_id())
            st.session_state.results["intro"] = result
            show_result(result, "intro", label="📝 产品介绍文案", file_name=fname, height=300, balloons=True, history_feature="产品介绍", history_title=product[:25])
        show_regenerate_buttons("intro", show_style_button=False)

elif st.session_state.results.get("intro"):
    show_result(
        st.session_state.results["intro"],
        "intro",
        label="📝 产品介绍文案（上次结果）",
        file_name="产品介绍.txt",
        height=300,
        balloons=False,
    )
    show_regenerate_buttons("intro", show_style_button=False)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 产品介绍生成</div>', unsafe_allow_html=True)
