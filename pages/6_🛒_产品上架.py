"""
pages/6_🛒_产品上架.py
生成 Amazon / Shopify 产品 Listing 文案，支持流式输出。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, show_result, get_user_id, show_regenerate_buttons
from utils.ai_client import generate_listing

st.set_page_config(page_title="产品上架 | 外贸AI助手", page_icon="🛒", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🛒 产品上架文案</h1>
    <p class="hero-subtitle">一键生成 Amazon / Shopify 产品 Listing，含标题、卖点、描述、搜索词</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 关键词越精准，Listing 的 SEO 效果越好。建议填写 3-5 个核心搜索词。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    product = st.text_input(
        "产品名称 *",
        placeholder="例如: Rechargeable LED Desk Lamp",
        value=st.session_state.get("listing_product_val", ""),
    )
    keywords = st.text_area(
        "核心关键词 *（每行一个或逗号分隔）",
        placeholder="led desk lamp\nrechargeable table light\ntouch control lamp\nUSB reading light",
        height=100,
        value=st.session_state.get("listing_keywords_val", ""),
    )
with col2:
    platform = st.selectbox(
        "目标平台",
        ["Amazon", "Shopify", "Amazon + Shopify"],
        help="选择平台会影响输出格式（如 Amazon 有 Search Terms 限制）",
    )
    category = st.text_input(
        "产品类目（可选）",
        placeholder="例如: Home & Kitchen > Lighting > Desk Lamps",
        value=st.session_state.get("listing_category_val", ""),
    )
    stream_mode = st.toggle("⚡ 流式输出（实时显示）", value=True)

features = st.text_area(
    "产品卖点 / 参数 *",
    placeholder="每行一条，例如：\n• 3000mAh 充电电池，续航 8 小时\n• 3 档色温 + 无极调光\n• USB-C 快充\n• ABS+铝合金材质\n• CE/FCC/RoHS 认证\n• 适合办公/阅读/卧室",
    height=140,
    value=st.session_state.get("listing_features_val", ""),
)

generate_clicked = st.button("🚀 生成 Listing 文案", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("listing_regenerate", None)
if _regen_mode:
    generate_clicked = True
    # Restore saved form values for regeneration
    product = st.session_state.get("listing_product_val", product)
    keywords = st.session_state.get("listing_keywords_val", keywords)
    features = st.session_state.get("listing_features_val", features)
    category = st.session_state.get("listing_category_val", category)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product:
        st.warning("⚠️ 请填写产品名称")
    elif not keywords.strip():
        st.warning("⚠️ 请填写核心关键词，这是 Listing SEO 的基础")
    elif not features.strip():
        st.warning("⚠️ 请填写产品卖点/参数")
    else:
        # 保存表单值
        st.session_state["listing_product_val"]  = product
        st.session_state["listing_keywords_val"] = keywords
        st.session_state["listing_features_val"] = features
        st.session_state["listing_category_val"] = category
        st.session_state.results.pop("listing", None)

        fname = f"Listing_{product[:20]}.txt"
        if stream_mode:
            result = generate_listing(
                product, keywords, features, platform, category,
                stream=True, user_id=get_user_id(),
            )
            show_result(result, "listing", label="📝 Listing 文案", file_name=fname, height=350, history_feature="产品上架", history_title=product[:30])
        else:
            with st.spinner("🤖 AI 正在生成 Listing..."):
                result = generate_listing(
                    product, keywords, features, platform, category,
                    stream=False, user_id=get_user_id(),
                )
            st.session_state.results["listing"] = result
            show_result(result, "listing", label="📝 Listing 文案", file_name=fname, height=350, balloons=True, history_feature="产品上架", history_title=product[:30])
        show_regenerate_buttons("listing", show_style_button=False)

elif st.session_state.results.get("listing"):
    show_result(
        st.session_state.results["listing"],
        "listing",
        label="📝 Listing 文案（上次结果）",
        file_name="Listing.txt",
        height=350,
        balloons=False,
    )
    show_regenerate_buttons("listing", show_style_button=False)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 产品上架文案</div>', unsafe_allow_html=True)
