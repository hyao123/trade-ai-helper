"""
pages/0_⚙️_AI偏好.py
AI 风格偏好 + 用户信息预填设置页。

用户在此页面设置的所有参数会自动同步到其他所有功能页面，
避免每次重复填写公司名、签名、风格偏好等。
"""
from __future__ import annotations

import streamlit as st

from utils.ui_helpers import check_auth, inject_css
from utils.user_auth import get_current_user
from utils.user_prefs import get_prefs, update_prefs

st.set_page_config(page_title="AI偏好设置 | 外贸AI助手", page_icon="⚙️", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">⚙️ AI 偏好设置</h1>
    <p class="hero-subtitle">设置一次，全站生效 · 公司信息自动预填 · AI 写作风格个性化</p>
</div>
""", unsafe_allow_html=True)

current_user = get_current_user()
prefs = get_prefs()

# ══════════════════════════════════════════════════════
# Tab 1: 身份信息（自动预填到所有表单）
# Tab 2: AI 写作风格
# Tab 3: 高级 Prompt 控制
# ══════════════════════════════════════════════════════
tab_identity, tab_style, tab_advanced = st.tabs(
    ["👤 身份信息（自动预填）", "✍️ AI 写作风格", "🔧 高级 Prompt 控制"]
)

# ──────────────────────────────────────────────────────
# Tab 1: Identity / 身份信息
# ──────────────────────────────────────────────────────
with tab_identity:
    st.markdown('<div class="main-form">', unsafe_allow_html=True)
    st.markdown("""
    <div class="tip-card">
    💡 填写后，开发信、询盘回复、报价单等所有页面的"公司名称"、"联系人"等字段将自动预填，无需每次重复输入。
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input(
            "公司名称",
            value=prefs.get("company_name", ""),
            placeholder="例如: Shenzhen LED Technology Co., Ltd.",
        )
        contact_name = st.text_input(
            "联系人姓名（签名用）",
            value=prefs.get("contact_name", ""),
            placeholder="例如: Tom Chen",
        )
        email_addr = st.text_input(
            "联系邮箱",
            value=prefs.get("email", ""),
            placeholder="sales@yourcompany.com",
        )
    with col2:
        phone = st.text_input(
            "联系电话",
            value=prefs.get("phone", ""),
            placeholder="+86-755-XXXXXXXX",
        )
        default_product = st.text_input(
            "常用产品（默认预填）",
            value=prefs.get("default_product", ""),
            placeholder="例如: LED Street Light",
        )
        default_language = st.selectbox(
            "默认输出语言",
            ["英语", "西班牙语", "法语", "德语", "葡萄牙语", "阿拉伯语", "俄语"],
            index=["英语", "西班牙语", "法语", "德语", "葡萄牙语", "阿拉伯语", "俄语"].index(
                prefs.get("default_language", "英语")
            ),
        )

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        default_tone = st.selectbox(
            "默认邮件风格",
            ["简洁专业", "正式商务", "亲切友好"],
            index=["简洁专业", "正式商务", "亲切友好"].index(
                prefs.get("default_tone", "简洁专业")
            ),
        )
    with col_t2:
        default_trade_term = st.selectbox(
            "默认贸易术语",
            ["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"],
            index=["FOB", "CIF", "EXW", "DDP", "CFR", "FCA"].index(
                prefs.get("default_trade_term", "FOB")
            ),
        )

    if st.button("💾 保存身份信息", type="primary", use_container_width=True, key="save_identity"):
        update_prefs({
            "company_name": company_name,
            "contact_name": contact_name,
            "email": email_addr,
            "phone": phone,
            "signature_name": contact_name,
            "default_product": default_product,
            "default_language": default_language,
            "default_tone": default_tone,
            "default_trade_term": default_trade_term,
        })
        st.success("✅ 身份信息已保存！下次访问所有页面将自动预填。")
        st.balloons()

    st.markdown("</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────
# Tab 2: AI Writing Style
# ──────────────────────────────────────────────────────
with tab_style:
    st.markdown('<div class="main-form">', unsafe_allow_html=True)
    st.markdown("""
    <div class="tip-card">
    💡 AI 写作风格设置会影响所有生成内容的语气、长度和格式，无需每次手动调整。
    </div>
    """, unsafe_allow_html=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        ai_tone = st.radio(
            "语气风格",
            ["专业", "友好", "正式", "简洁"],
            index=["专业", "友好", "正式", "简洁"].index(
                prefs.get("ai_style_tone", "专业")
            ),
            help="专业=B2B标准 | 友好=建立关系 | 正式=大客户/机构 | 简洁=高效直接",
        )
    with col_s2:
        ai_length = st.radio(
            "回复长度",
            ["简短", "中等", "详细"],
            index=["简短", "中等", "详细"].index(
                prefs.get("ai_response_length", "中等")
            ),
            help="简短<80词 | 中等100-150词 | 详细150-250词",
        )

    # Preview
    tone_preview = {
        "专业": "Dear Mr. Smith, Thank you for your inquiry regarding our LED street lights. We'd be pleased to discuss...",
        "友好": "Hi Mike! Great to hear from you! We're really excited about the possibility of working together on...",
        "正式": "Dear Mr. Smith, We acknowledge receipt of your inquiry dated May 15, 2026. In accordance with...",
        "简洁": "Hi Mike, Thanks for reaching out. Our MOQ is 500 pcs at $12.50/unit FOB Shenzhen. Can we schedule a call?",
    }
    st.markdown("**预览效果：**")
    st.info(f'_{tone_preview.get(ai_tone, "")}_')

    if st.button("💾 保存风格设置", type="primary", use_container_width=True, key="save_style"):
        update_prefs({
            "ai_style_tone": ai_tone,
            "ai_response_length": ai_length,
        })
        st.success("✅ AI 风格设置已保存！")

    st.markdown("</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────
# Tab 3: Advanced Prompt Control
# ──────────────────────────────────────────────────────
with tab_advanced:
    st.markdown('<div class="main-form">', unsafe_allow_html=True)
    st.markdown("""
    <div class="tip-card">
    🔧 高级选项：在每次 AI 生成时附加自定义指令，或指定不希望 AI 使用的词语。
    </div>
    """, unsafe_allow_html=True)

    ai_custom = st.text_area(
        "自定义附加指令（会追加到每次生成）",
        value=prefs.get("ai_custom_instructions", ""),
        height=120,
        placeholder=(
            "例如：\n"
            "- Always mention our ISO 9001 certification\n"
            "- End every email with 'Looking forward to a long-term partnership'\n"
            "- Reference our 15-year factory experience"
        ),
        help="这些指令会追加到每个 Prompt 末尾，影响所有 AI 生成的内容。",
    )

    ai_forbidden = st.text_input(
        "禁用词（逗号分隔，AI 会避免使用这些词）",
        value=prefs.get("ai_forbidden_words", ""),
        placeholder="例如: cheap, inferior, basic",
        help="AI 生成内容时会尽量避免使用这些词语",
    )

    # Show current active instructions
    if ai_custom.strip() or ai_forbidden.strip():
        st.markdown("**当前生效的附加指令预览：**")
        preview_parts = []
        if ai_custom.strip():
            preview_parts.append(f"📌 自定义指令：{ai_custom.strip()[:200]}")
        if ai_forbidden.strip():
            words = [w.strip() for w in ai_forbidden.split(",") if w.strip()]
            preview_parts.append(f"🚫 禁用词：{', '.join(words)}")
        for part in preview_parts:
            st.caption(part)

    col_adv1, col_adv2 = st.columns(2)
    with col_adv1:
        if st.button("💾 保存高级设置", type="primary", use_container_width=True, key="save_advanced"):
            update_prefs({
                "ai_custom_instructions": ai_custom,
                "ai_forbidden_words": ai_forbidden,
            })
            st.success("✅ 高级 Prompt 设置已保存！")
    with col_adv2:
        if st.button("🗑️ 清空高级设置", use_container_width=True, key="clear_advanced"):
            update_prefs({
                "ai_custom_instructions": "",
                "ai_forbidden_words": "",
            })
            st.info("已清空高级设置")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ── 状态摘要 ──────────────────────────────────────────
st.markdown("---")
st.markdown("### 📋 当前设置摘要")

current_prefs = get_prefs()
summary_cols = st.columns(4)

with summary_cols[0]:
    st.markdown("**👤 身份**")
    st.caption(f"公司: {current_prefs.get('company_name', '未设置') or '未设置'}")
    st.caption(f"联系人: {current_prefs.get('contact_name', '未设置') or '未设置'}")
    st.caption(f"邮箱: {current_prefs.get('email', '未设置') or '未设置'}")

with summary_cols[1]:
    st.markdown("**📝 偏好**")
    st.caption(f"语言: {current_prefs.get('default_language', '英语')}")
    st.caption(f"风格: {current_prefs.get('default_tone', '简洁专业')}")
    st.caption(f"贸易术语: {current_prefs.get('default_trade_term', 'FOB')}")

with summary_cols[2]:
    st.markdown("**🤖 AI 风格**")
    st.caption(f"语气: {current_prefs.get('ai_style_tone', '专业')}")
    st.caption(f"长度: {current_prefs.get('ai_response_length', '中等')}")

with summary_cols[3]:
    st.markdown("**🔧 高级**")
    has_custom = bool(current_prefs.get("ai_custom_instructions", "").strip())
    has_forbidden = bool(current_prefs.get("ai_forbidden_words", "").strip())
    st.caption(f"自定义指令: {'✅ 已设置' if has_custom else '未设置'}")
    st.caption(f"禁用词: {'✅ 已设置' if has_forbidden else '未设置'}")

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · AI偏好设置</div>', unsafe_allow_html=True)
