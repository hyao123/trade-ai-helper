"""
pages/18_📦_装箱计算器.py
集装箱装箱计算器：输入外箱尺寸和重量，自动计算各型号集装箱的装载方案。
"""
from __future__ import annotations

import streamlit as st

from utils.container_calc import (
    CONTAINER_SPECS,
    CartonSpec,
    calculate_all_containers,
    recommend_container,
)
from utils.ui_helpers import check_auth, inject_css

st.set_page_config(page_title="装箱计算器 | 外贸AI助手", page_icon="📦", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📦 装箱计算器</h1>
    <p class="hero-subtitle">输入外箱尺寸与重量，一键计算 20GP / 40GP / 40HQ 装载方案</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="form-title">📐 外箱参数</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    length = st.number_input("长度 (mm)", min_value=1, value=600, step=10)
    gross_weight = st.number_input("单箱毛重 (kg)", min_value=0.1, value=15.0, step=0.5, format="%.1f")
with col2:
    width = st.number_input("宽度 (mm)", min_value=1, value=400, step=10)
    qty_per_carton = st.number_input("每箱装量 (pcs)", min_value=1, value=24, step=1)
with col3:
    height = st.number_input("高度 (mm)", min_value=1, value=350, step=10)
    max_stack = st.number_input("最大堆叠层数", min_value=1, value=8, step=1)

stackable = st.checkbox("允许堆叠", value=True)
target_qty = st.number_input("目标发货箱数（可选，用于柜型推荐）", min_value=0, value=0, step=50,
                             help="填写目标箱数，系统会推荐最优柜型")

st.markdown('<div class="tip-card">💡 尺寸单位为毫米(mm)，重量为千克(kg)。堆叠层数限制可防止底层纸箱压坏。</div>', unsafe_allow_html=True)

calculate_clicked = st.button("🚀 计算装箱方案", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 计算逻辑 ──────────────────────────────────────────
if calculate_clicked:
    carton = CartonSpec(
        length_mm=length,
        width_mm=width,
        height_mm=height,
        gross_weight_kg=gross_weight,
        quantity_per_carton=qty_per_carton,
        stackable=stackable,
        max_stack_layers=max_stack,
    )

    # 计算所有柜型
    results = calculate_all_containers(carton)

    if not results:
        st.error("❌ 外箱尺寸过大，无法装入任何标准集装箱。请检查尺寸参数。")
    else:
        st.markdown(
            '<div class="success-box">'
            '<div style="font-size:1.5rem;">✅</div>'
            '<div class="success-title">装箱方案计算完成！</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # 概览指标
        best = results[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏆 最大装载柜型", best.container_type)
        c2.metric("📦 最大装箱数", f"{best.total_cartons} 箱")
        c3.metric("📊 体积利用率", f"{best.volume_utilization_pct}%")
        c4.metric("⚖️ 重量利用率", f"{best.weight_utilization_pct}%")

        st.markdown("---")

        # 各柜型详细方案
        for r in results:
            spec = CONTAINER_SPECS[r.container_type]
            with st.expander(f"🚛 {r.container_type} ({spec['name']}) — {r.total_cartons} 箱", expanded=(r == best)):
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("装箱总数", f"{r.total_cartons} 箱")
                mc2.metric("总件数", f"{r.total_units} pcs")
                mc3.metric("总重量", f"{r.total_weight_kg:,.1f} kg")
                mc4.metric("总体积", f"{r.volume_used_cbm:.2f} CBM")

                st.markdown("**装载排列：**")
                st.code(f"排列: {r.arrangement}\n"
                        f"每层: {r.cartons_per_layer} 箱 ({r.length_fit} x {r.width_fit})\n"
                        f"层数: {r.layers} 层")

                pcol1, pcol2 = st.columns(2)
                with pcol1:
                    st.progress(min(r.volume_utilization_pct / 100, 1.0))
                    st.caption(f"体积利用率: {r.volume_utilization_pct}% ({r.volume_used_cbm:.2f} / {r.volume_total_cbm} CBM)")
                with pcol2:
                    st.progress(min(r.weight_utilization_pct / 100, 1.0))
                    max_payload = spec["max_payload_kg"]
                    st.caption(f"重量利用率: {r.weight_utilization_pct}% ({r.total_weight_kg:,.0f} / {max_payload:,} kg)")

                if r.remaining_space_mm:
                    st.caption(
                        f"剩余空间 — 长: {r.remaining_space_mm['length']:.0f}mm, "
                        f"宽: {r.remaining_space_mm['width']:.0f}mm, "
                        f"高: {r.remaining_space_mm['height']:.0f}mm"
                    )

                if r.warnings:
                    for w in r.warnings:
                        st.warning(f"⚠️ {w}")

        # 柜型推荐（如果指定了目标箱数）
        if target_qty > 0:
            st.markdown("---")
            st.markdown("### 🎯 柜型推荐")
            rec = recommend_container(carton, target_qty)
            if rec["recommended"]:
                st.success(
                    f"推荐使用 **{rec['recommended']}** 柜型，"
                    f"需要 **{rec['containers_needed']}** 个集装箱装载 {target_qty} 箱货物。"
                )
                # 显示各柜型对比
                cols_header = st.columns([2, 2, 2, 2, 2])
                cols_header[0].markdown("**柜型**")
                cols_header[1].markdown("**每柜装箱数**")
                cols_header[2].markdown("**需要柜数**")
                cols_header[3].markdown("**体积利用率**")
                cols_header[4].markdown("**重量利用率**")
                for opt in rec["all_options"]:
                    cols = st.columns([2, 2, 2, 2, 2])
                    marker = " ✅" if opt["container_type"] == rec["recommended"] else ""
                    cols[0].write(f"{opt['container_type']}{marker}")
                    cols[1].write(f"{opt['cartons_per_container']} 箱")
                    cols[2].write(f"{opt['containers_needed']} 柜")
                    cols[3].write(f"{opt['volume_utilization']:.1f}%")
                    cols[4].write(f"{opt['weight_utilization']:.1f}%")

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 装箱计算器</div>', unsafe_allow_html=True)
