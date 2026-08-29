"""
pages/21_▪_AB测试.py
A/B 测试：生成邮件变体，模拟测试结果，对比转化率。
"""
from __future__ import annotations

import re

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
from utils.user_prefs import get_pref

st.set_page_config(page_title="A/B测试 | 外贸AI助手", page_icon="▪", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🧪 A/B 测试</h1>
    <p class="hero-subtitle">AI 生成多版邮件变体，支持 3 版本对比 + 效果追踪，科学优化转化率</p>
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
        product = st.text_input("产品 *", placeholder="e.g. LED Strip Lights", value=get_pref("default_product"))
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

            # Auto-create test record with parsed variant content
            if st.session_state.results.get("ab_variants"):
                content = st.session_state.results["ab_variants"]

                def _parse_variants(raw: str) -> list[dict]:
                    """Split AI output into per-variant blocks on '### Variant X' headers.

                    Returns a list of ``{label, content, subject_line}``. Blocks are
                    matched by the prompt's output convention so each returned variant
                    holds its own distinct body, not the whole generation.
                    """
                    raw = (raw or "").strip()
                    if not raw:
                        return []
                    parts = re.split(r'(?m)^###\s*Variant\s+([A-Za-z0-9])', raw)
                    # parts[0] is preamble text; then (label, body) pairs follow.
                    blocks: list[dict] = []
                    for i in range(1, len(parts) - 1, 2):
                        label = parts[i].strip()
                        body = (parts[i + 1] or "").strip()
                        if not body:
                            continue
                        subject = ""
                        m = re.search(r'(?im)^Subject\s*[:：]\s*(.+)$', body)
                        if m:
                            subject = m.group(1).strip()
                        blocks.append({
                            "label": label,
                            "content": body,
                            "subject_line": subject,
                        })
                    return blocks

                parsed = _parse_variants(content)

                def _fallback_label(i: int) -> str:
                    labels = ["A", "B", "C", "D", "E"]
                    return labels[i] if i < len(labels) else str(i + 1)

                # Only auto-create when we recovered at least the requested number of
                # distinct variants; otherwise the test would contain identical or
                # placeholder data, which makes A/B comparison meaningless.
                if len(parsed) >= num_variants:
                    variants = [
                        ABVariant(
                            variant_id=f"v{i}",
                            label=p["label"].strip() or _fallback_label(i),
                            content=p["content"],
                            subject_line=p["subject_line"],
                        )
                        for i, p in enumerate(parsed[:num_variants])
                    ]
                    try:
                        test = create_ab_test(
                            name=test_name or f"{product} A/B Test",
                            product=product,
                            variants=variants,
                        )
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"⚠️ 创建测试记录失败：{exc}")
                    else:
                        st.success(f"✅ 测试已创建: {test.test_id}（{len(variants)} 个独立变体）")
                else:
                    st.info("ℹ️ 未能从 AI 输出中切分出足够数量的独立变体，未自动创建测试记录。你可以复制上方生成结果作为参考。")

with tab_history:
    try:
        tests = load_ab_tests()
    except Exception:  # noqa: BLE001 - corrupted/unreadable storage shouldn't crash the tab
        tests = []
        st.warning("⚠️ 测试历史读取失败，请稍后重试。")

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
                            try:
                                simulate_results(test, total_sends=200)
                            except Exception as exc:  # noqa: BLE001
                                st.error(f"⚠️ 模拟结果失败：{exc}")
                            else:
                                st.rerun()
                    with col_del:
                        if st.button("🗑️ 删除测试", key=f"del_{test.test_id}", use_container_width=True):
                            try:
                                delete_ab_test(test.test_id)
                            except Exception as exc:  # noqa: BLE001
                                st.error(f"⚠️ 删除测试失败：{exc}")
                            else:
                                st.rerun()

    st.markdown("---")
    st.markdown('<div class="footer">💼 外贸AI助手 · A/B 测试</div>', unsafe_allow_html=True)
