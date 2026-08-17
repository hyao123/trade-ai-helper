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
tab_identity, tab_style, tab_advanced, tab_custom_model = st.tabs(
    ["👤 身份信息（自动预填）", "✍️ AI 写作风格", "🔧 高级 Prompt 控制", "🔑 自定义模型"]
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

    # ── 企业介绍（用于自动推送匹配）──
    st.markdown("---")
    st.markdown("##### 🏢 企业介绍（用于智能推送自动匹配）")
    from utils.auto_outreach import INDUSTRY_TEMPLATES
    industry_keys = list(INDUSTRY_TEMPLATES.keys())
    industry_labels = [INDUSTRY_TEMPLATES[k]["label"] for k in industry_keys]
    current_industry = prefs.get("company_industry", "")
    industry_idx = industry_keys.index(current_industry) if current_industry in industry_keys else 0
    company_industry = st.selectbox(
        "企业所属行业",
        options=industry_keys,
        index=industry_idx,
        format_func=lambda x: INDUSTRY_TEMPLATES[x]["label"],
        help="选择你的企业所属行业，推送时系统可自动匹配对口客户",
    )
    company_description = st.text_area(
        "企业简介",
        value=prefs.get("company_description", ""),
        placeholder="例如：深圳XX科技有限公司，成立于2010年，专注LED照明产品研发与出口，服务全球80+国家，年出口额超5000万美元...",
        height=80,
        help="简要描述你的企业背景、优势、出口经验等，推送邮件时自动引用",
    )
    main_products = st.text_area(
        "主营产品",
        value=prefs.get("main_products", ""),
        placeholder="例如：LED路灯、工矿灯、泛光灯、太阳能路灯等户外照明产品，功率范围30W-500W",
        height=60,
        help="描述你的主营产品线，逗号分隔或自由描述，推送时与产品目录互补",
    )

    if st.button("💾 保存身份信息", type="primary", use_container_width=True, key="save_identity"):
        update_prefs({
            "company_name": company_name,
            "contact_name": contact_name,
            "email": email_addr,
            "phone": phone,
            "signature_name": contact_name,
            "default_product": default_product,
            "company_industry": company_industry,
            "company_description": company_description,
            "main_products": main_products,
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

# ──────────────────────────────────────────────────────
# Tab 4: Custom Model Provider
# ──────────────────────────────────────────────────────
with tab_custom_model:
    st.markdown('<div class="main-form">', unsafe_allow_html=True)
    st.markdown("""
    <div class="tip-card">
    🔑 配置任意兼容 OpenAI 接口的模型服务（SiliconFlow、Ollama、月之暗面、零一万物等）。
    启用后将<strong>优先</strong>于内置 NVIDIA / OpenAI / DeepSeek 调用。
    </div>
    """, unsafe_allow_html=True)

    custom_enabled = st.toggle(
        "启用自定义模型",
        value=prefs.get("custom_provider_enabled", "false").lower() == "true",
        help="开启后，所有 AI 生成将优先使用下方配置的自定义模型",
    )

    # ── Preset shortcuts ──────────────────────────────
    PRESETS: dict[str, dict] = {
        "（手动填写）": {"base_url": "", "model": ""},
        "DeepSeek (官方推荐 · 超高性价比)": {
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "guide": "前往 https://platform.deepseek.com 登录并创建 API Key，充值 2 元即可使用数月。",
        },
        "阿里通义千问 (DashScope)": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "guide": "前往阿里云百炼平台开通并获取 API Key，新用户赠送数百万免费 Token。",
        },
        "智谱 AI (GLM-4)": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4-flash",
            "guide": "前往智谱开放平台注册并创建 API Key，glm-4-flash 模型免费开放。",
        },
        "月之暗面 (Moonshot / Kimi)": {
            "base_url": "https://api.moonshot.cn/v1",
            "model": "moonshot-v1-8k",
            "guide": "前往 https://platform.moonshot.cn 注册并创建 API Key。",
        },
        "SiliconFlow (硅基流动)": {
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "Qwen/Qwen2.5-72B-Instruct",
            "guide": "前往 https://siliconflow.cn 注册并生成 API Key。",
        },
        "OpenAI (官方)": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "guide": "前往 https://platform.openai.com 获取 API Key。",
        },
        "Groq (海外极速推理)": {
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile",
            "guide": "前往 https://console.groq.com 获取免费 API Key。",
        },
        "Ollama (本地私有化)": {
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5:72b",
            "guide": "本地运行 ollama run qwen2.5 即可无需联网使用。",
        },
    }

    preset_names = list(PRESETS.keys())
    # Detect which preset matches current prefs (by base_url)
    current_base = prefs.get("custom_provider_base_url", "")
    default_preset_idx = 0
    for i, (pname, pcfg) in enumerate(PRESETS.items()):
        if pcfg.get("base_url") and pcfg["base_url"] == current_base:
            default_preset_idx = i
            break

    selected_preset = st.selectbox(
        "快速选择服务商",
        preset_names,
        index=default_preset_idx,
        help="选择后自动填入 Base URL 和推荐模型，也可手动修改",
        disabled=not custom_enabled,
    )
    preset_cfg = PRESETS[selected_preset]
    if preset_cfg.get("guide"):
        st.markdown(
            f'<div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 14px; font-size: 0.85rem; color: #166534; margin: 8px 0 14px;">'
            f'💡 <strong>新手指南：</strong>{preset_cfg["guide"]}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        custom_name = st.text_input(
            "服务商名称（备注用）",
            value=prefs.get("custom_provider_name", "") or selected_preset.split(" ")[0],
            placeholder="例如: SiliconFlow",
            disabled=not custom_enabled,
        )
        custom_base_url = st.text_input(
            "Base URL *",
            value=prefs.get("custom_provider_base_url", "") if default_preset_idx == 0
                  else preset_cfg.get("base_url", prefs.get("custom_provider_base_url", "")),
            placeholder="https://api.siliconflow.cn/v1",
            help="以 /v1 结尾的 OpenAI 兼容接口地址",
            disabled=not custom_enabled,
        )

    with col_c2:
        custom_model = st.text_input(
            "模型 ID *",
            value=prefs.get("custom_provider_model", "") if default_preset_idx == 0
                  else preset_cfg.get("model", prefs.get("custom_provider_model", "")),
            placeholder="例如: Qwen/Qwen2.5-72B-Instruct",
            help="传入 API 的 model 字段，需与服务商文档一致",
            disabled=not custom_enabled,
        )
        custom_api_key = st.text_input(
            "API Key (SK) *",
            value="",  # Do not echo the saved key back into the widget.
            placeholder=("••••••••（已保存，留空保持不变）" if prefs.get("custom_provider_api_key")
                         else "sk-xxxxxxxxxxxxxxxxxxxxxxxx"),
            type="password",
            help="Bearer token / Secret Key，不会上传到任何第三方。留空则保留已保存的 Key。",
            disabled=not custom_enabled,
        )

    # ── Connection test ───────────────────────────────
    col_save, col_test = st.columns([2, 1])

    with col_save:
        if st.button("💾 保存自定义模型配置", type="primary",
                     use_container_width=True, key="save_custom_model"):
            saved_key = prefs.get("custom_provider_api_key", "").strip()
            new_key = custom_api_key.strip()
            # A blank field keeps the previously saved key (the widget never
            # echoes it back, so the user cannot accidentally wipe it).
            effective_key = new_key or saved_key
            if custom_enabled and (not custom_base_url.strip() or
                                   not effective_key or
                                   not custom_model.strip()):
                st.error("❌ 启用自定义模型时，Base URL、模型 ID 和 API Key 均为必填项。")
            else:
                update_prefs({
                    "custom_provider_enabled": "true" if custom_enabled else "false",
                    "custom_provider_name": custom_name.strip(),
                    "custom_provider_base_url": custom_base_url.strip().rstrip("/"),
                    "custom_provider_model": custom_model.strip(),
                    "custom_provider_api_key": effective_key,
                })
                if custom_enabled:
                    st.success(f"✅ 已保存！后续所有 AI 调用将优先使用 **{custom_name or custom_model}**。")
                else:
                    st.success("✅ 已保存（自定义模型已禁用，恢复使用内置服务商）。")

    with col_test:
        if st.button("🔗 测试连接", use_container_width=True, key="test_custom_model",
                     disabled=not custom_enabled):
            test_key = custom_api_key.strip() or prefs.get("custom_provider_api_key", "").strip()
            if not custom_base_url.strip() or not test_key or not custom_model.strip():
                st.warning("请先填写 Base URL、模型 ID 和 API Key")
            else:
                with st.spinner("连接测试中…"):
                    try:
                        from openai import OpenAI as _OAI
                        _test_client = _OAI(
                            api_key=test_key,
                            base_url=custom_base_url.strip().rstrip("/"),
                        )
                        _resp = _test_client.chat.completions.create(
                            model=custom_model.strip(),
                            messages=[{"role": "user", "content": "Say OK"}],
                            max_tokens=5,
                            timeout=15,
                        )
                        _reply = (_resp.choices[0].message.content or "").strip()
                        st.success(f"✅ 连接成功！模型回复: {_reply}")
                    except Exception as _e:
                        st.error(f"❌ 连接失败: {_e}")

    # ── Current status card ───────────────────────────
    st.markdown("---")
    _cp = get_prefs()
    _cp_enabled = _cp.get("custom_provider_enabled", "false").lower() == "true"
    _cp_url = _cp.get("custom_provider_base_url", "")
    _cp_model = _cp.get("custom_provider_model", "")
    _cp_has_key = bool(_cp.get("custom_provider_api_key", "").strip())

    if _cp_enabled and _cp_url and _cp_model and _cp_has_key:
        st.info(
            f"🟢 **自定义模型已启用**  \n"
            f"服务商: `{_cp.get('custom_provider_name', '自定义') or '自定义'}`  \n"
            f"Base URL: `{_cp_url}`  \n"
            f"模型: `{_cp_model}`  \n"
            f"API Key: `{'*' * 8}{_cp.get('custom_provider_api_key','')[-4:]}`"
        )
    elif _cp_enabled:
        st.warning("⚠️ 自定义模型已开启但配置不完整，请检查 Base URL / 模型 ID / API Key。")
    else:
        st.info("⚪ 自定义模型未启用，使用内置服务商（NVIDIA / OpenAI / DeepSeek）。")

    st.markdown("</div>", unsafe_allow_html=True)


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

_cm_enabled = current_prefs.get("custom_provider_enabled", "false").lower() == "true"
_cm_ok = all([
    _cm_enabled,
    current_prefs.get("custom_provider_base_url", "").strip(),
    current_prefs.get("custom_provider_model", "").strip(),
    current_prefs.get("custom_provider_api_key", "").strip(),
])
if _cm_ok:
    _cm_label = current_prefs.get("custom_provider_name", "") or current_prefs.get("custom_provider_model", "")
    st.info(f"🔑 **自定义模型已启用：** `{_cm_label}` · 所有 AI 调用将优先使用此模型")
elif _cm_enabled:
    st.warning("🔑 自定义模型已开启但配置不完整，请前往「🔑 自定义模型」Tab 补全设置。")

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · AI偏好设置</div>', unsafe_allow_html=True)
