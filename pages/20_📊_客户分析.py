"""
pages/20_📊_客户分析.py
客户数据分析仪表盘：转化漏斗、活跃度、地区/行业分布。
"""
from __future__ import annotations

import streamlit as st
from utils.ui_helpers import inject_css, check_auth
from utils.customers import get_customers
from utils.analytics import (
    generate_full_report,
    STAGE_ORDER,
    STAGE_LABELS_EN,
)

st.set_page_config(page_title="客户分析 | 外贸AI助手", page_icon="📊", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📊 客户分析</h1>
    <p class="hero-subtitle">可视化客户转化漏斗、活跃度分析、地区行业分布</p>
</div>
""", unsafe_allow_html=True)

# ── 加载客户数据 ──────────────────────────────────────
customers = get_customers()

if not customers:
    st.info("📭 暂无客户数据。请先在「客户管理」页面添加客户，或导入 CSV 数据。")
    st.markdown("---")
    st.markdown('<div class="footer">💼 外贸AI助手 · 客户分析</div>', unsafe_allow_html=True)
    st.stop()

# ── 生成报告 ──────────────────────────────────────────
report = generate_full_report(customers)

# ── 核心指标 ──────────────────────────────────────────
st.markdown("### 📈 核心指标")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("👥 总客户数", report.total_customers)
k2.metric("📈 转化率", f"{report.conversion_rate}%")
k3.metric("🟢 活跃客户", report.active_customers)
k4.metric("😴 沉默客户", report.dormant_customers)
k5.metric("📅 平均联系天数", f"{report.avg_days_since_contact:.0f} 天")

st.markdown("---")

# ── 转化漏斗 ──────────────────────────────────────────
st.markdown("### 🔄 客户转化漏斗")
if report.funnel:
    max_count = max(f.count for f in report.funnel) if report.funnel else 1
    for f_stage in report.funnel:
        bar_width = int((f_stage.count / max_count) * 100) if max_count > 0 else 0
        col_label, col_bar, col_num = st.columns([2, 6, 1])
        with col_label:
            st.write(f"**{f_stage.stage}**")
            st.caption(f_stage.label_en)
        with col_bar:
            st.progress(bar_width / 100)
        with col_num:
            st.write(f"**{f_stage.count}**")
            st.caption(f"{f_stage.percentage}%")

st.markdown("---")

# ── 地区分布 & 行业分布 ──────────────────────────────
col_geo, col_ind = st.columns(2)

with col_geo:
    st.markdown("### 🌍 客户地区分布")
    if report.top_countries:
        for country, count in report.top_countries:
            pct = (count / report.total_customers) * 100
            st.write(f"🏳️ **{country}** — {count} 家 ({pct:.1f}%)")
    else:
        st.info("暂无地区数据（请在客户信息中填写国家/地区字段）")

with col_ind:
    st.markdown("### 🏭 客户行业分布")
    if report.top_industries:
        for industry, count in report.top_industries:
            pct = (count / report.total_customers) * 100
            st.write(f"🏢 **{industry}** — {count} 家 ({pct:.1f}%)")
    else:
        st.info("暂无行业数据（请在客户信息中填写行业字段）")

st.markdown("---")

# ── 月度活动趋势 ──────────────────────────────────────
st.markdown("### 📅 近6个月联系活跃度")
if report.monthly_activity:
    months = [m["month"] for m in report.monthly_activity]
    counts = [m["count"] for m in report.monthly_activity]
    max_monthly = max(counts) if counts else 1

    for month, count in zip(months, counts):
        bar_pct = (count / max_monthly) if max_monthly > 0 else 0
        mc1, mc2, mc3 = st.columns([2, 6, 1])
        with mc1:
            st.write(f"**{month}**")
        with mc2:
            st.progress(bar_pct)
        with mc3:
            st.write(f"{count}")

st.markdown("---")

# ── 阶段分布详情 ──────────────────────────────────────
st.markdown("### 📋 客户阶段明细")
stage_data = []
for stage in STAGE_ORDER:
    count = report.stage_distribution.get(stage, 0)
    if count > 0:
        stage_data.append({"阶段": stage, "English": STAGE_LABELS_EN.get(stage, stage), "数量": count})

if stage_data:
    st.table(stage_data)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 客户分析</div>', unsafe_allow_html=True)
