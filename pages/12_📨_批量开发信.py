"""
pages/12_📨_批量开发信.py
批量开发信生成：上传CSV，逐行生成个性化开发信，支持预览和批量下载。
并发生成（ThreadPoolExecutor, max_workers=3），速度提升约 3x。
"""
from __future__ import annotations

import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from utils.ai_client import generate_bulk_email
from utils.history import add_to_history
from utils.ui_helpers import copy_button, get_user_id, page_setup

page_setup("批量开发信", "📨", "📨 批量开发信生成", "上传 CSV 客户名单，AI 并发批量生成个性化开发信（3x 提速）")

# ── 说明 ──────────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown(
    '<div class="tip-card">💡 CSV 文件需包含列：company, contact_name, product（必填）；'
    '可选列：email, industry, country。每行生成一封个性化开发信（并发 3 路，约 3x 提速）。</div>',
    unsafe_allow_html=True,
)

# ── 文件上传 ──────────────────────────────────────────
uploaded_file = st.file_uploader(
    "上传客户 CSV 文件",
    type=["csv"],
    help="必填列: company, contact_name, product；可选列: email, industry, country",
)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helper: parse one email result text
# ---------------------------------------------------------------------------
def _parse_email(result_text: str, contact_name: str, company: str, email: str) -> dict:
    subject = ""
    body = result_text
    for line in result_text.splitlines():
        if line.strip().lower().startswith("subject:"):
            subject = line.strip()[len("subject:"):].strip()
            idx = result_text.find(line)
            try:
                body = result_text[result_text.index("\n", idx) + 1:].strip()
            except ValueError:
                body = result_text
            break
    return {
        "recipient": f"{contact_name} <{email}>" if email else contact_name,
        "company": company,
        "contact_name": contact_name,
        "subject": subject,
        "body": body,
        "full_text": result_text,
    }


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
        required_cols = {"company", "contact_name", "product"}
        actual_cols = set(rows[0].keys()) if rows else set()
        missing_cols = required_cols - actual_cols

        if missing_cols:
            st.error(f"⚠️ CSV 缺少必填列: {', '.join(missing_cols)}")
            st.info("需要的列: company, contact_name, product（可选: email, industry, country）")
        else:
            # ── 预览 ──────────────────────────────────────
            st.markdown("### 📋 CSV 预览")
            st.caption(f"共 {len(rows)} 条记录")
            preview_data = [
                {
                    "公司": r.get("company", ""),
                    "联系人": r.get("contact_name", ""),
                    "产品": r.get("product", ""),
                    "邮箱": r.get("email", ""),
                    "行业": r.get("industry", ""),
                    "国家": r.get("country", ""),
                }
                for r in rows[:20]
            ]
            st.dataframe(preview_data, use_container_width=True)
            if len(rows) > 20:
                st.caption(f"（仅显示前 20 条，共 {len(rows)} 条）")

            generate_clicked = st.button(
                f"🚀 批量生成 {len(rows)} 封开发信（并发加速）",
                type="primary",
                use_container_width=True,
            )

            if generate_clicked:
                user_id = get_user_id()
                results_list: list[dict] = []
                errors: list[str] = []

                # ── 过滤掉缺失必填字段的行 ──────────────────
                valid_rows = []
                for i, row in enumerate(rows):
                    if not row.get("company", "").strip() or \
                       not row.get("contact_name", "").strip() or \
                       not row.get("product", "").strip():
                        errors.append(f"第 {i+1} 行: 缺少必填字段")
                    else:
                        valid_rows.append((i, row))

                if valid_rows:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    completed_count = 0

                    # ── 并发生成（max_workers=3）────────────────
                    def _generate_one(args: tuple) -> tuple[int, str | None, dict]:
                        """Generate a single email. Returns (row_idx, error_msg, result_dict)."""
                        idx, row = args
                        company = row.get("company", "").strip()
                        contact_name = row.get("contact_name", "").strip()
                        product = row.get("product", "").strip()
                        industry = row.get("industry", "").strip()
                        country = row.get("country", "").strip()
                        email_addr = row.get("email", "").strip()
                        try:
                            result_text = generate_bulk_email(
                                company=company,
                                contact_name=contact_name,
                                product=product,
                                industry=industry,
                                country=country,
                                stream=False,
                                user_id=user_id,
                            )
                        except Exception as ex:
                            return idx, f"生成异常: {ex}", {}
                        if result_text and not result_text.startswith("⚠️"):
                            return idx, None, _parse_email(result_text, contact_name, company, email_addr)
                        return idx, result_text or "生成失败", {}

                    # Collect futures indexed by future object
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        future_to_idx = {
                            executor.submit(_generate_one, args): args[0]
                            for args in valid_rows
                        }
                        for future in as_completed(future_to_idx):
                            row_idx, err_msg, result = future.result()
                            completed_count += 1
                            if err_msg:
                                errors.append(f"第 {row_idx + 1} 行: {err_msg}")
                            else:
                                results_list.append(result)

                            # Streamlit UI updates from background threads aren't safe;
                            # update progress based on completed count
                            progress_bar.progress(completed_count / len(valid_rows))
                            status_text.markdown(
                                f"⏳ 已完成 {completed_count}/{len(valid_rows)} 封..."
                            )

                    status_text.empty()
                    progress_bar.empty()

                st.session_state["bulk_email_results"] = results_list
                st.session_state["bulk_email_errors"] = errors

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

                for idx, item in enumerate(results_list):
                    with st.expander(
                        f"📧 {item['contact_name']} @ {item['company']}"
                        + (f" | {item['subject'][:40]}" if item["subject"] else ""),
                        expanded=(idx == 0),
                    ):
                        st.text_area("邮件内容", item["full_text"], height=180,
                                     key=f"bulk_result_{idx}")
                        copy_button(item["full_text"], f"bulk_copy_{idx}")

                # 批量下载 CSV
                st.markdown("---")
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["recipient", "subject", "body"])
                for item in results_list:
                    writer.writerow([item["recipient"], item["subject"], item["body"]])

                st.download_button(
                    "📥 批量下载 CSV（recipient, subject, body）",
                    output.getvalue(),
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
