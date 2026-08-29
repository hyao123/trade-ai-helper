"""
pages/35_📥_AI收件箱.py
AI 智能收件箱：连接 Gmail / Outlook → 自动拉取 → AI 分类 → 优先级排序 → 一键回复
依赖: utils/inbox_integration (OAuth + fetch/send) + utils/inbox_ai (分类 + 回复建议)
"""
from __future__ import annotations

import streamlit as st

from utils.inbox_ai import (
    INTENT_CATEGORIES,
    generate_reply_suggestion,
    get_inbox_analytics,
    get_prioritized_inbox,
    process_inbox,
)
from utils.inbox_integration import (
    PROVIDERS,
    disconnect,
    exchange_code,
    fetch_inbox,
    get_auth_url,
    get_available_providers,
    get_connection_status,
    send_via_provider,
)
from utils.mailslurp_integration import (
    ensure_inbox,
    fetch_received_emails,
    get_inbox_state,
    is_mailslurp_configured,
    process_received_inbox,
)
from utils.secrets import get_secret
from utils.ui_helpers import (
    check_auth,
    copy_button,
    get_user_id,
    html_escape,
    inject_css,
)

st.set_page_config(page_title="AI收件箱 | 外贸AI助手", page_icon="📥", layout="wide")
inject_css()
check_auth()


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────
def _get_username() -> str:
    user = st.session_state.get("current_user")
    if user and user.get("username"):
        return user["username"]
    return "default"


def _get_redirect_uri() -> str:
    """Build the OAuth redirect URI (must match what's registered in Google/Microsoft console)."""
    base = (get_secret("APP_BASE_URL") or "http://localhost:8501").rstrip("/")
    return f"{base}/AI收件箱"


def _urgency_color(urgency: str) -> str:
    return {"high": "#dc2626", "medium": "#d97706", "low": "#6b7280"}.get(urgency, "#6b7280")


def _priority_bar(score: int) -> str:
    """Render a colored priority bar (0-100)."""
    if score >= 70:
        color = "#dc2626"
    elif score >= 40:
        color = "#f59e0b"
    else:
        color = "#6b7280"
    return (
        f'<div style="background:#e5e7eb;border-radius:4px;height:6px;width:80px;overflow:hidden;">'
        f'<div style="background:{color};height:100%;width:{score}%;"></div></div>'
    )


username = _get_username()
user_id = get_user_id()


# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📥 AI 智能收件箱</h1>
    <p class="hero-subtitle">连接 Gmail / Outlook，AI 自动按外贸场景分类并优先级排序客户邮件，重点客户一目了然</p>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════
# OAuth 回调处理（用户授权后被重定向回来）
# ═════════════════════════════════════════════════════════
qp = st.query_params
auth_code = qp.get("code")
auth_state = qp.get("state", "")

if auth_code:
    provider = auth_state if auth_state in PROVIDERS else "gmail"
    with st.spinner(f"正在连接 {provider}..."):
        ok, msg = exchange_code(
            provider=provider,
            code=auth_code,
            redirect_uri=_get_redirect_uri(),
            username=username,
        )
    if ok:
        st.success(f"✅ {provider} 连接成功！")
        # Clear query params to avoid re-processing on refresh
        try:
            st.query_params.clear()
        except Exception:
            pass
    else:
        st.error(f"❌ 授权失败: {msg}")


# ═════════════════════════════════════════════════════════
# 连接状态面板
# ═════════════════════════════════════════════════════════
status = get_connection_status(username)
available = get_available_providers()

with st.container():
    if status["connected"]:
        col_info, col_disc = st.columns([4, 1])
        with col_info:
            provider_name = status.get("provider", "?")
            email_addr = status.get("email", "")
            st.success(
                f"🟢 **已连接 {provider_name.title()}**" +
                (f" · 账号: `{email_addr}`" if email_addr else "")
            )
        with col_disc:
            if st.button("🔌 断开", key="disconnect_inbox", use_container_width=True):
                disconnect(username)
                st.rerun()
    else:
        st.markdown(
            '<div class="tip-card">'
            '💡 <b>第一次使用？</b>选择并连接你的邮箱服务商，AI 会拉取最近邮件、自动分类并按外贸场景排序。'
            '系统只读取邮件元数据 + 摘要用于分类，不会保存邮件正文。'
            '</div>',
            unsafe_allow_html=True,
        )

        if not available:
            st.warning("⚠️ **管理员尚未配置邮箱 OAuth 凭证，暂无法连接邮箱。**")
            with st.expander("🔧 如何配置（管理员 / 部署者点击展开）", expanded=True):
                redirect_uri = _get_redirect_uri()
                st.markdown(
                    "在项目的 `.env` 文件里填入任一组 OAuth 凭证并**重启应用**即可启用。\n\n"
                    "**选项 A — Gmail：**\n"
                    "1. 到 [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 创建 OAuth 2.0 客户端（Web 应用）\n"
                    "2. 把下方「重定向 URI」添加到该客户端的**已授权重定向 URI** 列表\n"
                    "3. 在 `.env` 中填 `GMAIL_CLIENT_ID` 和 `GMAIL_CLIENT_SECRET`\n\n"
                    "**选项 B — Outlook / Microsoft 365：**\n"
                    "1. 到 [Azure 门户](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) 注册应用\n"
                    "2. 把下方「重定向 URI」添加到该应用的**重定向 URI**（Web 平台）\n"
                    "3. 在 `.env` 中填 `OUTLOOK_CLIENT_ID` 和 `OUTLOOK_CLIENT_SECRET`\n\n"
                    "> 💡 本机开发也可用：应用以 `localhost:8501` 运行时，重定向 URI 同样适用（Google/Azure 均支持本地回环）。",
                    unsafe_allow_html=True,
                )
                st.code(f"重定向 URI（配置 OAuth 应用时需填写）：\n{redirect_uri}", language="text")
                st.caption("配置完成后刷新本页面，「连接按钮」即会出现。")
        else:
            col_g, col_o = st.columns(2)
            with col_g:
                if "gmail" in available:
                    auth_url = get_auth_url("gmail", _get_redirect_uri(), state="gmail")
                    st.link_button(
                        "🔗 连接 Gmail",
                        auth_url,
                        use_container_width=True,
                        type="primary",
                    )
                else:
                    st.button("🔗 连接 Gmail", disabled=True, use_container_width=True,
                              help="管理员未配置 GMAIL_CLIENT_ID/SECRET")
            with col_o:
                if "outlook" in available:
                    auth_url = get_auth_url("outlook", _get_redirect_uri(), state="outlook")
                    st.link_button(
                        "🔗 连接 Outlook",
                        auth_url,
                        use_container_width=True,
                        type="primary",
                    )
                else:
                    st.button("🔗 连接 Outlook", disabled=True, use_container_width=True,
                              help="管理员未配置 OUTLOOK_CLIENT_ID/SECRET")

        st.stop()


# ═════════════════════════════════════════════════════════
# Tabs: 收件箱 / 分析 / 设置
# ═════════════════════════════════════════════════════════
tab_inbox, tab_analytics = st.tabs(["📥 收件箱", "📊 分析洞察"])

# ─────────────────────────────────────────────────────────
# Tab 1: 智能收件箱
# ─────────────────────────────────────────────────────────
with tab_inbox:
    # ── 控制栏 ──
    col_refresh, col_count, col_filter = st.columns([1.5, 1, 2.5])

    with col_count:
        max_results = st.selectbox(
            "拉取数量",
            options=[10, 20, 30, 50],
            index=1,
            label_visibility="collapsed",
            help="每次刷新拉取的最新邮件数",
        )

    with col_filter:
        intent_filter = st.multiselect(
            "筛选意图",
            options=list(INTENT_CATEGORIES.keys()),
            format_func=lambda k: f"{INTENT_CATEGORIES[k]['icon']} {INTENT_CATEGORIES[k]['label']}",
            default=[],
            label_visibility="collapsed",
            placeholder="全部意图",
        )

    with col_refresh:
        refresh_clicked = st.button(
            "🔄 刷新并 AI 分类",
            type="primary",
            use_container_width=True,
            help="拉取最新邮件并对未处理过的邮件运行 AI 分类",
        )

    # ── 刷新逻辑：拉取 + 分类 ──
    if refresh_clicked:
        with st.spinner(f"正在拉取最新 {max_results} 封邮件..."):
            ok, result = fetch_inbox(username, max_results=max_results)

        if not ok:
            st.error(f"❌ 拉取失败: {result}")
            st.session_state["_inbox_processed"] = []
        else:
            emails = result
            if not emails:
                st.info("📭 收件箱为空（或没有最近邮件）")
                st.session_state["_inbox_processed"] = []
            else:
                progress = st.progress(0, text=f"AI 正在分析 {len(emails)} 封邮件...")
                # process_inbox 会用缓存避免重复分类已处理过的邮件
                processed = process_inbox(username, emails, force_reprocess=False)
                progress.progress(1.0, text=f"✅ 完成！共处理 {len(processed)} 封邮件")
                st.session_state["_inbox_processed"] = processed
                # 一行汇总
                urgent = sum(1 for p in processed
                             if p.get("classification", {}).get("urgency") == "high")
                if urgent:
                    st.warning(f"⚠️ 发现 **{urgent}** 封高优先级邮件需要尽快处理")
                else:
                    st.success(f"✅ 已分析 {len(processed)} 封邮件，无紧急事项")

    # ── 邮件列表 ──
    processed = st.session_state.get("_inbox_processed", [])
    # 如果 session_state 为空，尝试加载已缓存的
    if not processed:
        cached = get_prioritized_inbox(username, limit=50)
        if cached:
            st.caption(f"📌 显示上次分析的 {len(cached)} 封邮件缓存（点击「🔄 刷新」获取最新）")
            processed = cached

    # 应用 intent filter
    if intent_filter and processed:
        processed = [
            p for p in processed
            if p.get("classification", {}).get("intent") in intent_filter
        ]

    if not processed:
        st.info("👆 点击「🔄 刷新并 AI 分类」开始处理收件箱")
    else:
        st.markdown(f"#### 📬 共 {len(processed)} 封邮件（按 AI 优先级排序）")

        for idx, item in enumerate(processed[:50]):
            classification = item.get("classification", {})
            email_obj = item.get("email", {}) or {}
            intent = classification.get("intent", "info_only")
            intent_info = INTENT_CATEGORIES.get(intent, INTENT_CATEGORIES["info_only"])
            urgency = classification.get("urgency", "low")
            priority_score = item.get("priority_score", 0)
            confidence = classification.get("confidence", 0.0)

            # 邮件主体
            from_addr = email_obj.get("from", "(未知发件人)")
            subject = email_obj.get("subject", "(无主题)")
            snippet = email_obj.get("snippet", "")
            date = email_obj.get("date", "")

            # Card header with priority + intent badge
            badge_color = _urgency_color(urgency)
            unique_key = item.get("email_id") or f"row_{idx}"

            with st.expander(
                f"{intent_info['icon']} **[{priority_score}]** "
                f"{intent_info['label']} | "
                f"{subject[:60]} — {from_addr[:35]}",
                expanded=(idx < 3 and urgency == "high"),
            ):
                col_meta, col_actions = st.columns([3, 1])

                with col_meta:
                    st.markdown(
                        f"<div style='font-size:0.85rem;color:#64748b;'>"
                        f"📧 <b>From:</b> {html_escape(from_addr)} &nbsp;|&nbsp; "
                        f"📅 {date[:25] if date else '-'} &nbsp;|&nbsp; "
                        f"<span style='background:{badge_color};color:white;padding:2px 8px;"
                        f"border-radius:10px;font-size:0.75rem;'>"
                        f"{urgency.upper()}</span> &nbsp;"
                        f"<span style='color:#64748b;'>置信度: {int(confidence*100)}%</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if subject:
                        st.markdown(f"**主题:** {subject}")

                    if snippet:
                        st.markdown(
                            f"<div style='background:#f8fafc;border-left:3px solid #cbd5e1;"
                            f"padding:0.6rem 0.9rem;border-radius:4px;margin:0.5rem 0;"
                            f"font-size:0.88rem;color:#475569;'>{html_escape(snippet[:400])}</div>",
                            unsafe_allow_html=True,
                        )

                    # Key points & action
                    kps = classification.get("key_points", [])
                    if kps:
                        st.markdown(
                            "**📌 关键点:** " +
                            " · ".join(f"`{p}`" for p in kps[:5])
                        )

                    suggested = classification.get("suggested_action", "")
                    if suggested:
                        st.info(f"💡 建议行动: {suggested}")

                with col_actions:
                    st.markdown(
                        f"<div style='font-size:0.7rem;color:#64748b;'>优先级</div>"
                        f"{_priority_bar(priority_score)}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"<div style='font-size:0.85rem;color:#0f172a;font-weight:600;'>"
                                f"{priority_score}/100</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:0.7rem;color:#64748b;margin-top:0.3rem;'>"
                                f"⏰ {intent_info.get('urgency_hours', 0)}h 内处理</div>",
                                unsafe_allow_html=True)

                # ── AI 回复建议 ──
                st.markdown("---")
                col_btn, col_send = st.columns([1, 1])

                draft_key = f"_draft_{unique_key}"
                gen_key = f"_gen_{unique_key}"

                with col_btn:
                    gen_clicked = st.button(
                        "🤖 AI 生成回复",
                        key=gen_key,
                        use_container_width=True,
                        disabled=intent in ("spam", "info_only"),
                    )

                with col_send:
                    sent_flag = f"_sent_{unique_key}"
                    send_clicked = st.button(
                        "📤 通过 " + status["provider"].title() + " 发送",
                        key=f"_send_{unique_key}",
                        use_container_width=True,
                        type="primary",
                        disabled=not st.session_state.get(draft_key),
                    )

                # 生成回复（流式）
                if gen_clicked:
                    placeholder = st.empty()
                    accumulated = ""
                    try:
                        gen = generate_reply_suggestion(
                            from_email=from_addr,
                            subject=subject,
                            snippet=snippet,
                            intent=intent,
                            key_points=classification.get("key_points", []),
                            user_id=user_id,
                            stream=True,
                        )
                        for chunk in gen:
                            accumulated += str(chunk)
                            placeholder.markdown(
                                f"<div style='background:#f0fdf4;border-left:3px solid #22c55e;"
                                f"padding:0.8rem;border-radius:6px;font-family:monospace;"
                                f"white-space:pre-wrap;font-size:0.88rem;'>{accumulated}▌</div>",
                                unsafe_allow_html=True,
                            )
                        placeholder.empty()
                        st.session_state[draft_key] = accumulated.strip()
                    except Exception as e:
                        st.error(f"生成失败: {e}")

                # 显示 / 编辑 草稿
                if st.session_state.get(draft_key):
                    edited_draft = st.text_area(
                        "AI 草稿（可编辑）",
                        value=st.session_state[draft_key],
                        height=180,
                        key=f"_textarea_{unique_key}",
                    )
                    st.session_state[draft_key] = edited_draft
                    copy_button(edited_draft, f"copy_{unique_key}")

                # 发送
                if send_clicked and st.session_state.get(draft_key):
                    # 提取纯邮箱（from 字段可能是 "Name <email@x.com>"）
                    import re as _re
                    m = _re.search(r"<([^>]+)>", from_addr)
                    to_email = m.group(1) if m else from_addr.strip()

                    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

                    with st.spinner(f"通过 {status['provider']} 发送..."):
                        send_ok, send_msg = send_via_provider(
                            username=username,
                            to_email=to_email,
                            subject=reply_subject,
                            body=st.session_state[draft_key],
                        )

                    if send_ok:
                        st.success(f"✅ 已发送给 {to_email}")
                        # 清空草稿
                        st.session_state.pop(draft_key, None)
                        # TODO: 关联原 tracking_id 后记录到 outreach log。
                    else:
                        st.error(f"❌ 发送失败: {send_msg}")


# ─────────────────────────────────────────────────────────
# Tab 2: 分析洞察
# ─────────────────────────────────────────────────────────
with tab_analytics:
    analytics = get_inbox_analytics(username)

    if analytics["total_processed"] == 0:
        st.info("📊 还没有分析过的邮件。先在「收件箱」标签页点击刷新")
    else:
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("已分析邮件", analytics["total_processed"])
        with col2:
            st.metric("⚠️ 紧急邮件", analytics["urgent_count"])
        with col3:
            st.metric("平均优先级", analytics["avg_priority"])
        with col4:
            top_intents = analytics.get("top_intents", [])
            if top_intents:
                top_intent_key = top_intents[0][0]
                top_label = INTENT_CATEGORIES.get(
                    top_intent_key, {}
                ).get("label", top_intent_key)
                st.metric("最多类型", top_label)

        st.markdown("---")
        st.markdown("### 📊 邮件意图分布")
        dist = analytics.get("intent_distribution", {})
        total = sum(dist.values()) or 1
        for intent_key, count in sorted(dist.items(), key=lambda x: -x[1]):
            info = INTENT_CATEGORIES.get(intent_key, {})
            label = info.get("label", intent_key)
            icon = info.get("icon", "•")
            pct = count / total * 100
            st.markdown(
                f"**{icon} {label}** &nbsp; <span style='color:#64748b;'>"
                f"{count} 封 ({pct:.1f}%)</span>",
                unsafe_allow_html=True,
            )
            st.progress(min(pct / 100, 1.0))


st.markdown("---")
st.markdown(
    '<div class="footer">📥 AI 智能收件箱 · 让外贸员把时间花在对的客户身上</div>',
    unsafe_allow_html=True,
)
