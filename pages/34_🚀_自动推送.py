"""
pages/34_🚀_自动推送.py
自动客户推送：上传客户列表 → AI按行业生成个性化邮件 → 批量发送 → 自动回复 → 重点转发
支持本地产品目录管理，自动匹配对口企业产品信息
"""
import csv
import io
import time

import streamlit as st

from utils.auto_outreach import (
    INDUSTRY_TEMPLATES,
    auto_reply_to_customer,
    create_campaign,
    delete_campaign,
    get_campaign,
    get_campaign_summary,
    get_campaigns,
    get_outreach_logs,
    generate_outreach_email,
    parse_prospect_file,
    run_campaign_step,
    update_campaign,
)
from utils.product_catalog import (
    add_product,
    delete_product,
    get_catalog,
    get_catalog_industries,
    match_products_for_prospect,
    update_product,
)
from utils.ui_helpers import check_auth, copy_button, get_user_id, inject_css

st.set_page_config(page_title="自动推送 | 外贸AI助手", page_icon="🚀", layout="wide")
inject_css()
check_auth()


def _get_username() -> str:
    """获取当前用户名。"""
    user = st.session_state.get("current_user")
    if user and user.get("username"):
        return user["username"]
    return "default"


# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">🚀 智能自动推送</h1>
    <p class="hero-subtitle">上传客户列表，AI按行业自动生成个性化产品推介邮件，支持自动回复与重点邮件转发</p>
</div>
""", unsafe_allow_html=True)

# ── 功能切换 Tab ──────────────────────────────────────
tab_new, tab_catalog, tab_campaigns, tab_auto_reply, tab_logs = st.tabs([
    "📤 新建推送", "📦 产品目录", "📊 推送任务", "💬 自动回复", "📋 推送日志"
])

# ══════════════════════════════════════════════════════
# Tab 1: 新建推送任务
# ══════════════════════════════════════════════════════
with tab_new:
    st.markdown('<div class="main-form">', unsafe_allow_html=True)

    # ── Step 1: 上传客户列表 ──
    st.markdown("### 📁 第一步：上传客户列表")
    st.markdown(
        '<div class="tip-card">'
        '💡 支持 CSV / Excel 格式。必填列: <code>email</code>；'
        '推荐列: <code>company</code>, <code>contact_name</code>, <code>industry</code>, '
        '<code>country</code>, <code>product_interest</code>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 下载模板
    template_csv = "email,company,contact_name,industry,country,product_interest\njohn@example.com,ABC Corp,John Smith,electronics,USA,LED lights\nmaria@test.de,Schmidt GmbH,Maria Schmidt,automotive,Germany,auto parts\n"
    st.download_button(
        "📥 下载 CSV 模板",
        template_csv,
        file_name="客户列表模板.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader(
        "上传客户列表文件",
        type=["csv", "xlsx", "xls"],
        help="必填: email 列；推荐: company, contact_name, industry, country",
    )

    prospects = []
    if uploaded_file is not None:
        file_content = uploaded_file.getvalue()
        prospects, parse_error = parse_prospect_file(file_content, uploaded_file.name)

        if parse_error:
            st.error(f"⚠️ {parse_error}")
        elif prospects:
            st.success(f"✅ 成功解析 {len(prospects)} 个客户记录")

            # 行业分布统计
            industry_counts = {}
            for p in prospects:
                ind = p.get("industry", "other")
                label = INDUSTRY_TEMPLATES.get(ind, {}).get("label", ind)
                industry_counts[label] = industry_counts.get(label, 0) + 1

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总客户数", len(prospects))
            with col2:
                st.metric("行业类别", len(industry_counts))
            with col3:
                has_email = sum(1 for p in prospects if p.get("email"))
                st.metric("有效邮箱", has_email)

            # 行业分布
            with st.expander("📊 行业分布", expanded=False):
                for ind_label, count in sorted(industry_counts.items(), key=lambda x: -x[1]):
                    st.markdown(f"- **{ind_label}**: {count} 个客户")

            # 预览表格
            with st.expander("👀 客户预览（前10条）", expanded=True):
                preview_data = []
                for p in prospects[:10]:
                    ind = p.get("industry", "other")
                    preview_data.append({
                        "邮箱": p.get("email", ""),
                        "公司": p.get("company", ""),
                        "联系人": p.get("contact_name", ""),
                        "行业": INDUSTRY_TEMPLATES.get(ind, {}).get("label", ind),
                        "国家": p.get("country", ""),
                    })
                st.dataframe(preview_data, use_container_width=True)

    # ── Step 2: 配置推送参数 ──
    st.markdown("---")
    st.markdown("### ⚙️ 第二步：配置推送参数")

    col_left, col_right = st.columns(2)

    with col_left:
        campaign_name = st.text_input(
            "任务名称",
            value=f"推送任务_{time.strftime('%m%d_%H%M')}",
            help="给这个推送任务起个名字，方便后续管理",
        )
        product_info = st.text_area(
            "产品/服务信息 *",
            placeholder="例如：LED户外照明灯具，IP67防水，寿命50000小时，适用于道路/工厂/仓库照明...",
            height=120,
            help="描述你要推广的产品或服务，AI会根据客户行业匹配相关卖点",
        )
        company_intro = st.text_area(
            "公司简介（可选）",
            placeholder="例如：深圳XX科技有限公司，成立于2010年，专注LED照明15年，出口80+国家...",
            height=80,
        )

    with col_right:
        sender_name = st.text_input(
            "发件人显示名",
            placeholder="例如：Tom Wang - XYZ Lighting",
            help="邮件中显示的发件人名称",
        )
        forward_email = st.text_input(
            "重点邮件转发邮箱",
            placeholder="例如：boss@mycompany.com",
            help="当客户回复表现出下单/采购意向时，自动转发到此邮箱",
        )
        forward_channel = st.selectbox(
            "转发渠道",
            ["email", "webhook"],
            format_func=lambda x: "📧 邮件转发" if x == "email" else "🔗 Webhook推送",
            help="重点邮件的通知方式",
        )
        auto_reply_enabled = st.checkbox(
            "开启自动回复",
            value=True,
            help="收到客户回复时，AI自动识别意图并生成回复",
        )

    # ── Step 3: 预览 & 发送 ──
    st.markdown("---")
    st.markdown("### 🚀 第三步：预览并发送")

    # 产品目录匹配状态提示
    username_for_catalog = _get_username()
    catalog = get_catalog(username_for_catalog)
    if catalog:
        ind_counts = get_catalog_industries(username_for_catalog)
        st.markdown(
            f'<div class="tip-card">'
            f'🎯 <b>产品目录已启用：</b>{len(catalog)} 个产品，覆盖 {len(ind_counts)} 个行业。'
            f'系统将自动为每位客户匹配最相关的产品参数写入邮件。'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="tip-card">'
            '💡 <b>提示：</b>前往「📦 产品目录」添加你的产品信息，系统可自动匹配客户行业推送对口产品，大幅提升邮件精准度。'
            '</div>',
            unsafe_allow_html=True,
        )

    col_preview, col_send = st.columns(2)

    with col_preview:
        preview_clicked = st.button(
            "👁️ 预览第一封邮件",
            disabled=not (prospects and product_info),
            use_container_width=True,
        )

    with col_send:
        send_clicked = st.button(
            f"🚀 开始推送 ({len(prospects)} 封)",
            type="primary",
            disabled=not (prospects and product_info),
            use_container_width=True,
        )

    # 预览逻辑
    if preview_clicked and prospects and product_info:
        with st.spinner("AI 正在生成预览邮件（自动匹配本地产品目录）..."):
            user_id = get_user_id()
            username = _get_username()
            email_data = generate_outreach_email(
                prospect=prospects[0],
                product_info=product_info,
                company_intro=company_intro,
                user_id=user_id,
                username=username,
                use_catalog=True,
            )
            if email_data["error"]:
                st.error(email_data["error"])
            else:
                st.markdown("#### 📧 预览邮件")
                ind = prospects[0].get("industry", "other")

                # 显示匹配到的本地产品
                matched = email_data.get("matched_products", [])
                if matched:
                    matched_names = ", ".join(p.get("name", "") for p in matched[:3])
                    st.success(
                        f"🎯 **已匹配本地产品目录:** {matched_names}\n\n"
                        f"AI 将基于你的实际产品参数生成精准推介邮件"
                    )
                else:
                    catalog = get_catalog(_get_username())
                    if not catalog:
                        st.warning("💡 提示：尚未配置产品目录，前往「📦 产品目录」添加产品可提升邮件精准度")
                    else:
                        st.info("ℹ️ 未匹配到与该客户行业对口的产品，使用通用产品描述")

                st.info(
                    f"**收件人:** {prospects[0].get('contact_name', '')} "
                    f"<{prospects[0].get('email', '')}>\n\n"
                    f"**行业:** {INDUSTRY_TEMPLATES.get(ind, {}).get('label', ind)}\n\n"
                    f"**Subject:** {email_data['subject']}"
                )
                st.text_area("邮件正文", email_data["body"], height=250, key="preview_body")
                copy_button(f"Subject: {email_data['subject']}\n\n{email_data['body']}", "preview_copy")

    # 发送逻辑
    if send_clicked and prospects and product_info:
        username = _get_username()
        user_id = get_user_id()

        # 创建campaign
        campaign = create_campaign(
            username=username,
            campaign_name=campaign_name,
            prospects=prospects,
            product_info=product_info,
            company_intro=company_intro,
            sender_name=sender_name,
            forward_email=forward_email,
            forward_channel=forward_channel,
            auto_reply_enabled=auto_reply_enabled,
        )

        st.markdown("---")
        st.markdown("### 📡 推送进度")

        progress_bar = st.progress(0)
        status_container = st.empty()
        results_container = st.container()

        sent_count = 0
        failed_count = 0
        total = len(prospects)

        for step_result in run_campaign_step(username, campaign["id"], user_id):
            idx = step_result["index"]
            email = step_result["email"]
            status = step_result["status"]
            detail = step_result["detail"]

            if status == "sent":
                sent_count += 1
            elif status == "failed":
                failed_count += 1

            progress = (idx + 1) / total
            progress_bar.progress(progress)

            status_emoji = {"sent": "✅", "failed": "❌", "skipped": "⏭️"}.get(status, "•")
            status_container.markdown(
                f"**进度:** {idx + 1}/{total} | "
                f"✅ 成功: {sent_count} | ❌ 失败: {failed_count} | "
                f"当前: {status_emoji} {email}"
            )

        # 完成汇总
        progress_bar.progress(1.0)
        status_container.empty()

        if sent_count > 0:
            st.markdown(
                f'<div class="success-box">'
                f'<div style="font-size:1.5rem;">🎉</div>'
                f'<div class="success-title">推送完成！成功发送 {sent_count}/{total} 封邮件</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if failed_count > 0:
            st.warning(f"⚠️ {failed_count} 封发送失败，请检查邮件配置")

        if forward_email:
            st.info(f"📬 重点邮件将自动转发到: {forward_email}")
        if auto_reply_enabled:
            st.info("🤖 自动回复已开启，收到客户回复时将自动处理")

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# Tab 2: 产品目录管理
# ══════════════════════════════════════════════════════
with tab_catalog:
    username = _get_username()
    catalog = get_catalog(username)

    st.markdown("""
    <div class="tip-card">
    💡 <b>产品目录说明：</b>在这里添加你的产品信息并标注适用行业。
    推送邮件时，系统会<b>自动匹配客户行业</b>对应的产品，将真实产品名称、参数、认证写入邮件，大幅提升专业度和回复率。
    </div>
    """, unsafe_allow_html=True)

    # ── 目录统计 ──
    if catalog:
        ind_counts = get_catalog_industries(username)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("产品总数", len(catalog))
        with col2:
            st.metric("覆盖行业", len(ind_counts))
        with col3:
            # 未覆盖行业提示
            all_industries = set(INDUSTRY_TEMPLATES.keys()) - {"other"}
            covered = set(ind_counts.keys())
            uncovered = all_industries - covered
            st.metric("未覆盖行业", len(uncovered))

        if uncovered:
            uncovered_labels = [INDUSTRY_TEMPLATES[i]["label"] for i in uncovered if i in INDUSTRY_TEMPLATES]
            with st.expander("⚠️ 未覆盖的行业（该行业客户将使用通用描述）"):
                for label in uncovered_labels:
                    st.markdown(f"- {label}")

    # ── 添加新产品 ──
    st.markdown("### ➕ 添加产品")
    with st.form("add_product_form", clear_on_submit=True):
        col_name, col_ind = st.columns([2, 1])
        with col_name:
            new_name = st.text_input("产品名称 *", placeholder="例如: LED Street Light 200W")
        with col_ind:
            industry_options = [(k, v["label"]) for k, v in INDUSTRY_TEMPLATES.items() if k != "other"]
            new_industries = st.multiselect(
                "适用行业 *",
                options=[k for k, _ in industry_options],
                format_func=lambda x: INDUSTRY_TEMPLATES[x]["label"],
                help="选择该产品适合推送的目标行业",
            )

        new_description = st.text_area(
            "产品描述",
            placeholder="一句话概述产品用途和优势...",
            height=60,
        )
        new_features = st.text_area(
            "核心卖点/参数 *",
            placeholder="每行一条，例如：\n• IP67防水\n• 寿命50000小时\n• 光效160lm/W\n• CE/RoHS/UL认证",
            height=100,
        )

        col_price, col_moq, col_cert = st.columns(3)
        with col_price:
            new_price = st.text_input("参考价格区间", placeholder="$50-$120/unit")
        with col_moq:
            new_moq = st.text_input("MOQ", placeholder="100 units")
        with col_cert:
            new_certs = st.text_input("认证", placeholder="CE, RoHS, FCC, UL")

        new_keywords = st.text_input(
            "搜索关键词（逗号分隔）",
            placeholder="led, street light, outdoor lighting, solar",
            help="用于匹配客户的 product_interest 字段",
        )

        submitted = st.form_submit_button("✅ 添加到产品目录", type="primary", use_container_width=True)
        if submitted:
            if not new_name or not new_features:
                st.error("请填写产品名称和核心卖点")
            elif not new_industries:
                st.error("请选择至少一个适用行业")
            else:
                keywords_list = [kw.strip() for kw in new_keywords.split(",") if kw.strip()] if new_keywords else []
                add_product(
                    username=username,
                    name=new_name,
                    description=new_description,
                    features=new_features,
                    industries=new_industries,
                    keywords=keywords_list,
                    price_range=new_price,
                    moq=new_moq,
                    certifications=new_certs,
                )
                st.success(f"✅ 已添加产品: {new_name}")
                st.rerun()

    # ── 现有产品列表 ──
    if catalog:
        st.markdown("### 📦 我的产品目录")
        for product in catalog:
            ind_labels = [INDUSTRY_TEMPLATES.get(i, {}).get("label", i) for i in product.get("industries", [])]
            with st.expander(
                f"**{product['name']}** — 行业: {', '.join(ind_labels) or '未分类'} | "
                f"{'💰 ' + product.get('price_range', '') if product.get('price_range') else ''}"
            ):
                col_detail, col_action = st.columns([4, 1])
                with col_detail:
                    if product.get("description"):
                        st.markdown(f"📝 {product['description']}")
                    if product.get("features"):
                        st.markdown(f"**卖点:** {product['features'][:200]}")
                    info_parts = []
                    if product.get("moq"):
                        info_parts.append(f"MOQ: {product['moq']}")
                    if product.get("certifications"):
                        info_parts.append(f"认证: {product['certifications']}")
                    if product.get("keywords"):
                        info_parts.append(f"关键词: {', '.join(product['keywords'][:5])}")
                    if info_parts:
                        st.markdown(" | ".join(info_parts))
                with col_action:
                    if st.button("🗑️ 删除", key=f"del_prod_{product['id']}"):
                        delete_product(username, product["id"])
                        st.rerun()
    else:
        st.info("📭 产品目录为空，请添加产品以启用智能匹配推送")


# ══════════════════════════════════════════════════════
# Tab 3: 推送任务管理
# ══════════════════════════════════════════════════════
with tab_campaigns:
    username = _get_username()
    campaigns = get_campaigns(username)

    if not campaigns:
        st.info("📭 暂无推送任务，请在「新建推送」标签页创建")
    else:
        # 汇总统计
        summary = get_campaign_summary(username)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总任务数", summary["total_campaigns"])
        with col2:
            st.metric("已发送", summary["total_sent"])
        with col3:
            st.metric("客户回复", summary["total_replied"])
        with col4:
            st.metric("成功率", f"{summary['success_rate']}%")

        st.markdown("---")

        # 任务列表
        for campaign in reversed(campaigns):
            status_map = {
                "created": "🆕 已创建",
                "running": "▶️ 运行中",
                "paused": "⏸️ 已暂停",
                "completed": "✅ 已完成",
            }
            status_label = status_map.get(campaign["status"], campaign["status"])

            stats = campaign.get("stats", {})
            with st.expander(
                f"{status_label} | **{campaign['name']}** — "
                f"发送 {stats.get('sent', 0)}/{stats.get('total', 0)} | "
                f"回复 {stats.get('replied', 0)} | "
                f"重点 {stats.get('important', 0)} | "
                f"{campaign.get('created_at', '')[:10]}",
                expanded=False,
            ):
                col_info, col_actions = st.columns([3, 1])

                with col_info:
                    st.markdown(f"**产品:** {campaign.get('product_info', '')[:100]}...")
                    st.markdown(f"**转发邮箱:** {campaign.get('forward_email', '未设置')}")
                    st.markdown(f"**自动回复:** {'开启' if campaign.get('auto_reply_enabled') else '关闭'}")
                    st.markdown(f"**创建时间:** {campaign.get('created_at', '')[:16]}")

                with col_actions:
                    if campaign["status"] == "running":
                        if st.button("⏸️ 暂停", key=f"pause_{campaign['id']}"):
                            update_campaign(username, campaign["id"], {"status": "paused"})
                            st.rerun()
                    elif campaign["status"] == "paused":
                        if st.button("▶️ 恢复", key=f"resume_{campaign['id']}"):
                            update_campaign(username, campaign["id"], {"status": "running"})
                            st.rerun()

                    if st.button("🗑️ 删除", key=f"del_{campaign['id']}"):
                        delete_campaign(username, campaign["id"])
                        st.rerun()

                # 发送结果详情
                results = campaign.get("results", [])
                if results:
                    st.markdown("**发送记录:**")
                    result_data = []
                    for r in results[:20]:
                        result_data.append({
                            "状态": "✅" if r.get("status") == "sent" else "❌",
                            "邮箱": r.get("email", ""),
                            "公司": r.get("company", ""),
                            "主题": r.get("subject", r.get("error", ""))[:50],
                            "时间": r.get("timestamp", "")[:16],
                        })
                    st.dataframe(result_data, use_container_width=True)

                    # 导出结果
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(["email", "company", "contact_name", "status", "subject", "timestamp"])
                    for r in results:
                        writer.writerow([
                            r.get("email", ""),
                            r.get("company", ""),
                            r.get("contact_name", ""),
                            r.get("status", ""),
                            r.get("subject", r.get("error", "")),
                            r.get("timestamp", ""),
                        ])
                    st.download_button(
                        "📥 导出发送记录",
                        output.getvalue(),
                        file_name=f"推送记录_{campaign['name']}.csv",
                        mime="text/csv",
                        key=f"export_{campaign['id']}",
                    )


# ══════════════════════════════════════════════════════
# Tab 4: 自动回复测试
# ══════════════════════════════════════════════════════
with tab_auto_reply:
    st.markdown("""
    <div class="tip-card">
    💡 <b>自动回复功能说明：</b><br>
    当客户回复你的推送邮件时，AI会自动：<br>
    1. 识别客户意图（感兴趣/需要报价/下单等）<br>
    2. 生成合适的回复邮件<br>
    3. 如果是重点客户（下单/采购意向），自动转发到你指定的邮箱<br><br>
    下方可以模拟测试自动回复效果。
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🧪 模拟自动回复")

    # 选择关联的推送任务
    username = _get_username()
    campaigns = get_campaigns(username)
    campaign_options = {c["id"]: f"{c['name']} ({c.get('created_at', '')[:10]})" for c in campaigns}

    if not campaign_options:
        st.info("请先创建一个推送任务，自动回复功能需要关联任务上下文")
    else:
        selected_campaign_id = st.selectbox(
            "关联推送任务",
            options=list(campaign_options.keys()),
            format_func=lambda x: campaign_options[x],
        )

        col_email, col_msg = st.columns([1, 2])
        with col_email:
            test_customer_email = st.text_input(
                "客户邮箱",
                placeholder="customer@example.com",
            )
        with col_msg:
            pass

        test_message = st.text_area(
            "客户回复内容",
            placeholder="粘贴客户的回复邮件内容...\n\n例如：\nHi, thanks for your email. We are interested in your LED lights. Could you send us a quotation for 5000 units? We need IP67 rated for outdoor use.",
            height=150,
        )

        if st.button("🤖 测试自动回复", type="primary", disabled=not (test_customer_email and test_message)):
            with st.spinner("AI 正在分析客户意图并生成回复..."):
                user_id = get_user_id()
                reply_data = auto_reply_to_customer(
                    customer_email=test_customer_email,
                    customer_message=test_message,
                    campaign_id=selected_campaign_id,
                    username=username,
                    user_id=user_id,
                )

            if reply_data["error"]:
                st.error(reply_data["error"])
            else:
                # 显示分析结果
                col_intent, col_important = st.columns(2)
                with col_intent:
                    st.markdown(f"**🎯 识别意图:** {reply_data['intent']}")
                with col_important:
                    if reply_data["is_important"]:
                        st.markdown("**🔥 重要程度:** <span style='color:red;font-weight:bold;'>高优先级</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("**📊 重要程度:** 普通")

                if reply_data["forwarded"]:
                    campaign = get_campaign(username, selected_campaign_id)
                    fwd_email = campaign.get("forward_email", "") if campaign else ""
                    st.success(f"📬 已转发到: {fwd_email}")

                st.markdown("---")
                st.markdown("#### 📧 AI 生成的回复")
                st.info(f"**Subject:** {reply_data['reply_subject']}")
                st.text_area(
                    "回复正文",
                    reply_data["reply_body"],
                    height=200,
                    key="auto_reply_preview",
                )
                copy_button(
                    f"Subject: {reply_data['reply_subject']}\n\n{reply_data['reply_body']}",
                    "reply_copy",
                )


# ══════════════════════════════════════════════════════
# Tab 5: 推送日志
# ══════════════════════════════════════════════════════
with tab_logs:
    username = _get_username()
    logs = get_outreach_logs(username, limit=100)

    if not logs:
        st.info("📭 暂无推送日志")
    else:
        st.markdown(f"### 📋 最近 {len(logs)} 条推送记录")

        # 筛选
        log_types = list(set(log.get("type", "unknown") for log in logs))
        type_labels = {
            "auto_reply": "💬 自动回复",
            "campaign_sent": "📤 邮件发送",
            "forward": "📬 重点转发",
        }
        selected_type = st.selectbox(
            "筛选类型",
            ["all"] + log_types,
            format_func=lambda x: "全部" if x == "all" else type_labels.get(x, x),
        )

        filtered_logs = logs if selected_type == "all" else [l for l in logs if l.get("type") == selected_type]

        for log in filtered_logs[:50]:
            log_type = log.get("type", "unknown")
            type_emoji = {"auto_reply": "💬", "campaign_sent": "📤", "forward": "📬"}.get(log_type, "•")
            timestamp = log.get("timestamp", "")[:16]
            customer = log.get("customer_email", "")
            intent = log.get("intent", "")
            is_important = log.get("is_important", False)

            detail_parts = [f"{type_emoji} **{timestamp}**"]
            if customer:
                detail_parts.append(f"客户: {customer}")
            if intent:
                detail_parts.append(f"意图: {intent}")
            if is_important:
                detail_parts.append("🔥 重点")

            st.markdown(" | ".join(detail_parts))


# ── 页脚 ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div class="footer">💼 外贸AI助手 · 智能自动推送 — 让AI帮你精准触达每一位潜在客户</div>',
    unsafe_allow_html=True,
)
