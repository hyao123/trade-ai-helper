"""
pages/15_🌐_邮件润色.py
邮件翻译+润色：将邮件翻译成目标语言并/或润色优化，对比展示原文和改进版。
"""
import streamlit as st

from utils.ai_client import generate_email_polish
from utils.ui_helpers import (
    check_auth,
    get_user_id,
    inject_css,
    show_regenerate_buttons,
    show_result,
)

st.set_page_config(page_title="邮件润色 | 外贸AI助手", page_icon="🌐", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🌐 邮件翻译 & 润色</h1>
    <p class="hero-subtitle">AI 翻译/润色商务邮件，让表达更专业地道</p>
</div>
""", unsafe_allow_html=True)

# ── 侧栏输入 ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 润色参数")
    source_lang = st.selectbox(
        "原文语言",
        ["自动检测", "中文", "英文", "其他"],
        key="polish_source",
    )
    target_lang = st.selectbox(
        "目标语言",
        ["英文", "中文"],
        key="polish_target",
    )
    mode = st.selectbox(
        "处理模式",
        ["翻译", "润色", "翻译+润色"],
        key="polish_mode",
        help="翻译: 转换语言 | 润色: 优化表达 | 翻译+润色: 翻译后再优化",
    )
    stream_mode = st.toggle("⚡ 流式输出", value=True, key="polish_stream")

# ── 主内容区 ──────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 粘贴你的邮件原文，AI 会根据模式进行翻译和/或润色，让邮件更专业。</div>',
    unsafe_allow_html=True,
)

email_content = st.text_area(
    "邮件原文 *",
    height=250,
    placeholder="在此粘贴需要翻译或润色的邮件内容...\n\n例如:\n你好张经理，\n我们公司生产LED灯，质量好价格优惠。请问你们有兴趣吗？\n谢谢",
    value=st.session_state.get("polish_content_val", ""),
    key="polish_content_input",
)

generate_clicked = st.button("🚀 开始处理", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── 再生成处理 ────────────────────────────────────────
_regen_mode = st.session_state.pop("polish_regenerate", None)
if _regen_mode:
    generate_clicked = True
    email_content = st.session_state.get("polish_content_val", email_content)

# ── 生成逻辑 ──────────────────────────────────────────
if generate_clicked:
    if not email_content.strip():
        st.warning("⚠️ 请粘贴邮件原文")
    else:
        st.session_state["polish_content_val"] = email_content
        st.session_state.results.pop("polish", None)

        # 映射语言名
        source_map = {"自动检测": "Auto-detect", "中文": "Chinese", "英文": "English", "其他": "Other"}
        target_map = {"英文": "English", "中文": "Chinese"}
        src = source_map.get(source_lang, source_lang)
        tgt = target_map.get(target_lang, target_lang)

        fname = f"邮件润色_{mode}.txt"
        if stream_mode:
            result = generate_email_polish(
                email_content, src, tgt, mode,
                stream=True, user_id=get_user_id(),
            )
            show_result(
                result, "polish",
                label="📝 处理结果",
                file_name=fname,
                height=250,
                history_feature="邮件润色",
                history_title=f"{mode} - {email_content[:20]}...",
            )
        else:
            with st.spinner("🤖 AI 正在处理..."):
                result = generate_email_polish(
                    email_content, src, tgt, mode,
                    stream=False, user_id=get_user_id(),
                )
            st.session_state.results["polish"] = result
            show_result(
                result, "polish",
                label="📝 处理结果",
                file_name=fname,
                height=250,
                balloons=True,
                history_feature="邮件润色",
                history_title=f"{mode} - {email_content[:20]}...",
            )

        # 对比展示（原文 vs 结果）
        polished_text = st.session_state.results.get("polish", "")
        if polished_text and not polished_text.startswith("⚠️"):
            st.markdown("### 📊 原文 vs 改进版对比")
            col_orig, col_new = st.columns(2)
            with col_orig:
                st.markdown("**📄 原文：**")
                st.text_area("原文", email_content, height=180, key="compare_original", disabled=True)
            with col_new:
                st.markdown("**✨ 改进版：**")
                st.text_area("改进版", polished_text, height=180, key="compare_polished", disabled=True)

        show_regenerate_buttons("polish", show_style_button=False)

elif st.session_state.results.get("polish"):
    result_text = st.session_state.results["polish"]
    show_result(
        result_text,
        "polish",
        label="📝 处理结果（上次）",
        file_name="邮件润色.txt",
        height=250,
        balloons=False,
    )
    # 对比展示
    original = st.session_state.get("polish_content_val", "")
    if original and result_text and not result_text.startswith("⚠️"):
        st.markdown("### 📊 原文 vs 改进版对比")
        col_orig, col_new = st.columns(2)
        with col_orig:
            st.markdown("**📄 原文：**")
            st.text_area("原文", original, height=180, key="compare_original_prev", disabled=True)
        with col_new:
            st.markdown("**✨ 改进版：**")
            st.text_area("改进版", result_text, height=180, key="compare_polished_prev", disabled=True)
    show_regenerate_buttons("polish", show_style_button=False)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 邮件翻译 & 润色</div>', unsafe_allow_html=True)
