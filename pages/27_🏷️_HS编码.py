"""
pages/27_🏷️_HS编码.py
HS 编码查询 — 输入产品描述，AI 建议合适的 HS Code。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_client import lookup_hs_code
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result
from utils.user_prefs import get_pref

st.set_page_config(page_title="HS编码查询 | 外贸AI助手", page_icon="🏷️", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🏷️ HS 编码查询</h1>
    <p class="hero-subtitle">输入产品名称，AI 建议 HS Code · 分析分类依据 · 提示注意事项</p>
</div>
""", unsafe_allow_html=True)

with st.expander("💡 什么是 HS 编码？", expanded=False):
    st.markdown("""
**HS 编码**（Harmonized System Code）是世界海关组织（WCO）制定的国际贸易商品分类体系。

- **6位码**：全球通用（前两位=章、前四位=品目、6位=子目）
- **8位码**：中国出口使用
- **10位码**：中国进口、美国 HTS 编码

**用途：**
- 申报出口/进口报关
- 确认关税税率
- 申请出口退税（中国）
- 确认是否需要出口许可证
    """)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 产品描述越详细，查询结果越准确。建议填写材质、用途、工作原理等。</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    product = st.text_input(
        "产品名称 *",
        value=get_pref("default_product"),
        placeholder="例如: LED Street Light 100W",
        key="hs_product",
    )
    target_country = st.text_input(
        "目标进口国（可选）",
        placeholder="例如: USA, Germany, Saudi Arabia",
        key="hs_country",
    )
with col2:
    description = st.text_area(
        "详细描述（可选，越详细越准确）",
        height=120,
        placeholder=(
            "例如:\n"
            "- 功能: 道路照明\n"
            "- 材质: 铝合金外壳，钢化玻璃\n"
            "- 电源: AC 100-277V, 100W\n"
            "- 认证: CE, RoHS, IP66\n"
            "- 用途: 户外路灯，工业照明"
        ),
        key="hs_description",
    )

# 常用产品快捷按钮
st.markdown("**常用产品快捷查询：**")
qc = st.columns(6)
quick_products = [
    "LED Street Light", "Solar Panel", "Lithium Battery",
    "Electric Vehicle", "Textile Fabric", "Stainless Steel Pipe",
]
for col, qp in zip(qc, quick_products):
    with col:
        if st.button(qp, key=f"hs_quick_{qp}", use_container_width=True):
            st.session_state["hs_product"] = qp
            st.rerun()

lookup_clicked = st.button("🔍 查询 HS 编码", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if lookup_clicked:
    if not product.strip():
        st.warning("⚠️ 请填写产品名称")
    else:
        uid = get_user_id()
        result = lookup_hs_code(
            product=product,
            description=description,
            target_country=target_country,
            stream=True,
            user_id=uid,
        )
        show_result(
            result,
            result_key="hs_result",
            label="🏷️ HS 编码查询结果",
            file_name=f"HS_Code_{product[:20]}.txt",
            height=350,
            show_subject_line=False,
            history_feature="HS编码查询",
            history_title=f"HS: {product[:30]}",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · HS编码查询</div>', unsafe_allow_html=True)
