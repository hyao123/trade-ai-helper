"""
pages/30_🚢_提单解读.py
提单(B/L)解读 — 粘贴提单内容，AI 提取关键字段并解释注意事项。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_client import interpret_bill_of_lading
from utils.ui_helpers import get_user_id, page_setup, show_result

page_setup("提单解读", "🚢", "🚢 提单解读", "粘贴 Bill of Lading 内容，AI 提取关键字段、解释术语、提示风险")

st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 将提单上的所有文字内容粘贴到下方，AI 会自动识别并解读每个字段。</div>',
    unsafe_allow_html=True,
)

bl_content = st.text_area(
    "提单内容 *",
    height=250,
    placeholder=(
        "粘贴提单全文...\n\n"
        "例如:\n"
        "BILL OF LADING\n"
        "B/L No: COSU6123456789\n"
        "Shipper: Shenzhen LED Technology Co., Ltd.\n"
        "Consignee: TO ORDER\n"
        "..."
    ),
)

analyze_clicked = st.button("🚢 解读提单", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if analyze_clicked:
    if not bl_content.strip():
        st.warning("⚠️ 请粘贴提单内容")
    else:
        result = interpret_bill_of_lading(
            bl_content=bl_content,
            stream=True,
            user_id=get_user_id(),
        )
        show_result(
            result,
            result_key="bl_interpretation",
            label="🚢 提单解读报告",
            file_name="bl_interpretation.txt",
            height=400,
            history_feature="提单解读",
            history_title="B/L 解读",
        )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 提单解读</div>', unsafe_allow_html=True)
