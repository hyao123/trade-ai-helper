"""
pages/24_🔁_批量生成.py
批量生成：同一产品一键生成 N 封风格各异的开发信，供对比选优或 A/B 测试。
"""
from __future__ import annotations

import uuid

import streamlit as st

from config.prompts import EMAIL_LANGUAGES
from utils.ai_client import call_llm
from utils.history import add_to_history
from utils.ui_helpers import check_auth, copy_button, get_user_id, inject_css
from utils.user_prefs import get_ai_style_suffix, get_pref

st.set_page_config(page_title="批量生成 | 外贸AI助手", page_icon="🔁", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}
if "batch_results" not in st.session_state:
    st.session_state.batch_results = []

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🔁 批量生成</h1>
    <p class="hero-subtitle">同一产品一键生成多封风格各异的开发信，找出最高转化率的版本</p>
</div>
""", unsafe_allow_html=True)

# ── 表单 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="form-title">📝 批量生成参数</div>', unsafe_allow_html=True)

st.markdown("""
<div class="tip-card">
💡 系统将为同一产品生成多封开发信，每封使用不同的角度、开场白和 CTA 策略，方便你 A/B 测试或直接选用最佳版本。
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    product = st.text_input(
        "产品名称 *",
        value=get_pref("default_product"),
        placeholder="例如: LED Street Light 100W",
    )
    customer = st.text_input(
        "目标客户 *",
        placeholder="例如: Lighting Wholesaler, USA",
    )
    features = st.text_area(
        "产品卖点 *",
        height=120,
        placeholder="• IP66防水\n• 5年保修\n• CE/RoHS认证\n• 支持OEM",
    )

with col2:
    num_variants = st.slider(
        "生成数量",
        min_value=2,
        max_value=10,
        value=5,
        step=1,
        help="生成越多消耗 API 调用次数越多",
    )
    language = st.selectbox(
        "输出语言",
        list(EMAIL_LANGUAGES.keys()),
        index=list(EMAIL_LANGUAGES.keys()).index(
            get_pref("default_language") if get_pref("default_language") in EMAIL_LANGUAGES else "英语"
        ),
    )
    strategy = st.multiselect(
        "使用策略（选多个以增加多样性）",
        [
            "开门见山型：直接说产品价值",
            "痛点共鸣型：先讲买家痛点",
            "数字证明型：用数据说话",
            "好奇心驱动型：悬念开头",
            "社会认同型：客户案例引导",
            "紧迫感型：限时/限量",
            "问题导入型：以问题开头",
            "故事叙述型：品牌故事开场",
        ],
        default=[
            "开门见山型：直接说产品价值",
            "痛点共鸣型：先讲买家痛点",
            "数字证明型：用数据说话",
            "好奇心驱动型：悬念开头",
            "社会认同型：客户案例引导",
        ],
        help="每种策略对应不同的开场白和说服逻辑",
    )

generate_clicked = st.button(
    f"🚀 一键生成 {num_variants} 封开发信",
    type="primary",
    use_container_width=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not product.strip():
        st.warning("⚠️ 请填写产品名称")
    elif not customer.strip():
        st.warning("⚠️ 请填写目标客户")
    elif not features.strip():
        st.warning("⚠️ 请填写产品卖点")
    else:
        lang_name = EMAIL_LANGUAGES.get(language, "English")

        # Cycle strategies
        strats = strategy if strategy else [
            "开门见山型：直接说产品价值",
            "痛点共鸣型：先讲买家痛点",
            "数字证明型：用数据说话",
        ]

        st.session_state.batch_results = []
        progress = st.progress(0.0, text="正在生成第 1 封...")
        uid = get_user_id()
        style_suffix = get_ai_style_suffix()

        for i in range(num_variants):
            strat = strats[i % len(strats)]
            label = chr(65 + i)  # A, B, C...

            prompt = f"""Generate a cold email in {lang_name} for the following:

Product: {product}
Target Customer: {customer}
Key Features: {features}
Writing Strategy: {strat}

Requirements:
1. Subject line: under 60 chars, compelling
2. Body: 60-90 words, {lang_name}
3. Use the specified strategy: {strat}
4. Include a clear Call to Action
5. Sign off with [Your Name] / [Your Company]
6. Output format:
Subject: [subject line]

[email body]

Plain text only, no markdown symbols.{style_suffix}"""

            system = f"你是一位外贸开发信专家，精通{lang_name}写作，擅长使用不同心理策略撰写高转化冷邮件。"

            with st.spinner(f"⚡ 正在生成第 {i + 1}/{num_variants} 封（策略: {strat.split('：')[0]}）..."):
                result = call_llm(prompt, system, user_id=uid)

            st.session_state.batch_results.append({
                "id": str(uuid.uuid4())[:6],
                "label": label,
                "strategy": strat,
                "content": result,
            })
            progress.progress((i + 1) / num_variants, text=f"已完成 {i + 1}/{num_variants} 封")

        progress.empty()
        st.balloons()

        # Save to history
        combined = "\n\n" + "=" * 60 + "\n\n".join(
            f"=== 版本 {r['label']} ({r['strategy'].split('：')[0]}) ===\n{r['content']}"
            for r in st.session_state.batch_results
        )
        add_to_history("批量生成", f"{product} × {num_variants}封", combined)

# ── 展示结果 ──────────────────────────────────────────
if st.session_state.batch_results:
    st.markdown("---")
    st.markdown(f"### 📬 生成结果（共 {len(st.session_state.batch_results)} 封）")

    # Quick comparison table
    with st.expander("📊 快速对比（仅主题行）", expanded=True):
        for r in st.session_state.batch_results:
            content = r["content"]
            # Extract subject line
            subject = ""
            for line in content.splitlines():
                if line.lower().startswith("subject:"):
                    subject = line.split(":", 1)[1].strip()
                    break
            strat_short = r["strategy"].split("：")[0]
            st.markdown(
                f'<div style="display:flex;gap:0.75rem;align-items:center;'
                f'padding:0.5rem;border-bottom:1px solid #f3f4f6;">'
                f'  <span style="background:#1e3a5f;color:white;padding:0.2rem 0.6rem;'
                f'border-radius:8px;font-weight:700;font-size:0.85rem;">版本 {r["label"]}</span>'
                f'  <span style="background:#eff6ff;color:#3b82f6;padding:0.2rem 0.6rem;'
                f'border-radius:6px;font-size:0.78rem;">{strat_short}</span>'
                f'  <span style="font-size:0.9rem;color:#1e3a5f;">'
                f'{"📌 " + subject if subject else "（无主题行）"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Full content cards
    for r in st.session_state.batch_results:
        strat_short = r["strategy"].split("：")[0]
        with st.expander(f"📧 版本 {r['label']} — {strat_short}", expanded=(r["label"] == "A")):
            st.markdown(
                f'<div style="background:#f8fafc;border-radius:8px;padding:1rem;'
                f'border:1px solid #e2e8f0;white-space:pre-wrap;'
                f'font-size:0.9rem;line-height:1.7;">{r["content"]}</div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    f"📥 下载版本 {r['label']}",
                    r["content"],
                    file_name=f"cold_email_{product[:15]}_v{r['label']}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"dl_{r['id']}",
                )
            with c2:
                copy_button(r["content"], f"batch_{r['id']}")

    # Download all
    st.markdown("---")
    all_content = "\n\n" + ("=" * 60 + "\n\n").join(
        f"版本 {r['label']} — {r['strategy'].split('：')[0]}\n\n{r['content']}"
        for r in st.session_state.batch_results
    )
    st.download_button(
        "📥 下载全部版本（TXT）",
        all_content,
        file_name=f"batch_emails_{product[:15]}.txt",
        mime="text/plain",
        use_container_width=True,
        type="primary",
    )

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 批量生成</div>', unsafe_allow_html=True)
