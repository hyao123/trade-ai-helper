"""
pages/12_📨_批量开发信.py
批量开发信生成：上传CSV，逐行生成个性化开发信，支持预览和批量下载。
"""
import csv
import io

import streamlit as st

from utils.ai_client import generate_bulk_email
from utils.history import add_to_history
from utils.ui_helpers import (
    check_auth,
    copy_button,
    get_user_id,
    inject_css,
)

st.set_page_config(page_title="批量开发信 | 外贸AI助手", page_icon="📨", layout="wide")
inject_css()
check_auth()

if "results" not in st.session_state:
    st.session_state.results = {}

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📨 批量开发信生成</h1>
    <p class="hero-subtitle">上传 CSV 客户名单，一键批量生成个性化开发信</p>
</div>
""", unsafe_allow_html=True)

# ── 说明 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 CSV 文件需包含列：company, contact_name, product（必填）；'
    '可选列：email, industry, country。每行生成一封个性化开发信。</div>',
    unsafe_allow_html=True,
)

# ── 文件上传 ──────────────────────────────────────────
uploaded_file = st.file_uploader(
    "上传客户 CSV 文件",
    type=["csv"],
    help="必填列: company, contact_name, product；可选列: email, industry, country",
)

st.markdown("</div>", unsafe_allow_html=True)

# ── CSV 解析与预览 ────────────────────────────────────
if uploaded_file is not None:
    try:
        content = uploaded_file.getvalue().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    except Exception as e:
        st.error(f"⚠️ CSV 解析失败: {e}")
        rows = []

    if rows:
        # 检查必填列
        required_cols = {"company", "contact_name", "product"}
        actual_cols = set(rows[0].keys()) if rows else set()
        missing_cols = required_cols - actual_cols

        if missing_cols:
            st.error(f"⚠️ CSV 缺少必填列: {', '.join(missing_cols)}")
            st.info("需要的列: company, contact_name, product（可选: email, industry, country）")
        else:
            # 预览步骤
            st.markdown("### 📋 CSV 预览")
            st.caption(f"共 {len(rows)} 条记录")

            # 构建预览表格
            preview_data = []
            for row in rows[:20]:  # 最多预览20行
                preview_data.append({
                    "公司": row.get("company", ""),
                    "联系人": row.get("contact_name", ""),
                    "产品": row.get("product", ""),
                    "邮箱": row.get("email", ""),
                    "行业": row.get("industry", ""),
                    "国家": row.get("country", ""),
                })
            st.dataframe(preview_data, use_container_width=True)
            if len(rows) > 20:
                st.caption(f"（仅显示前 20 条，共 {len(rows)} 条）")

            # 生成按钮
            generate_clicked = st.button(
                f"🚀 批量生成 {len(rows)} 封开发信",
                type="primary",
                use_container_width=True,
            )

            if generate_clicked:
                user_id = get_user_id()
                results_list = []
                errors = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, row in enumerate(rows):
                    company = row.get("company", "").strip()
                    contact_name = row.get("contact_name", "").strip()
                    product = row.get("product", "").strip()
                    industry = row.get("industry", "").strip()
                    country = row.get("country", "").strip()
                    email = row.get("email", "").strip()

                    # 跳过缺少必填字段的行
                    if not company or not contact_name or not product:
                        errors.append(f"第 {i+1} 行: 缺少必填字段 (company/contact_name/product)")
                        progress_bar.progress((i + 1) / len(rows))
                        continue

                    status_text.markdown(f"⏳ 正在生成第 {i+1}/{len(rows)} 封... ({contact_name} @ {company})")

                    # 非流式调用（批量模式）
                    result_text = generate_bulk_email(
                        company=company,
                        contact_name=contact_name,
                        product=product,
                        industry=industry,
                        country=country,
                        stream=False,
                        user_id=user_id,
                    )

                    if result_text and not result_text.startswith("⚠️"):
                        # 提取 Subject
                        subject = ""
                        body = result_text
                        for line in result_text.splitlines():
                            if line.strip().lower().startswith("subject:"):
                                subject = line.strip()[len("subject:"):].strip()
                                body = result_text[result_text.index("\n", result_text.index(line)) + 1:].strip()
                                break

                        results_list.append({
                            "recipient": f"{contact_name} <{email}>" if email else contact_name,
                            "company": company,
                            "contact_name": contact_name,
                            "subject": subject,
                            "body": body,
                            "full_text": result_text,
                        })
                    else:
                        errors.append(f"第 {i+1} 行 ({contact_name}): {result_text or '生成失败'}")

                    progress_bar.progress((i + 1) / len(rows))

                status_text.empty()
                progress_bar.empty()

                # 保存到 session_state
                st.session_state["bulk_email_results"] = results_list
                st.session_state["bulk_email_errors"] = errors

                # 保存第一条成功结果到历史
                if results_list:
                    add_to_history(
                        "批量开发信",
                        f"批量({len(results_list)}封)",
                        results_list[0]["full_text"],
                    )

            # ── 展示结果 ──────────────────────────────────
            results_list = st.session_state.get("bulk_email_results", [])
            errors = st.session_state.get("bulk_email_errors", [])

            if results_list:
                st.markdown(
                    '<div class="success-box">'
                    f'<div style="font-size:1.5rem;">✅</div>'
                    f'<div class="success-title">成功生成 {len(results_list)} 封开发信！</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                # 展开列表显示每封邮件
                for idx, item in enumerate(results_list):
                    with st.expander(
                        f"📧 {item['contact_name']} @ {item['company']} | Subject: {item['subject'][:40]}...",
                        expanded=(idx == 0),
                    ):
                        st.text_area(
                            "邮件内容",
                            item["full_text"],
                            height=180,
                            key=f"bulk_result_{idx}",
                        )
                        copy_button(item["full_text"], f"bulk_copy_{idx}")

                # 批量下载 CSV
                st.markdown("---")
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["recipient", "subject", "body"])
                for item in results_list:
                    writer.writerow([item["recipient"], item["subject"], item["body"]])
                csv_content = output.getvalue()

                st.download_button(
                    "📥 批量下载 CSV（recipient, subject, body）",
                    csv_content,
                    file_name="批量开发信_结果.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            if errors:
                with st.expander(f"⚠️ 跳过/失败记录 ({len(errors)} 条)", expanded=False):
                    for err in errors:
                        st.warning(err)

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 批量开发信</div>', unsafe_allow_html=True)
