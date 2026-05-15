"""
pages/21_🧪_AB测试.py
A/B 测试：生成邮件变体，模拟测试结果，对比转化率。
"""
from __future__ import annotations

import streamlit as st

from utils.ab_testing import (
    ABVariant,
    compute_confidence,
    create_ab_test,
    delete_ab_test,
    load_ab_tests,
    simulate_results,
)
from utils.ui_helpers import check_auth, get_user_id, inject_css, show_result

st.set_page_config(page_title="A/B测试 | 外贸AI助手", page_icon="🧪", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🧪 A/B 测试</h1>
    <p class="hero-subtitle">AI 生成多版邮件变体，模拟发送数据，科学对比转化效果</p>
</div>
""", unsafe_allow_html=True)

# ── 标签页 ──────────────────────────────────────────
tab_create, tab_history = st.tabs(["🆕 创建新测试", "📋 历史测试"])

with tab_create:
    st.markdown('<div class="main-form">', unsafe_allow_html=True)
    st.markdown('<div class="form-title">📝 设置 A/B 测试参数</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        test_name = st.text_input("测试名称", placeholder="e.g. Q3 Cold Email Campaign")
        product = st.text_input("产品 *", placeholder="e.g. LED Strip Lights")
    with col2:
        customer_type = st.text_input("目标客户类型 *", placeholder="e.g. Home Decor Wholesalers")
        num_variants = st.selectbox("变体数量", [2, 3, 4, 5], index=1)

    focus = st.radio("测试重点", ["subject_line", "full_email"], horizontal=True,
                     format_func=lambda x: "主题行测试" if x == "subject_line" else "完整邮件测试")

    st.markdown('<div class="tip-card">💡 A/B 测试帮助你找到最高转化率的邮件版本。建议先测试主题行，再测试邮件正文。</div>', unsafe_allow_html=True)

    generate_clicked = st.button("🚀 AI 生成测试变体", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if generate_clicked:
        if not product.strip():
            st.warning("⚠️ 请填写产品名称")
        elif not customer_type.strip():
            st.warning("⚠️ 请填写目标客户类型")
        else:
            from utils.ai_client import generate_ab_variants
            uid = get_user_id()
            result = generate_ab_variants(
                product=product,
                customer_type=customer_type,
                num_variants=num_variants,
                focus=focus,
                stream=True,
                user_id=uid,
            )
            show_result(
                result,
                result_key="ab_variants",
                label="🧪 A/B 测试变体",
                file_name=f"ab_test_{product[:15]}.txt",
                height=350,
                show_subject_line=False,
                history_feature="A/B测试",
                history_title=f"{test_name or product} - {num_variants}变体",
            )

            # Auto-create test record with generated content
            if st.session_state.results.get("ab_variants"):
                content = st.session_state.results["ab_variants"]
                # Parse variants from generated content
                labels = ["A", "B", "C", "D", "E"]
                variants = []
                for idx in range(num_variants):
                    label = labels[idx] if idx < len(labels) else str(idx + 1)
                    variants.append(ABVariant(
                        variant_id=f"v{idx}",
                        label=label,
                        content=content,  # Full content stored
                        subject_line=f"Variant {label}",
                    ))
                if variants:
                    test = create_ab_test(
                        name=test_name or f"{product} A/B Test",
                        product=product,
                        variants=variants,
                    )
                    st.success(f"✅ 测试已创建: {test.test_id}")

with tab_history:
    tests = load_ab_tests()

    if not tests:
        st.info("📭 暂无 A/B 测试记录。请先创建一个测试。")
    else:
        for test in tests:
            with st.expander(
                f"{'🟢' if test.status == 'completed' else '🔵'} "
                f"{test.name} — {test.created_at} ({len(test.variants)} 变体)",
                expanded=False,
            ):
                sc1, sc2, sc3 = st.columns(3)
                sc1.write(f"**产品:** {test.product}")
                sc2.write(f"**状态:** {test.status}")
                sc3.write(f"**创建时间:** {test.created_at}")

                if test.status == "completed":
                    # Show results
                    st.markdown("#### 📊 测试结果")
                    for v in test.variants:
                        vc1, vc2, vc3, vc4, vc5 = st.columns(5)
                        winner_mark = " 🏆" if v.variant_id == test.winner else ""
                        vc1.metric(f"变体 {v.label}{winner_mark}", f"{v.sends} 发送")
                        vc2.metric("打开率", f"{v.open_rate:.1f}%")
                        vc3.metric("点击率", f"{v.click_rate:.1f}%")
                        vc4.metric("回复率", f"{v.reply_rate:.1f}%")
                        vc5.write(f"Opens: {v.opens} | Clicks: {v.clicks} | Replies: {v.replies}")

                    # Statistical confidence
                    if len(test.variants) >= 2:
                        conf = compute_confidence(test.variants[0], test.variants[1])
                        st.caption(f"📐 变体 A vs B 统计置信度: {conf:.1f}%")

                elif test.status == "draft":
                    col_sim, col_del = st.columns(2)
                    with col_sim:
                        if st.button("🎲 模拟测试结果", key=f"sim_{test.test_id}", use_container_width=True):
                            simulate_results(test, total_sends=200)
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ 删除测试", key=f"del_{test.test_id}", use_container_width=True):
                            delete_ab_test(test.test_id)
                            st.rerun()

    st.markdown("---")
    st.markdown('<div class="footer">💼 外贸AI助手 · A/B 测试</div>', unsafe_allow_html=True)
